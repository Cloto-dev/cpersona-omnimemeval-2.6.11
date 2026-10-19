"""Recompute the published scores from the per-question records in this repository.

For each of the four runs (LongMemEval-S and LoCoMo, pro and lite mode) it checks:
- coverage: the expected number of judged records, each with status "success" and one verdict,
  and the harness's stage status counts (search, answer, eval) with no failed or skipped item;
- accuracy: Overall and every category recomputed from the per-question verdicts, compared with
  the harness's own grades file;
- Context Tokens: the answer model's reported prompt-token total over its call count;
- the published figures: every Overall, category and Context Tokens value shown in the README and
  in the OmniMemEval rows, against the recomputed ones;
- ingestion: the number of sessions the harness recorded as stored.
It also checks:
- LongMemEval-S accuracy split into the 100 development questions and the other 400;
- that the LoCoMo rerun's search returned, for every question in both modes, the same context
  as the published search;
- the SHA-256 of the reused LongMemEval-S calibration file;
- with --data DIR (holding longmemeval_s_cleaned.json and locomo10.json, checked by SHA-256),
  that every record's question, reference answer and category match the dataset.
A failed check stops the script with exit status 1, under `python -O` too.

usage: python verify/recompute.py [--data DIR]     (standard library only)
"""
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCOMO_NAMES = {1: "multi hop", 2: "temporal reasoning", 3: "open domain", 4: "single hop"}
CALIBRATION_SHA256 = "1c13934a7cf245367c7362083380c6853bf121b922cb984f8811aac6bdc90c01"
DATA_SHA256 = {
    "longmemeval_s_cleaned.json": "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442",
    "locomo10.json": "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4",
}
# The published figures: Overall and categories (%, two decimals), and Context Tokens as the
# README shows it (one decimal) and as the OmniMemEval rows show it (whole tokens).
PUBLISHED = {
    "LongMemEval-S, pro mode": (89.60, {"single-session-user": 97.14, "single-session-assistant": 94.64,
        "single-session-preference": 96.67, "temporal-reasoning": 86.47, "multi-session": 85.71,
        "knowledge-update": 88.46}, 4262.5, 4262),
    "LongMemEval-S, lite mode": (82.20, {"single-session-user": 95.71, "single-session-assistant": 83.93,
        "single-session-preference": 90.00, "temporal-reasoning": 80.45, "multi-session": 74.44,
        "knowledge-update": 82.05}, 993.3, 993),
    "LoCoMo, pro mode": (84.03, {"single hop": 88.70, "multi hop": 78.01, "temporal reasoning": 83.18,
        "open domain": 63.54}, 4441.0, 4441),
    "LoCoMo, lite mode": (68.18, {"single hop": 73.84, "multi hop": 51.06, "temporal reasoning": 72.59,
        "open domain": 54.17}, 1485.0, 1485),
}
# LongMemEval-S accuracy (%) on the 100 development questions and on the other 400.
PUBLISHED_SPLIT = {"pro": (93.00, 88.75), "lite": (87.00, 81.00)}


def check(condition, *detail):
    if not condition:
        print("CHECK FAILED: " + " | ".join(str(d) for d in detail), file=sys.stderr)
        sys.exit(1)


def rows(judged):
    """The judged file maps a user to one record (LongMemEval) or a list of records (LoCoMo)."""
    for user, value in judged.items():
        for record in value if isinstance(value, list) else [value]:
            yield user, record


