# FilingForensics — Architecture and Stack

## Product shape

FilingForensics is a local-first evidence-review application. It answers a narrow filing question and exposes the evidence, calculation, provenance, and limitations instead of returning unsupported financial commentary.

## Runtime architecture

```text
User
  ↓
Streamlit frontend
  ↓
Python application/orchestration layer
  ├── retrieval adapter
  │     ├── fixture data (always available)
  │     └── Snowflake connector (optional live mode)
  ├── deterministic calculation module
  ├── evidence/provenance normalizer
  └── Ollama client
          ↓
      qwen3.5:2b on localhost
```

There is no separate backend service in the MVP. Streamlit invokes the Python modules directly. This reduces setup, debugging, and deployment risk within the three-hour window.

## Frontend

- Streamlit
- Localhost first
- One page with:
  - question/company controls
  - answer card
  - metric table/chart
  - narrative evidence expander
  - provenance and limitations
  - debug/evidence expander
  - fixture/live mode indicator

## Application layer

Python modules should separate concerns:

- `config.py` — environment variables and safe defaults
- `models.py` — typed evidence/result objects
- `fixtures.py` — verified Apple evidence
- `snowflake_client.py` — optional parameterized read-only queries
- `retrieval.py` — fetch text and metrics independently
- `calculations.py` — deterministic revenue change calculations
- `ollama_client.py` — local REST call with timeout and fallback
- `answer_schema.py` — tolerant model-output parsing

## Data layer

Snowflake source:

```text
SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE
```

Views:

```text
SEC_CORPORATE_REPORT_INDEX
SEC_CORPORATE_REPORT_ITEM_ATTRIBUTES
SEC_METRICS_TIMESERIES
```

Use `ADSH` for filing provenance. Never use `LEFT JOIN ... ON TRUE` between text and metrics. Retrieve selected text and selected metrics independently, then combine the small results in Python.

Financial metrics must retain both:

- The source filing accession and filed date
- The financial period and fiscal year represented

## Product core versus model layer

The product is not a generic LLM wrapper. The core value is the evidence/reconciliation pipeline:

```text
filing selection
  → period-aware metric normalization
  → independent narrative retrieval
  → deterministic calculations and validation
  → provenance/evidence bundle
  → optional language-model explanation
```

The language model is the final explanation layer, not the source of truth. It must not select unsupported metrics, perform the authoritative calculation, invent causes, or create citations.

### Primary three-hour model path: Ollama

- Ollama local REST API
- Model: `qwen3.5:2b`
- `think: false`
- Temperature 0
- Short bounded output
- Evidence-only prompt
- Deterministic calculations remain outside the model

### Optional Snowflake-native model path

Snowflake Cortex AI Functions can be used later as an alternative synthesis adapter if the account has the required privileges and credits. Cortex-hosted models run inside Snowflake and are callable from SQL/Python. This mode must not replace fixture mode or the deterministic evidence pipeline.

The application should eventually support a model adapter interface:

```text
EvidenceSynthesizer
  ├── OllamaSynthesizer        # default local demo
  └── SnowflakeCortexSynthesizer # optional account-dependent mode
```

Do not attempt Snowpark Container Services or a custom Ollama container during the three-hour MVP. Those are valid Snowflake model-serving directions, but require additional container, compute, and deployment work.

If any model fails or returns malformed JSON, show the deterministic result and raw model response in a debug expander. The app must not crash.

## Why this is not an API-call demo

The application remains meaningful even with the language model disabled. It still:

- selects the correct filing and financial period;
- prevents text/fact Cartesian joins;
- normalizes metric provenance across filing accessions;
- calculates changes deterministically;
- exposes the exact evidence used;
- validates missing/duplicate/conflicting facts; and
- renders an auditable answer bundle.

The model adds grounded explanation and natural-language presentation to that evidence bundle.

## Configuration

Use environment variables only for live Snowflake mode:

```text
SNOWFLAKE_ACCOUNT
SNOWFLAKE_USER
SNOWFLAKE_PASSWORD  # optional and never committed
SNOWFLAKE_WAREHOUSE
SNOWFLAKE_DATABASE
SNOWFLAKE_SCHEMA
```

Support fixture mode with no environment variables. Add `.env.example`, never `.env`.

## Testing

- Unit tests for calculations and evidence validation
- Fixture-mode smoke test
- Ollama client timeout/failure test
- Optional Snowflake live test, skipped when credentials are absent

## Explicit non-goals

- No separate FastAPI backend
- No authentication system
- No cloud deployment requirement
- No embeddings/vector database
- No multi-agent system
- No investment recommendation engine
- No broad production data platform
