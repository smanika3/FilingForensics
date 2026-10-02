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

- Status: `PENDING`
- Last agent: none
- Notes: not started
- Next action: build the fixture-first page.