def check_run(name, folder, prefix, expected_questions, expected_sessions):
    judged = json.loads((folder / f"{prefix}_judged.json").read_text())
    grades = json.loads((folder / f"{prefix}_grades.json").read_text())
    usage = json.loads((folder / "token_usage_answer.json").read_text())["modules"]["ANSWER"]

    total = correct = 0
    by_category = defaultdict(lambda: [0, 0])
    for _, record in rows(judged):
        check(record["status"] == "success", name, "record status", record.get("status"))
        verdicts = list(record["llm_judgments"].values())
        check(len(verdicts) == 1, name, "one judge run per question", len(verdicts))
        ok = bool(verdicts[0])
        category = record["category"]
        if isinstance(category, int):
            category = LOCOMO_NAMES[category]
        total += 1
        correct += ok
        by_category[category][0] += ok
        by_category[category][1] += 1
    check(total == expected_questions, name, "questions", total, expected_questions)

    overall = 100 * correct / total
    published = 100 * grades["metrics"]["llm_judge_score"]
    check(abs(overall - published) < 1e-9, name, "grades Overall", overall, published)
    graded = {v.get("category_name", k): v for k, v in grades["category_scores"].items()}
    check(set(graded) == set(by_category), name, "categories", sorted(graded), sorted(by_category))
    for category, (ok, n) in by_category.items():
        check(graded[category]["total"] == n, name, category, "grades count", graded[category]["total"], n)
        check(abs(graded[category]["llm_judge_score"] - ok / n) < 1e-12, name, category, "grades score")
    for stage, status in grades["pipeline_status"].items():
        check(status["status_counts"] == {"success": expected_questions}, name, stage, status)
        check(status["failed_units"] == 0 and status["skipped_records"] == 0, name, stage, status)

    check(usage["call_count"] == expected_questions and usage["estimated_prompt_call_count"] == 0,
          name, "answer calls", usage["call_count"], usage["estimated_prompt_call_count"])
    context_tokens = usage["prompt_tokens"] / usage["call_count"]

    want_overall, want_categories, want_ctx1, want_ctx0 = PUBLISHED[name]
    check(round(overall, 2) == want_overall, name, "published Overall", round(overall, 2), want_overall)
    for category, (ok, n) in by_category.items():
        check(round(100 * ok / n, 2) == want_categories[category], name, category, "published",
              round(100 * ok / n, 2))
    check(round(context_tokens, 1) == want_ctx1 and round(context_tokens) == want_ctx0,
          name, "published Context Tokens", context_tokens, want_ctx1, want_ctx0)

    stored = [line for line in (folder / "ingest/success_records.txt").read_text().splitlines() if line.strip()]
    check(len(stored) == len(set(stored)) == expected_sessions, name, "stored sessions", len(stored),
          expected_sessions)

    print(f"{name}: {correct}/{total} = {overall:.2f}% (grades file: {published:.2f}%)")
    for category, (ok, n) in sorted(by_category.items()):
        print(f"  {category:28s} {ok:4d}/{n:<4d} {100 * ok / n:6.2f}%  (grades file agrees)")
    print(f"  Context Tokens = {usage['prompt_tokens']:,} prompt tokens / {usage['call_count']:,} calls "
          f"= {context_tokens:,.1f} (answer model {usage['model']}, none estimated)")
    print(f"  sessions stored: {len(stored):,}")
    return judged


def question_index(user):
    """LongMemEval-S users are named <prefix>_<index of the question in the dataset>."""
    return int(user.rsplit("_", 1)[1])


def check_split(judged_by_mode):
    dev = {q["index"] for q in json.loads((ROOT / "data/longmemeval-s-dev-questions.json").read_text())["dev"]}
    check(len(dev) == 100, "development questions", len(dev))
    for mode, judged in judged_by_mode.items():
        verdicts = {question_index(user): bool(next(iter(r["llm_judgments"].values()))) for user, r in rows(judged)}
        check(sorted(verdicts) == list(range(500)), "LongMemEval-S", mode, "question indices")
        a = [v for i, v in verdicts.items() if i in dev]
        b = [v for i, v in verdicts.items() if i not in dev]
        got = (round(100 * sum(a) / len(a), 2), round(100 * sum(b) / len(b), 2))
        check(len(a) == 100 and len(b) == 400 and got == PUBLISHED_SPLIT[mode],
              "LongMemEval-S split", mode, len(a), len(b), got, PUBLISHED_SPLIT[mode])
        print(f"LongMemEval-S, {mode} mode: {sum(a)}/100 development questions = {got[0]:.2f}%, "
              f"{sum(b)}/400 other questions = {got[1]:.2f}%")


