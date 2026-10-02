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

- Status: `PENDING`
- Last agent: none
- Notes: Ollama was externally smoke-tested before coding and passed with `think: false`.
- Next action: implement the local model adapter.
