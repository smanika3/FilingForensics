# FilingForensics — Coding Agent Handoff

## Mission

Build a working local demo in approximately three hours. Do not broaden scope. The demo must answer one evidence-backed Apple filing question using Snowflake data and a local open-weight model.

Primary question:

> What changed in Apple revenue from FY2022 to FY2023, and which filing section provides context?

## Hard constraints

- Local-first; target a 16 GB Apple Silicon M3.
- Use Ollama and the already-installed `qwen3.5:2b` model.
- Use Snowflake Public Data (Free) as the primary data source when live credentials are available.
- The application must work in fixture/demo mode without live Snowflake authentication.
- Do not install Octagon, Calcbench, embeddings, Haystack, Cortex Search, or another model.
- Do not expose or commit credentials.
- Do not give investment, legal, or compliance advice.
- Never fabricate a quote, metric, filing, or source.

## Required output

Create a small local Streamlit application with:

The application is not a generic API-call chatbot. Its product core must remain the evidence/reconciliation pipeline: period-aware metric selection, independent text retrieval, deterministic calculations, provenance, validation, and citation rendering. The local model is only a bounded explanation layer. The app must still produce a useful deterministic evidence result when Ollama is unavailable.

Snowflake has native Cortex AI Functions and other managed AI features, but they are account/privilege/credit dependent. Keep Ollama as the default local open-weight path for the MVP. A future `SnowflakeCortexSynthesizer` adapter may be added after the MVP; do not add it before the fixture-first demo works.

1. Sidebar or top controls:
   - Company preset: Apple Inc.
   - Question preset: revenue change FY2022 to FY2023
   - Data mode: fixture or Snowflake
2. Main answer card:
   - One-sentence answer
   - Absolute and percentage change
   - Numeric evidence table
   - Narrative evidence excerpt
   - Provenance fields
   - Limitations/safety note
3. A debug/evidence expander showing:
   - SQL used
   - Retrieved row counts
   - Model name
   - Model latency if available

## Suggested project layout

```text
filingforensics/
  app.py
  requirements.txt
  .env.example
  README.md
  src/
    __init__.py
    config.py
    models.py
    fixtures.py
    snowflake_client.py
    retrieval.py
    calculations.py
    ollama_client.py
    answer_schema.py
  tests/
    test_calculations.py
    test_fixtures.py
```

Keep imports and execution simple. The app must run with `streamlit run app.py`.

## Verified Snowflake identifiers

```text
Database: SNOWFLAKE_PUBLIC_DATA_FREE
Schema:   PUBLIC_DATA_FREE
```

Views:

```text
SEC_CIK_INDEX
SEC_CORPORATE_REPORT_INDEX
SEC_CORPORATE_REPORT_ITEM_ATTRIBUTES
SEC_METRICS_TIMESERIES
```

Apple:

```text
CIK: 0000320193
```

Verified readable MD&A filing:

```text
ADSH: 0000320193-23-000106
FORM_TYPE: 10-K
FILED_DATE: 2023-11-03
ITEM_NUMBER: PART II, Item 7
```

Verified total revenue rows:

```text
FY2022: 394328000000 USD
PERIOD: 2021-09-26 through 2022-09-24
ADSH: 0000320193-24-000123

FY2023: 383285000000 USD
PERIOD: 2022-09-25 through 2023-09-30
ADSH: 0000320193-25-000079
```

## Retrieval contract

Return two independent result objects:

```python
text_evidence = {
    "cik": "0000320193",
    "adsh": "0000320193-23-000106",
    "form_type": "10-K",
    "filed_date": "2023-11-03",
    "item_number": "PART II, Item 7",
    "item_title": "Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "text": "..."
}

metric_evidence = [
    {
        "fiscal_year": 2022,
        "value": 394328000000,
        "unit": "USD",
        "period_start": "2021-09-26",
        "period_end": "2022-09-24",
        "adsh": "0000320193-24-000123",
        "filed_date": "2024-11-01",
        "variable_name": "NET SALES | ANNUAL"
    },
    {
        "fiscal_year": 2023,
        "value": 383285000000,
        "unit": "USD",
        "period_start": "2022-09-25",
        "period_end": "2023-09-30",
        "adsh": "0000320193-25-000079",
        "filed_date": "2025-10-31",
        "variable_name": "NET SALES | ANNUAL"
    }
]
```

Do not join every text row to every metric row. Retrieval and filtering must happen separately. Combine only the small selected results in Python.

## Snowflake SQL

Text query:

```sql
SELECT
    CIK,
    ADSH,
    FORM_TYPE,
    FILED_DATE,
    ITEM_NUMBER,
    ITEM_TITLE,
    LEFT(PLAINTEXT_CONTENT, 8000) AS TEXT
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.SEC_CORPORATE_REPORT_ITEM_ATTRIBUTES
WHERE CIK = '0000320193'
  AND ADSH = '0000320193-23-000106'
  AND ITEM_NUMBER = 'PART II, Item 7';
```

Metric query:

