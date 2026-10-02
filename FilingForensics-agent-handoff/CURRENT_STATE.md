# FilingForensics — Current State

This file is the handoff memory. Update it after every stage and every important recovery fix.

## Overall status

- Current stage: `COMPLETE` (MVP; Stage 4 optional)
- Stage 0: `DONE`
- Stage 1: `DONE`
- Stage 2: `DONE`
- Stage 3: `DONE`
- Stage 4: `OPTIONAL_PENDING`
- Stage 5: `DONE`

Critical path: `STAGE-0 → STAGE-1 → STAGE-2 → STAGE-3 → STAGE-5`

Stage 4 is optional and must not block the localhost MVP.

## Last checkpoint

- Date/time: 2026-10-02
- Commit: `stage-5: finalize demo and submission evidence`
- Summary: MVP complete. README with run/demo instructions and five-case smoke checklist. Clean-shell launch, real Ollama-down fallback, and secret scan verified.

## Demo instructions

```bash
.venv/bin/pip install -r requirements.txt   # if .venv missing: python3 -m venv .venv first
.venv/bin/python -m pytest -q
.venv/bin/streamlit run app.py              # http://localhost:8501, fixture mode, click Analyze
```

Demo sequence and limitations: see root `README.md`.

## Verified external facts

- Snowflake database: `SNOWFLAKE_PUBLIC_DATA_FREE`
- Snowflake schema: `PUBLIC_DATA_FREE`
- Apple CIK: `0000320193`
- Verified MD&A filing accession: `0000320193-23-000106`
- FY2022 revenue: `394328000000 USD`, period `2021-09-26` through `2022-09-24`, accession `0000320193-24-000123`
- FY2023 revenue: `383285000000 USD`, period `2022-09-25` through `2023-09-30`, accession `0000320193-25-000079`
- Deterministic change: `-11043000000 USD`, approximately `-2.8%` (exact -2.8005%)
- Ollama model: `qwen3.5:2b`
- Ollama endpoint: `http://127.0.0.1:11434`
- Ollama requires `think: false` for the fast response path.

## Last known commands/results

- `ollama --version` passed.
- `ollama list` showed `qwen3.5:2b` installed.
- Local Ollama smoke test passed in approximately 1.35 seconds.
- Python 3.9.6 (no 3.10+ syntax). `py_compile app.py src/config.py` passed.
- Virtualenv: `.venv/` (gitignored); run `.venv/bin/pip install -r requirements.txt` to recreate.
- `.venv/bin/python -m pytest -q` → 21 passed, 1 skipped.
- Live Ollama smoke (`FF_LIVE_OLLAMA=1`): ok, ~13-14s, num_predict 700 needed to avoid truncated JSON.
- Streamlit app: `.venv/bin/streamlit run app.py --server.port 8501` works; fixture mode verified end-to-end in browser.
- Model citations tend to omit the MD&A ADSH; deterministic provenance section always lists all three accessions.

## Blockers and decisions

- Use Streamlit as the frontend.
- Use a single Python process for the MVP; do not create a separate backend service.
- Use fixture mode as a first-class fallback.
- Keep Snowflake live mode optional and credential-safe.
- Do not add vector search or additional Marketplace datasets.

## Next action

MVP is complete. Only implement `STAGE-4-SNOWFLAKE.md` (optional live mode) if the user explicitly requests it; it must not break fixture mode.
