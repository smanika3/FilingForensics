# FilingForensics — Current State

This file is the handoff memory. Update it after every stage and every important recovery fix.

## Overall status

- Current stage: `STAGE-2`
- Stage 0: `DONE`
- Stage 1: `DONE`
- Stage 2: `IN_PROGRESS`
- Stage 3: `PENDING`
- Stage 4: `OPTIONAL_PENDING`
- Stage 5: `PENDING`

Critical path: `STAGE-0 → STAGE-1 → STAGE-2 → STAGE-3 → STAGE-5`

Stage 4 is optional and must not block the localhost MVP.

## Last checkpoint

- Date/time: 2026-10-02
- Commit: `stage-1: add evidence fixtures and deterministic calculations`
- Summary: Evidence models, verified Apple fixtures (incl. real MD&A excerpt), deterministic revenue change with validation (missing/duplicate/non-USD/segment/non-adjacent), 10 unit tests passing.

## Verified external facts

- Snowflake database: `SNOWFLAKE_PUBLIC_DATA_FREE`
- Snowflake schema: `PUBLIC_DATA_FREE`
- Apple CIK: `0000320193`
- Verified MD&A filing accession: `0000320193-23-000106`
- FY2022 revenue: `394328000000 USD`, period `2021-09-26` through `2022-09-24`, accession `0000320193-24-000123`
- FY2023 revenue: `383285000000 USD`, period `2022-09-25` through `2023-09-30`, accession `0000320193-25-000079`
- Deterministic change: `-11043000000 USD`, approximately `-2.8%`
- Ollama model: `qwen3.5:2b`
- Ollama endpoint: `http://127.0.0.1:11434`
- Ollama requires `think: false` for the fast response path.

## Last known commands/results

- `ollama --version` passed.
- `ollama list` showed `qwen3.5:2b` installed.
- Local Ollama smoke test passed in approximately 1.35 seconds.
- Python 3.9.6 (no 3.10+ syntax). `py_compile app.py src/config.py` passed.
- Virtualenv: `.venv/` (gitignored); run `.venv/bin/pip install -r requirements.txt` to recreate.
- `.venv/bin/python -m pytest -q` → 10 passed.
- Streamlit app: placeholder only.

## Blockers and decisions

- Use Streamlit as the frontend.
- Use a single Python process for the MVP; do not create a separate backend service.
- Use fixture mode as a first-class fallback.
- Keep Snowflake live mode optional and credential-safe.
- Do not add vector search or additional Marketplace datasets.

## Next action

Read and implement `STAGE-2-OLLAMA.md`.