```sql
WITH filings AS (
    SELECT DISTINCT
        ADSH,
        FORM_TYPE,
        FILED_DATE
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.SEC_CORPORATE_REPORT_INDEX
    WHERE CIK = '0000320193'
      AND FORM_TYPE = '10-K'
)
SELECT
    m.ADSH,
    f.FORM_TYPE,
    f.FILED_DATE,
    TRY_TO_NUMBER(TO_VARCHAR(m.FISCAL_YEAR)) AS FISCAL_YEAR,
    m.FISCAL_PERIOD,
    m.VARIABLE_NAME,
    m.VALUE,
    m.UNIT,
    m.PERIOD_START_DATE,
    m.PERIOD_END_DATE
FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.SEC_METRICS_TIMESERIES m
JOIN filings f
    ON m.ADSH = f.ADSH
WHERE m.CIK = '0000320193'
  AND m.TAG = 'RevenueFromContractWithCustomerExcludingAssessedTax'
  AND m.FISCAL_PERIOD = 'FY'
  AND TRY_TO_NUMBER(TO_VARCHAR(m.FISCAL_YEAR)) IN (2022, 2023)
  AND m.VARIABLE_NAME = 'NET SALES | ANNUAL'
  AND m.BUSINESS_SEGMENT IS NULL
  AND m.BUSINESS_SUBSEGMENT IS NULL
ORDER BY FISCAL_YEAR;
```

The application may use parameterized SQL for future companies, but hardcoded Apple preset values are acceptable for the hackathon MVP.

## Deterministic calculations

Implement calculations outside the LLM:

```python
old = 394328000000
new = 383285000000
absolute_change = new - old
percent_change = (absolute_change / old) * 100
```

Expected:

```text
absolute_change = -11043000000
percent_change ≈ -2.8007%
```

Format for UI:

```text
Revenue decreased by $11.04B, or 2.8%, from FY2022 to FY2023.
```

Validate:

- Exactly one total annual row per target fiscal year.
- `UNIT == USD`.
- No segment fields for total revenue rows.
- Period dates exist.
- The two periods are adjacent/non-overlapping as expected.

## Ollama contract

Endpoint:

```text
POST http://127.0.0.1:11434/api/generate
```

Request:

```json
{
  "model": "qwen3.5:2b",
  "stream": false,
  "think": false,
  "options": {
    "temperature": 0,
    "num_predict": 400
  },
  "prompt": "..."
}
```

Prompt template:

```text
You are FilingForensics, an evidence-constrained SEC filing assistant.

Use only the supplied evidence. Do not invent facts, quotes, causes, or citations.
If the evidence does not support a claim, say that it is not established.
Do not provide investment, legal, or compliance advice.

Return JSON with these fields:
- answer: concise answer
- calculation: explain the numeric change
- narrative_evidence: explain which supplied passage is relevant
- citations: array of source identifiers
- limitations: array of limitations

Question:
{question}

Numeric evidence:
{metric_evidence}

Narrative evidence:
{text_evidence}
```

If JSON parsing fails, show the raw model response in the evidence expander and use the deterministic calculation as the visible primary answer. Do not let malformed model JSON crash the app.

## Fixture mode

Fixture mode is mandatory so the demo works without live Snowflake credentials. Include the verified metric rows and a short MD&A excerpt from the user-provided Snowflake query output. Mark the UI clearly:

```text
Fixture mode — using verified sample evidence
```

Live mode should be optional and should fail gracefully with a visible error and a button/instruction to switch to fixture mode.

## Three-hour execution order

### 0–15 minutes: environment

- Confirm `ollama list` includes `qwen3.5:2b`.
- Create project files.
- Create virtual environment if desired.
- Install minimal dependencies.
- Confirm a one-line Ollama request works with `think: false`.

### 15–45 minutes: core logic

- Implement fixture data.
- Implement deterministic calculation and validation.
- Implement Ollama client.
- Add unit tests for the calculation.

### 45–90 minutes: UI

- Build Streamlit answer card.
- Add evidence/provenance sections.
- Add fixture/live mode selector.
- Handle Ollama and Snowflake errors.

### 90–125 minutes: local demo hardening

- Verify the complete fixture → calculation → Ollama → Streamlit path.
- Add graceful Ollama failure behavior.
- Add evidence/provenance and limitation rendering.
- Keep the app usable with no Snowflake credentials.

### 125–145 minutes: optional Snowflake live path

Only attempt this if the local MVP is already working. Otherwise skip it and record `STAGE-4` as optional.

- Implement optional connector.
- Use environment variables only.
- Run the two verified queries.
- Normalize rows into the retrieval contract.

### 145–160 minutes: polish and evidence

- Add citations and limitation text.
- Add SQL/model debug expander.
- Record CoCo prompts and screenshots separately.
- Add README run instructions.
- Test fresh launch in fixture mode.

### 160–180 minutes: demo rehearsal

Demo sequence:

1. Show CoCo prompt/schema discovery evidence.
2. Show installed Snowflake SEC dataset.
3. Open FilingForensics.
4. Ask the revenue-change question.
5. Show deterministic calculation.
6. Expand filing evidence and provenance.
7. Explain local open-weight model and safety boundary.

## Acceptance criteria

The MVP is done when:

- `streamlit run app.py` launches.
- Fixture mode works without credentials.
- The UI displays the expected -$11.043B / -2.8% result.
- The answer cites the MD&A section and both metric accessions.
- Source filing date and financial period are both visible.
- The local Qwen model is used in the answer path or its failure is clearly handled.
- No Cartesian text/fact join exists.
- No secrets are committed.
- The app states that it is not investment, legal, or compliance advice.
- A five-question or five-case smoke-test checklist is recorded, even if only one question is user-facing.

## What not to do if time is running out

Keep fixture mode, deterministic calculations, evidence citations, and the polished demo. Remove live Snowflake mode before removing those. Do not spend the final hour on embeddings, deployment, or model upgrades.
