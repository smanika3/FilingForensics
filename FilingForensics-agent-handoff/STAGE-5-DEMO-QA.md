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

- Status: `DONE`
- Date/time: 2026-10-02
- Last agent: Cortex Code (claude-opus-5-5)
- Files: README.md (run instructions, architecture, CoCo/Snowflake/model roles, five-case smoke checklist, demo sequence, limitations)
- Commands/results:
  - `.venv/bin/python -m pytest -q` -> 21 passed, 1 skipped
  - Clean shell (`env -i`) `streamlit run app.py --server.port 8502` -> HTTP 200, `/_stcore/health` ok
  - Real Ollama-unavailable (port 11999) -> structured fallback `Ollama unavailable ...`, no exception
  - Browser run with live qwen3.5:2b (Stage 3) -> full answer/evidence/provenance, 14.3s
  - Secret scan of tracked files -> none; no .env, logs, or CSVs tracked
- Five-case checklist: all five covered (see README table).
- Live Snowflake mode: not available (Stage 4 optional, not implemented); graceful error verified.
- Known limitations: see README.
- Next action: MVP complete. Optional: Stage 4 live Snowflake mode only if requested.
