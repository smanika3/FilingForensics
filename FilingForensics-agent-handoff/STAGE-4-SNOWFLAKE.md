# Stage 4 — Optional Snowflake Live Mode

## Objective

Add live Snowflake retrieval while preserving a fully working fixture fallback.

## Build scope

- Implement `src/snowflake_client.py`.
- Use environment variables only.
- Use read-only, parameterized queries.
- Retrieve text and metric evidence independently.
- Normalize live rows into the same contracts used by fixture mode.
- Show a clear live/fixture status in the UI.
- If credentials are absent or connection fails, offer fixture mode instead of crashing.

## Data rules

Database:

```text
SNOWFLAKE_PUBLIC_DATA_FREE
```

Schema:

```text
PUBLIC_DATA_FREE
```

Do not use `LEFT JOIN ... ON TRUE`. Do not scan the entire dataset. Keep the Apple preset query narrow.

Always preserve:

- `ADSH`
- `FORM_TYPE`
- `FILED_DATE`
- `FISCAL_YEAR`
- `PERIOD_START_DATE`
- `PERIOD_END_DATE`
- `VALUE`
- `UNIT`

## Acceptance checks

- Fixture mode still works with all Snowflake variables unset.
- Live mode uses only read-only queries.
- Live mode returns the expected FY2022 and FY2023 revenue values when credentials are valid.
- Errors are visible and recoverable.
- `.env` is ignored and not committed.

## Checkpoint requirements

1. Set this stage to `DONE` if live mode works, or `DONE_WITH_FALLBACK` if fixture mode remains the reliable demo path.
2. Set Stage 5 to `IN_PROGRESS` in `CURRENT_STATE.md`.
3. Record whether live mode was tested and any account-specific limitation.
4. Commit:

```text
stage-4: add optional Snowflake live retrieval
```

## Implementation status

- Status: `DONE`
- Date/time: 2026-10-02
- Last agent: Cortex Code (claude-opus-5-5)
- Files: src/snowflake_client.py (new), src/retrieval.py (live dispatch, lazy import, text_rows), app.py (cached live load, live banner/badge, Switch-to-fixture button), tests/test_snowflake_client.py (new), tests/test_app.py (recovery), requirements.txt (+snowflake-connector-python[secure-local-storage]), .env.example, README.md
- Auth: SNOWFLAKE_CONNECTION_NAME (reuses ~/.snowflake/connections.toml) or SNOWFLAKE_ACCOUNT+USER with PASSWORD/AUTHENTICATOR (default externalbrowser). DB/schema validated as identifiers; all values bound via %(name)s.
- Commands:
  - `.venv/bin/python -m pytest -q` (Snowflake env unset) -> 28 passed, 2 skipped
  - `FF_LIVE_SNOWFLAKE=1 SNOWFLAKE_CONNECTION_NAME=vlwhdrb-kb51087 .venv/bin/python -m pytest -q -s tests/test_snowflake_client.py::test_live_snowflake` -> passed (12.6s incl. OAuth), rows text=1 metric=2, change -11043000000, -2.8005%
  - Browser: `SNOWFLAKE_CONNECTION_NAME=vlwhdrb-kb51087 .venv/bin/streamlit run app.py`, live mode -> "Live Snowflake evidence" badge, exact result, debug shows both SQL statements, model ok in 21.85s
- Live tested: yes, account VLWHDRB-KB51087, user smanika3, authenticator oauth_authorization_code.
- Account-specific notes: connector warns ~/.snowflake/connections.toml has loose permissions (`chmod 0600` recommended); OAuth opens browser login on first connect (keyring extra caches tokens).
- Known limitations: live MD&A text is 8,000 chars -> ~22s model latency (30s timeout). Apple preset only.
- Next action: none required. Fixture mode remains the default demo path.
