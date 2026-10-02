# Stage 1 — Core Evidence Models, Fixtures, and Calculations

## Objective

Implement the data contracts and deterministic financial calculation using the verified Apple evidence. Do not build the UI yet.

## Build scope

Create:

- Typed or clearly structured evidence models
- Verified Apple fixture data
- Revenue change calculation
- Input validation
- Unit tests

Expected calculation:

```text
FY2022 = 394328000000 USD
FY2023 = 383285000000 USD
absolute change = -11043000000 USD
percent change ≈ -2.8007%
```

## Required behaviors

- Reject missing fiscal years.
- Reject duplicate total annual metric rows.
- Reject non-USD rows for this preset.
- Preserve accession, filed date, period dates, and fiscal year.
- Format values as USD billions for display while retaining raw values.

## Acceptance checks

```bash
python3 -m pytest -q
```

Minimum tests:

- Expected absolute change
- Expected percentage change within tolerance
- Evidence validation
- Missing-row failure
- Duplicate-row failure

## Checkpoint requirements

1. Set this stage to `DONE`.
2. Set Stage 2 to `IN_PROGRESS` in `CURRENT_STATE.md`.
3. Record test output and changed files.
4. Commit:

```text
stage-1: add evidence fixtures and deterministic calculations
```

## Implementation status

- Status: `DONE`
- Date/time: 2026-10-02
- Last agent: Cortex Code (claude-opus-5-5)
- Files created: src/models.py, src/fixtures.py, src/calculations.py, tests/test_calculations.py, tests/test_fixtures.py
- Environment: `.venv/` (Python 3.9.6, gitignored) with requirements.txt installed (streamlit 1.50.0, requests 2.32.5, pytest 8.4.2). Use `.venv/bin/python`.
- Commands: `.venv/bin/python -m pytest -q` → `10 passed in 0.01s`
- Tests: absolute change, percent change (±1e-3), summary/formatting, missing year, duplicate row, non-USD, segment row, non-adjacent periods, fixture provenance.
- Notes: MD&A excerpt pulled read-only from Snowflake (ADSH 0000320193-23-000106, PART II Item 7) and stored verbatim in src/fixtures.py.
- Known limitations: Apple FY2022→FY2023 preset only.
- Next action: Stage 2 (Ollama client + answer schema).
