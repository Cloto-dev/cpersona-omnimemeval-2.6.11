# CPersona 2.6.11 on OmniMemEval: run records

Per-question records of [CPersona](https://github.com/Cloto-dev/cpersona) 2.6.11 on
LongMemEval-S and LoCoMo through [OmniMemEval](https://github.com/MemTensor/OmniMemEval)'s
shared pipeline, in both of `reconstruct`'s response modes, with a script that
recomputes every published number from them.

| Benchmark | Questions | Mode | Overall | Context Tokens |
| --- | ---: | --- | ---: | ---: |
| LongMemEval-S (cleaned) | 500 | pro | 89.60 | 4,262.5 |
| LongMemEval-S (cleaned) | 500 | lite | 82.20 | 993.3 |
| LoCoMo (categories 1–4) | 1,540 | pro | 84.03 | 4,441.0 |
| LoCoMo (categories 1–4) | 1,540 | lite | 68.18 | 1,485.0 |

The two modes are `reconstruct`'s two response sizes. `pro` returns up to 15 items within
5,000 tokens of response JSON and holds two more places for block retrieval; `lite`
returns the default 10 items within 3,000 tokens. Both hold one place for a keyword
match. The runs of the two modes differ only in that setting, so a difference between
them is the mode's whole effect, not that of the token cap alone.

By category:

| LongMemEval-S | SS-User | SS-Asst | SS-Pref | Temp. Reas | Multi-S | Know. Upd |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CPersona 2.6.11 (pro) | 97.14 | 94.64 | 96.67 | 86.47 | 85.71 | 88.46 |
| CPersona 2.6.11 (lite) | 95.71 | 83.93 | 90.00 | 80.45 | 74.44 | 82.05 |

| LoCoMo | Single-Hop | Multi-Hop | Temporal | Open-Domain |
| --- | ---: | ---: | ---: | ---: |
| CPersona 2.6.11 (pro) | 88.70 | 78.01 | 83.18 | 63.54 |
| CPersona 2.6.11 (lite) | 73.84 | 51.06 | 72.59 | 54.17 |

## The runs

- **Who and when**: run by the CPersona project (Cloto-dev), 2026-10-19, one run each.
- **Backend**: CPersona 2.6.11 (git tag `v2.6.11`, also on PyPI), self-hosted on one
  machine. CPersona calls no generative model to store or recall, so OmniMemEval's
  "memory service model" setting does not apply.
- **Stores**: each benchmark was ingested once into a new, empty database file. For
  LongMemEval-S both modes searched that store. For LoCoMo each mode searched its own
  copy of it, made before any search.
- **Server settings**: streamable HTTP on loopback; `CPERSONA_MAX_CONTENT_LENGTH=80000`
  (default 16,000) so that no session is cut when it is stored; every other setting at
  its default.
- **Embeddings**: `BAAI/bge-m3` (revision `5617a9f61b028005a4858fdac845db406aefb181`)
  through sentence-transformers 5.6.0 (transformers 5.12.1, torch 2.12.1), normalized,
  512-token window, served over HTTP by a local process.
- **Harness**: OmniMemEval at commit `0b1ea8d` on Python 3.12.13 (mcp 2.2.0, openai 3.23.0,
  tiktoken 0.14.0, httpx 0.28.1). Later commits up to `c3b60c7`, the current `main`, do
  not change the pipeline: under `scripts/` they change only comments, tests and a
  documentation-link checker. The run used
  [`omnimemeval-0b1ea8d-2_6_11.patch`](https://github.com/Cloto-dev/cpersona/blob/master/benchmarks/omnimemeval/omnimemeval-0b1ea8d-2_6_11.patch)
  applied and the client
  [`cpersona_client.py`](https://github.com/Cloto-dev/cpersona/blob/master/benchmarks/omnimemeval/cpersona_client.py)
  added under `scripts/client_factory/`. The patch registers the client. For LoCoMo it
  stores each session once, as the harness's speaker-A view (which carries both
  speakers' turns), in one store per conversation, and searches that store with the
  harness's `shared_conv_search`, as for EverOS and Supermemory. The client calls
  CPersona's `reconstruct` with the mode named by `CPERSONA_SEARCH_MODE` (`pro` or
  `lite`) and that mode's default count; the harness's `top_k` (`TOPK=20` in the env
  file) is not passed.
- **Models**: answers by `gpt-4.1-mini`, recorded as `gpt-4.1-mini-2025-04-14` in
  `token_usage_answer.json`; one judge run by `gpt-4o-mini`. The harness does not record
  the judge's resolved snapshot; one API call on 2026-10-19 showed that alias resolving
  to `gpt-4o-mini-2024-07-18`. The harness's own prompts and metric.
- **Data**: LongMemEval-S cleaned, `longmemeval_s_cleaned.json`, sha256
  `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`, all 500 questions.
  LoCoMo `locomo10.json`, sha256
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`, the 1,540 questions
  of categories 1–4 (the adversarial category 5 excluded, as in OmniMemEval's tables).
  Both datasets as distributed, with their answer keys unmodified.
- **Coverage**: in every run published here, every question was searched, answered and
  judged: each item's recorded status is `success` at the search, answer and eval
  stages. The harness has no separate timeout status, and no item failed or was
  skipped. The ingestion stored all 23,867 LongMemEval-S sessions and all 272 LoCoMo
  sessions (`ingest/success_records.txt`). A discarded first ingestion is described
  below. Overall is correct answers over all questions (500 and 1,540).
- **Context Tokens**: the answer model's reported prompt tokens over its calls, answer
  prompt included, none estimated: LongMemEval-S 2,131,237 (pro) and 496,670 (lite) over
  500 calls; LoCoMo 6,839,071 (pro) and 2,286,974 (lite) over 1,540 calls. The
  `context_tokens` field inside `*_grades.json` is a different count (the retrieved
  context alone, in `cl100k_base`) and is not the table's figure.

### Commands

From the patched OmniMemEval checkout, with a CPersona 2.6.11 server running
([`config/cpersona-server-env.example`](config/cpersona-server-env.example)) and the
harness's env file ([`config/omnimemeval-env.example`](config/omnimemeval-env.example)).
`<mode>` is `pro` or `lite`:

```bash
# LongMemEval-S (ingestion once; search, answer, judge and metric once per mode)
scripts/longmemeval/lme_ingestion.py --lib cpersona --version lme2611 --workers 2
CPERSONA_SEARCH_MODE=<mode> scripts/longmemeval/lme_search.py --lib cpersona --version lme2611 --workers 2
scripts/longmemeval/lme_responses.py --lib cpersona --version lme2611 --llm-workers 3
scripts/longmemeval/lme_eval.py --lib cpersona --version lme2611 --num_runs 1 --llm-workers 5
scripts/longmemeval/lme_metric.py --lib cpersona --version lme2611

# LoCoMo (ingestion once; the store copied for each mode before searching)
scripts/locomo/locomo_ingestion.py --lib cpersona --version ov2611 --workers 2
CPERSONA_SEARCH_MODE=<mode> scripts/locomo/locomo_search.py --lib cpersona --version ov2611 --workers 1
scripts/locomo/locomo_responses.py --lib cpersona --version ov2611
scripts/locomo/locomo_eval.py --lib cpersona --version ov2611 --num_runs 1
scripts/locomo/locomo_metric.py --lib cpersona --version ov2611
```

Each command runs under `OMNIMEMEVAL_ENV_FILE=<env file>` with the harness's Python.
The harness names its output folder `cpersona-<version>`; the folders here add the mode.

### What differs from a clean run

1. **Calibration (LongMemEval-S)**: CPersona calibrates a similarity threshold, per user
   or for the whole store. Calibrating each of the 500 users costs about 200 recalls per
   user, so both modes reused the calibration file of an earlier LongMemEval-S store
   built by this project from the same data and embedding model
   ([`calibration/longmemeval-s-store.calibration.json`](calibration/longmemeval-s-store.calibration.json)):
   a store-wide similarity threshold of 0.3628, and no per-user entry naming any of these
   users. The server restored that file at startup in both modes rather than
   recalibrating during the search.
2. **Calibration (LoCoMo)**: each of the 10 users was calibrated once, before the store
   was copied for the two modes. On these small stores (19 to 32 records a user) the
   recall gate cannot be calibrated, so at every start the server recalibrates the whole
   store again while it serves, and the original searches ran beside that. A later
   rerun that waited for the startup calibration to finish returned the same context for
   every one of the 1,540 questions in both modes: every user's threshold came out the
   same in every calibration, and the gate stayed at its default (only the store-wide
   threshold differed, and the contexts did not change with it). So the contexts in these records
   are the ones a search gives once the startup calibration has finished. The answers
   and judgments were not run again.
3. **Ingestion (LongMemEval-S)**: a first ingestion with four workers lost 339
   embedding calls to a refused connection on the local embedding server and was
   discarded. The second, with two workers, stored all 23,867 sessions without an
   embedding failure. These records are from the second.

The reasons for all three are on the
[results page](https://github.com/Cloto-dev/cpersona/blob/master/benchmarks/measurements/results-omnimemeval-2_6_11.md).

## Files

```
results/lme/cpersona-lme2611-pro/      OmniMemEval's own output files, one folder per run
results/lme/cpersona-lme2611-lite/
results/locomo/cpersona-ov2611-pro/
results/locomo/cpersona-ov2611-lite/
  *_search_results.json.gz             what search returned for each question (gzip)
  *_responses.json                     the answer model's answers
  *_judged.json                        the judge's verdict for each question
  *_grades.json                        the harness's aggregate, by category
  *_status.json                        stage status counts
  token_usage_answer.json              answer-model prompt tokens and call count
  ingest/success_records.txt           the sessions the harness recorded as stored
calibration/                           the calibration file the LongMemEval-S runs reused
config/                                the server's and the harness's settings, credentials removed
verify/recompute.py                    recomputes the numbers above from these files
```

## Verify

```bash
python verify/recompute.py
```

For each of the four runs it checks that the records hold 500 or 1,540 judged answers
with no failed or skipped stage, recomputes Overall and each category from the
per-question verdicts and compares both with the harness's grades file, recomputes
Context Tokens from the token totals, and counts the stored sessions. It also checks
the calibration file's SHA-256. Standard library only. To replay the answer and judge
steps, decompress a `*_search_results.json.gz` into OmniMemEval's `results/` layout and
run the responses, eval and metric commands above with your own API key.

## Licenses

- `verify/` and this README: MIT.
- `results/lme/`: derived from [LongMemEval](https://github.com/xiaowu0162/LongMemEval)
  (Wu et al., 2024), MIT.
- `results/locomo/`: derived from [LoCoMo](https://github.com/snap-research/locomo)
  (Maharana et al., 2024), CC BY-NC 4.0. Use must be non-commercial and credit the
  LoCoMo authors.
