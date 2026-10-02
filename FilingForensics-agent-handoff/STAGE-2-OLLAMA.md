# Stage 2 — Ollama Evidence Synthesizer

## Objective

Connect the core evidence objects to the already-installed local `qwen3.5:2b` model.

## Build scope

- Implement `src/ollama_client.py` using the local HTTP API.
- Use `think: false`, temperature 0, and bounded output.
- Add a strict evidence-only prompt.
- Parse JSON if returned.
- Gracefully handle timeout, unavailable server, malformed JSON, and empty output.
- Never let the model calculate the authoritative percentage; use the deterministic calculation module.

Endpoint:

```text
http://127.0.0.1:11434/api/generate
```

## Required answer fields

```text
answer
calculation
narrative_evidence
citations
limitations
```

## Acceptance checks

```bash
python3 -m pytest -q
```

Also run a local smoke test against Ollama. The test must have a timeout and must not make any network request outside localhost.

If Ollama is unavailable, the client must return a structured fallback rather than raising an uncaught exception.

## Checkpoint requirements

1. Set this stage to `DONE`.
2. Set Stage 3 to `IN_PROGRESS` in `CURRENT_STATE.md`.
3. Record model latency, response behavior, and fallback behavior.
4. Commit:

```text
stage-2: add local Ollama evidence synthesis
```

## Implementation status

- Status: `DONE`
- Date/time: 2026-10-02
- Last agent: Cortex Code (claude-opus-5-5)
- Files created: src/answer_schema.py (tolerant JSON parse -> ModelAnswer), src/ollama_client.py (build_prompt, synthesize), tests/test_ollama_client.py
- Request: think=false, format=json, temperature 0, num_predict 700, timeout from OLLAMA_TIMEOUT_SECONDS (default 30s). Non-localhost hosts are refused without a request.
- Commands: `.venv/bin/python -m pytest -q` -> 18 passed, 1 skipped (live). `FF_LIVE_OLLAMA=1 .venv/bin/python -m pytest -q -s tests/test_ollama_client.py::test_live_ollama_smoke` -> passed twice, ok=True, latency 14.2s / 13.3s.
- Response behavior: model echoes the deterministic numbers and cites the ADSH IDs. With num_predict 400 the JSON was truncated (parse failed, handled as fallback); fixed by 700 + brevity instruction.
- Fallback behavior: timeout, connection error, HTTP error, empty output, malformed JSON, and missing fields all return ModelAnswer(ok=False, error=..., raw=...) - never raise.
- Correction: exact percent change is -2.8005% (-11043/394328); handoff's "-2.8007%" is within the Stage 1 test tolerance.
- Known limitations: ~14s latency on qwen3.5:2b with full evidence prompt; app should show a spinner. Model may restate rather than add insight.
- Next action: Stage 3 (Streamlit UI).
