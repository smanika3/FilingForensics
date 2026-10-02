# FilingForensics — Agent Start Here

## Mission

Build the smallest credible FilingForensics MVP in a time-boxed, resumable workflow. The user may switch agents or run out of CoCo credits. Never assume previous conversational memory.

## Mandatory resume protocol

Before writing code:

1. Read this file completely.
2. Read `CURRENT_STATE.md`.
3. Read `ARCHITECTURE.md`.
4. List the repository files and inspect the latest Git commits.
5. Read the stage README for the first incomplete critical-path stage. The critical path is:

```text
STAGE-0 → STAGE-1 → STAGE-2 → STAGE-3 → STAGE-5
```

`STAGE-4-SNOWFLAKE.md` is optional and must not block a working localhost MVP. Read it only after Stage 5 or when live mode is specifically requested.

6. Determine the first incomplete stage on the critical path. Do not skip ahead unless the stage explicitly permits it.
7. Inspect existing code and tests before changing them.

## Mandatory stage protocol

For the first incomplete stage only:

1. State which stage you are starting.
2. Implement only that stage's scope.
3. Run its acceptance checks.
4. Do not replace working code with speculative abstractions.
5. Update that stage README's `Implementation status` section with:
   - Date/time
   - Files created or changed
   - Commands run
   - Test results
   - Known limitations
   - Next action
6. Update `CURRENT_STATE.md` with the same concise facts.
7. Create a local Git commit:

```text
stage-N: short description
```

8. After committing, stop and report the checkpoint. A later agent must be able to resume from the files alone.

## Git rules

- Initialize Git in Stage 0 if needed.
- Commit after every completed stage and after any important recovery fix.
- Never delete or rewrite prior commits.
- Do not push to GitHub or any remote unless the user explicitly asks.
- Never commit `.env`, credentials, Snowflake tokens, browser data, model secrets, or private CSVs.
- Keep the working tree clean at each checkpoint when practical.

## Credit and time rules

- Do not spend CoCo credits on brainstorming after implementation begins.
- Do not install Octagon, Calcbench, embeddings, Haystack, Cortex Search, or another model.
- Do not upgrade the model.
- Prefer fixture mode if Snowflake authentication slows development.
- If a stage is blocked for more than ten minutes, implement the documented fallback, record the blocker, commit, and continue only if the stage README allows it.

## Completion definition

The MVP is complete when Stage 5 is `DONE` and the app can:

```text
show a verified Apple revenue trend
+ calculate the change deterministically
+ cite filing evidence and accession IDs
+ call the local Ollama model
+ explain provenance and limitations
+ run in fixture mode without credentials
```
