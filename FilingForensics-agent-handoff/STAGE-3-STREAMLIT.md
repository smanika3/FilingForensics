# Stage 3 — Streamlit Frontend

## Objective

Build a polished local Streamlit UI around fixture mode. The app must be demonstrable without Snowflake credentials.

## Build scope

- Implement `app.py`.
- Add Apple/company and question presets.
- Add fixture/live mode selector, defaulting to fixture.
- Display deterministic answer and calculation.
- Display metric evidence table.
- Display narrative evidence excerpt.
- Display source filing accession, filed date, form, and financial periods.
- Display limitations and the non-advice boundary.
- Add debug/evidence expander with model name and row counts.

## Acceptance checks

```bash
streamlit run app.py
```

Manually verify:

- App launches locally.
- Fixture mode works without credentials.
- Expected revenue change is visible.
- Evidence and provenance are visible.
- Model failure does not crash the page.
- No secrets appear in the UI.

## Checkpoint requirements

1. Set this stage to `DONE`.
2. Set Stage 5 to `IN_PROGRESS` in `CURRENT_STATE.md`.
3. Leave Stage 4 as `OPTIONAL_PENDING` unless live Snowflake mode is already working without slowing the demo.
4. Record the launch command and manual checks.
5. Commit:

```text
stage-3: build fixture-first Streamlit evidence UI
```

## Implementation status

- Status: `DONE`
- Date/time: 2026-10-02
- Last agent: Cortex Code (claude-opus-5-5)
- Files: app.py (full UI), src/retrieval.py (EvidenceBundle; fixture mode; live raises LiveModeUnavailable -> visible error), tests/test_app.py (AppTest)
- Launch: `.venv/bin/streamlit run app.py --server.port 8501` -> http://localhost:8501
- Commands: `.venv/bin/python -m pytest -q` -> 21 passed, 1 skipped (live Ollama).
- Manual checks (browser, live qwen3.5:2b): launches; fixture banner shown; answer "Revenue decreased by $11.04B, or 2.8%, from FY2022 to FY2023." with metrics and exact calc (-2.8005%); model explanation in 14.3s; metric table + bar chart; MD&A excerpt with ADSH/form/filed/item; provenance with both metric accessions, filed dates and periods; limitations + non-advice; debug shows mode, row counts, model, latency, raw JSON. No secrets displayed.
- Failure checks (AppTest): Ollama ConnectionError -> warning + deterministic answer, no crash; live mode -> error telling user to switch to fixture mode.
- Fixes: model text containing `$` rendered as LaTeX -> escaped via md(). `st.segmented_control` broke AppTest on Streamlit 1.50 -> used `st.radio(horizontal=True)`.
- Known limitations: model citations usually list the two metric ADSHs but omit the MD&A ADSH (app's provenance section always shows all three). ~14s model latency (spinner shown). Live mode not implemented (Stage 4 optional).
- Next action: Stage 5 (demo QA, README, smoke checklist).
