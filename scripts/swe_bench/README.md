# SWE-bench Dataset Tooling

Tools under `scripts/swe_bench/` materialize [SWE-bench Verified](https://www.swebench.com/) instances into Shelly Testbench `repos/<instance_id>/` folders.

## Data source

- **Dataset:** [`princeton-nlp/SWE-bench_Verified`](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified)
- **Split:** `test` (500 human-verified instances)
- **On-disk copy:** `scripts/swe_bench/data/swe_bench_verified.json`

The fetcher reads the committed JSON only. No runtime Hugging Face / network dependency — once the file is in the repo, `fetch.sh` works offline apart from cloning the target upstream repos.

## Schema

Each JSON array entry is an object with at least these fields (the loader enforces them):

| Field | Type | Description |
| --- | --- | --- |
| `instance_id` | string | Unique SWE-bench identifier, e.g. `astropy__astropy-12907`. |
| `repo` | string | Upstream GitHub `owner/name`. |
| `base_commit` | string | Commit SHA to check out before the agent runs. |
| `problem_statement` | string | Raw GitHub issue text — becomes the body of the generated `PRD.md`. |
| `FAIL_TO_PASS` | string (JSON-encoded list) | Tests that should fail before the fix and pass after. |
| `PASS_TO_PASS` | string (JSON-encoded list) | Tests that must keep passing. |
| `environment_setup_commit` | string | Commit to use for installing dependencies (may differ from `base_commit`). |
| `version` | string | Upstream release tag the instance targets. |

Additional upstream fields (`patch`, `test_patch`, `hints_text`, `created_at`, `difficulty`) are preserved in the JSON for reference but are **intentionally ignored** by the fetcher so the agent never sees the gold solution.

## Regenerating the JSON

```bash
# Option A — preferred, uses the HuggingFace `datasets` library
pip install datasets
python scripts/swe_bench/download_dataset.py

# Option B — zero extra deps, hits the datasets-server API directly
python scripts/swe_bench/download_dataset.py --backend urllib
```

The helper writes to `scripts/swe_bench/data/swe_bench_verified.json`, validates that every required field is present, and exits nonzero if the upstream schema has drifted.

Regenerate and commit the updated JSON whenever:
- Hugging Face ships a revised `SWE-bench_Verified` revision, or
- you need fields that aren't currently in the committed file.

## Downstream consumers

- `scripts/swe_bench/loader.py` — reads and indexes the JSON.
- `scripts/swe_bench/fetch.sh` — the user-facing CLI that materializes instances into `repos/`.

See the top-level `README.md` → **`/repos`** section for a usage walkthrough.
