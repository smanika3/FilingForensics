# Stage 5 — Demo, QA, and Submission Evidence

## Objective

Turn the working vertical slice into a reliable hackathon demo and leave a complete handoff trail.

## Build scope

- Run the app from a clean shell.
- Verify fixture mode.
- Verify Ollama response or deterministic fallback.
- Verify live Snowflake mode if available, but do not risk fixture mode.
- Add a five-case smoke-test checklist.
- Add final README run instructions.
- Remove debug secrets and temporary files.
- Capture the CoCo role, Snowflake source, open-weight model, and local architecture in the project docs.

## Required demo sequence

1. Show the CoCo schema/query work.
2. Show the installed Snowflake SEC source.
3. Open the local Streamlit app.
4. Ask the Apple revenue question.
5. Show the deterministic calculation.
6. Expand narrative evidence and metric provenance.
7. Explain that Qwen runs locally through Ollama.
8. Show limitations and the non-advice boundary.

## Five-case smoke checklist

- Fixture mode with normal evidence.
- Fixture mode with Ollama unavailable.
- Missing metric row.
- Duplicate metric row.
- Live mode unavailable with graceful fallback.

## Acceptance checks

```bash
python3 -m pytest -q
streamlit run app.py

git status --short
```

The final working tree should contain no secrets or private data.

## Checkpoint requirements

1. Set this stage to `DONE`.
2. Update `CURRENT_STATE.md` with final commands, commit, known limitations, and demo instructions.
3. Commit:

```text
stage-5: finalize demo and submission evidence
```

## Implementation status

- Status: `PENDING`
- Last agent: none
- Notes: not started
- Next action: run final QA after the MVP is complete.
