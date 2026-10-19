"""Recompute the published scores from the per-question records in this repository.

For each benchmark it checks:
- coverage: the expected number of judged records, each with status "success" and one verdict,
  and the harness's stage status counts (search, answer, eval) with no failed or skipped item;
- accuracy: Overall and every category recomputed from the per-question verdicts, compared with
  the harness's own grades file;
- Context Tokens: the answer model's reported prompt-token total over its call count;
- ingestion: the number of sessions the harness recorded as stored.
It also checks the SHA-256 of the reused LongMemEval-S calibration file.

usage: python verify/recompute.py        (standard library only; run from the repository root)
"""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCOMO_NAMES = {1: "multi hop", 2: "temporal reasoning", 3: "open domain", 4: "single hop"}
CALIBRATION_SHA256 = "1c13934a7cf245367c7362083380c6853bf121b922cb984f8811aac6bdc90c01"


def rows(judged):
    """The judged file maps a user to one record (LongMemEval) or a list of records (LoCoMo)."""
    for user, value in judged.items():
        for record in value if isinstance(value, list) else [value]:
            yield user, record


def check(name, folder, prefix, expected_questions, expected_sessions):
    judged = json.loads((folder / f"{prefix}_judged.json").read_text())
    grades = json.loads((folder / f"{prefix}_grades.json").read_text())
    usage = json.loads((folder / "token_usage_answer.json").read_text())["modules"]["ANSWER"]

    total = correct = 0
    by_category = defaultdict(lambda: [0, 0])
    for _, record in rows(judged):
        assert record["status"] == "success", record
        verdicts = list(record["llm_judgments"].values())
        assert len(verdicts) == 1, "one judge run per question"
        ok = bool(verdicts[0])
        category = record["category"]
        if isinstance(category, int):
            category = LOCOMO_NAMES[category]
        total += 1
        correct += ok
        by_category[category][0] += ok
        by_category[category][1] += 1
    assert total == expected_questions, (name, total, expected_questions)

    overall = 100 * correct / total
    published = 100 * grades["metrics"]["llm_judge_score"]
    assert abs(overall - published) < 1e-9, (name, overall, published)
    graded = {v.get("category_name", k): v for k, v in grades["category_scores"].items()}
    assert set(graded) == set(by_category), (name, sorted(graded), sorted(by_category))
    for category, (ok, n) in by_category.items():
        assert graded[category]["total"] == n, (name, category, graded[category]["total"], n)
        assert abs(graded[category]["llm_judge_score"] - ok / n) < 1e-12, (name, category)
    for stage, status in grades["pipeline_status"].items():
        assert status["status_counts"] == {"success": expected_questions}, (name, stage, status)
        assert status["failed_units"] == 0 and status["skipped_records"] == 0, (name, stage, status)

    assert usage["call_count"] == expected_questions and usage["estimated_prompt_call_count"] == 0
    context_tokens = usage["prompt_tokens"] / usage["call_count"]

    stored = [line for line in (folder / "ingest/success_records.txt").read_text().splitlines() if line.strip()]
    assert len(stored) == len(set(stored)) == expected_sessions, (name, len(stored), expected_sessions)

    print(f"{name}: {correct}/{total} = {overall:.2f}% (grades file: {published:.2f}%)")
    for category, (ok, n) in sorted(by_category.items()):
        print(f"  {category:28s} {ok:4d}/{n:<4d} {100 * ok / n:6.2f}%  (grades file agrees)")
    print(f"  Context Tokens = {usage['prompt_tokens']:,} prompt tokens / {usage['call_count']:,} calls "
          f"= {context_tokens:,.1f} (answer model {usage['model']}, none estimated)")
    print(f"  sessions stored: {len(stored):,}")


for mode in ("pro", "lite"):
    check(f"LongMemEval-S, {mode} mode", ROOT / f"results/lme/cpersona-lme2611-{mode}", "cpersona_lme", 500, 23867)
    check(f"LoCoMo, {mode} mode", ROOT / f"results/locomo/cpersona-ov2611-{mode}", "cpersona_locomo", 1540, 272)
digest = hashlib.sha256((ROOT / "calibration/longmemeval-s-store.calibration.json").read_bytes()).hexdigest()
assert digest == CALIBRATION_SHA256, digest
print(f"calibration file sha256 {digest}")
print("all checks passed")
