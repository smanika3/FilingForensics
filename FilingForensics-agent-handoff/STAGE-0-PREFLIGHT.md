# Stage 0 — Repository and Environment Preflight

## Objective

Create a clean, resumable Python project and verify the local runtime without implementing product behavior yet.

## Build scope

- Initialize Git if needed.
- Create the project layout from `CODING-AGENT-HANDOFF.md`.
- Create `.gitignore` and `.env.example`.
- Create `requirements.txt` with minimal dependencies.
- Confirm Python and Ollama are accessible.
- Confirm `qwen3.5:2b` is installed.
- Do not require Snowflake credentials.

## Required files

```text
app.py
requirements.txt
.env.example
.gitignore
src/__init__.py
src/config.py
tests/__init__.py
CURRENT_STATE.md
```

## Acceptance checks

```bash
python3 --version
ollama list
python3 -m py_compile app.py  # if app.py exists
git status --short
```

The stage passes when the repository is reproducible and no secrets/private data are tracked.

## Checkpoint requirements

1. Set this stage to `DONE` in this file.
2. Set Stage 1 to `IN_PROGRESS` in `CURRENT_STATE.md`.
3. Record commands/results in `CURRENT_STATE.md`.
4. Commit:

```text
stage-0: initialize resumable project
```

## Implementation status

- Status: `DONE`
- Date/time: 2026-10-02
- Last agent: Cortex Code (claude-opus-5-5)
- Files created: app.py (placeholder), requirements.txt, .env.example, .gitignore, src/__init__.py, src/config.py, tests/__init__.py
- Commands: `python3 --version` → 3.9.6; `ollama list` → qwen3.5:2b present; `python3 -m py_compile app.py src/config.py` → OK; `git status --short` → only scaffold + handoff docs
- Known limitations: Python 3.9 (avoid 3.10+ syntax such as `X | None`); dependencies not yet pip-installed; CURRENT_STATE.md lives in FilingForensics-agent-handoff/.
- Next action: Stage 1 (core fixture pipeline).