def contexts(path):
    """Map (user, query, occurrence of that query for the user) to the context search returned."""
    with gzip.open(path) as f:
        search = json.load(f)
    out = {}
    for user, records in search.items():
        seen = Counter()
        for r in records:
            out[(user, r["query"], seen[r["query"]])] = r["context"]
            seen[r["query"]] += 1
    return out


def check_rerun():
    for mode in ("pro", "lite"):
        published = contexts(ROOT / f"results/locomo/cpersona-ov2611-{mode}/cpersona_locomo_search_results.json.gz")
        rerun = contexts(ROOT / f"results/locomo/rerun-search/{mode}/cpersona_locomo_search_results.json.gz")
        check(len(published) == 1540 and set(published) == set(rerun), "LoCoMo rerun", mode, "question sets",
              len(published), len(rerun))
        differ = sum(published[k] != rerun[k] for k in published)
        check(differ == 0, "LoCoMo rerun", mode, f"{differ} contexts differ")
        print(f"LoCoMo rerun, {mode} mode: the same context for all {len(published):,} questions")


def check_against_data(data_dir, judged_by_run):
    for name, digest in DATA_SHA256.items():
        got = hashlib.sha256((data_dir / name).read_bytes()).hexdigest()
        check(got == digest, name, "SHA-256", got)
    lme = json.loads((data_dir / "longmemeval_s_cleaned.json").read_text())
    for run in ("LongMemEval-S, pro mode", "LongMemEval-S, lite mode"):
        for user, r in rows(judged_by_run[run]):
            q = lme[question_index(user)]
            check(r["question"] == q["question"] and str(r["golden_answer"]) == str(q["answer"])
                  and r["category"] == q["question_type"], run, user, "does not match the dataset")
    locomo = json.loads((data_dir / "locomo10.json").read_text())
    want = Counter((qa["question"], str(qa["answer"]), qa["category"])
                   for conv in locomo for qa in conv["qa"] if qa.get("category") in LOCOMO_NAMES)
    for run in ("LoCoMo, pro mode", "LoCoMo, lite mode"):
        got = Counter((r["question"], str(r["golden_answer"]), r["category"]) for _, r in rows(judged_by_run[run]))
        check(got == want, run, "questions, answers and categories do not match the dataset",
              sum((got - want).values()), sum((want - got).values()))
    print("every record's question, reference answer and category match the dataset")


judged_by_run = {}
for mode in ("pro", "lite"):
    judged_by_run[f"LongMemEval-S, {mode} mode"] = check_run(
        f"LongMemEval-S, {mode} mode", ROOT / f"results/lme/cpersona-lme2611-{mode}", "cpersona_lme", 500, 23867)
    judged_by_run[f"LoCoMo, {mode} mode"] = check_run(
        f"LoCoMo, {mode} mode", ROOT / f"results/locomo/cpersona-ov2611-{mode}", "cpersona_locomo", 1540, 272)
check_split({m: judged_by_run[f"LongMemEval-S, {m} mode"] for m in ("pro", "lite")})
check_rerun()
digest = hashlib.sha256((ROOT / "calibration/longmemeval-s-store.calibration.json").read_bytes()).hexdigest()
check(digest == CALIBRATION_SHA256, "calibration file SHA-256", digest)
print(f"calibration file sha256 {digest}")
if "--data" in sys.argv:
    check(sys.argv.index("--data") + 1 < len(sys.argv), "--data needs a directory")
    check_against_data(Path(sys.argv[sys.argv.index("--data") + 1]), judged_by_run)
print("all checks passed")
