# FilingForensics

Evidence-backed analysis of SEC filings using Snowflake Public Data, Snowflake CoCo, and a local open-weight model.

## Hack Day concept

FilingForensics answers focused questions about a company filing and shows the evidence behind every answer.

Example:

> What changed in Apple revenue from FY2022 to FY2023, and which filing section explains the change?

The application returns:

- A concise evidence-constrained answer
- The calculation and source values
- Filing form, accession, and filed date
- Relevant MD&A or risk-section evidence
- A limitation note when the evidence is incomplete

This is document analysis, not investment, legal, or compliance advice.

## Why this satisfies Best Use of Snowflake

```text
Snowflake CoCo
  -> schema discovery, SQL generation, join validation, and pipeline scaffolding

Snowflake Public Data (Free)
  -> SEC filing metadata, filing-section text, and structured financial facts

Open-source/open-weight AI
  -> local Qwen model synthesizes an answer only from retrieved evidence

Open-source application
  -> local Streamlit UI and Python retrieval/application code
```

## Verified Snowflake source

The account has the following installed source:

```text
Database: SNOWFLAKE_PUBLIC_DATA_FREE
Schema:   PUBLIC_DATA_FREE
```

Important views:

- `SEC_CIK_INDEX` — company metadata
- `SEC_CORPORATE_REPORT_INDEX` — filing metadata and `ADSH`
- `SEC_CORPORATE_REPORT_ITEM_ATTRIBUTES` — readable section text in `PLAINTEXT_CONTENT`
- `SEC_METRICS_TIMESERIES` — structured metrics with value, unit, and period dates
- `SEC_CORPORATE_REPORT_ATTRIBUTES` — raw XBRL line items
- `XBRL_TAXONOMY_INDEX` — taxonomy/tag descriptions

Verified join keys:

```text
CIK -> company
ADSH -> filing/accession
```

Do not join text rows and metric rows using `ON TRUE`. Retrieve and aggregate them separately, then combine the small results in application code.

## Verified demo data

Apple CIK:

```text
0000320193
```

Verified readable filing:

```text
ADSH:       0000320193-23-000106
Form:       10-K
Filed:      2023-11-03
Section:    PART II, Item 7 — MD&A
```

Verified revenue facts:

```text
FY2022: $394,328,000,000 USD
Period: 2021-09-26 to 2022-09-24
Source: 0000320193-24-000123

FY2023: $383,285,000,000 USD
Period: 2022-09-25 to 2023-09-30
Source: 0000320193-25-000079
```

Calculated change:

```text
Absolute change:  -$11.043B
Percent change:   approximately -2.8%
```

The UI must distinguish the source filing date from the financial period represented by a metric.

## Local model

Ollama is already installed locally.

```text
Model: qwen3.5:2b
Endpoint: http://127.0.0.1:11434
```

Use the Ollama `/api/generate` endpoint with:

```json
{
  "stream": false,
  "think": false,
  "options": {
    "temperature": 0,
    "num_predict": 400
  }
}
```

The model must receive retrieved evidence, not an unrestricted database dump.

## MVP scope

Build only this vertical slice:

1. Select Apple and a filing/question preset.
2. Retrieve one MD&A section from Snowflake.
3. Retrieve FY2022 and FY2023 total revenue facts from Snowflake.
4. Calculate the difference and percentage change deterministically in Python.
5. Send the question, evidence text, and numeric facts to Ollama.
6. Render an answer card with citations, calculation, provenance, and limitations.

Preset questions:

- What changed in revenue from FY2022 to FY2023?
- Which filing section provides context for that change?

## Non-goals for Hack Day

Do not add these before the MVP works:

- Octagon Marketplace installation
- Embeddings or vector databases
- Haystack
- Cortex Search
- Multi-agent orchestration
- Broad company coverage
- Investment recommendations
- Automated SEC downloading
- Production authentication
- Cloud deployment

## Run target

The preferred first implementation is a local Streamlit application:

```bash
streamlit run app.py
```

Required packages should be kept minimal:

```text
streamlit
snowflake-connector-python
pandas
requests
python-dotenv
```

Use Snowflake live mode when credentials are available. Include a small fixture mode containing only the verified Apple evidence so the UI can still be demonstrated if external-browser authentication fails.

Never commit Snowflake credentials, tokens, `.env` files, or private browser data.

## Safety and provenance rules

- Use only retrieved filing evidence.
- Never invent a missing metric or quote.
- Show accession, filing date, form, and period dates.
- State when narrative text and numeric facts come from different filing accessions.
- Calculate changes in deterministic Python code, not in the language model.
- If evidence is insufficient, say so.
- Include: `Not investment, legal, or compliance advice.`

## Submission story

FilingForensics turns Snowflake's difficult SEC EAV-style data into an auditable user experience. CoCo is used for genuine schema and query work, Snowflake is the data plane, and the open-weight local model is constrained to explain retrieved evidence rather than fabricate financial commentary.
