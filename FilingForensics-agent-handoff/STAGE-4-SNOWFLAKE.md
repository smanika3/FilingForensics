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

- Status: `PENDING`
- Last agent: none
- Notes: Snowflake SQL was verified manually before coding.
- Next action: implement the optional connector only after fixture UI works.
