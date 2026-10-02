# FilingForensics

**Evidence-First SEC 10-K Filing Intelligence & Financial Verification Engine**

FilingForensics answers complex natural-language questions about public company annual reports (SEC Forms 10-K) by pairing **deterministic arithmetic** with **strictly cited narrative evidence**. 

Unlike standard LLM applications that rely on generative models to extract numbers and do arithmetic (frequently causing subtle hallucinations), FilingForensics enforces an architectural boundary:
* **All numbers and percentage changes are computed deterministically in Python** from raw XBRL facts.
* **A local open-weight language model (Qwen 2.5 via Ollama) is used solely to summarize and explain the verified narrative evidence** (Management's Discussion & Analysis — Part II, Item 7).
* **Every fact, table, and explanation includes SEC Accession Number (ADSH) citations** back to the underlying 10-K filings.

*Not investment, legal, or compliance advice.*

---

## Capabilities & Highlights

* **Any-Company Support:** 
  * 10 curated tech and industry leaders with built-in aliases (Apple, Microsoft, NVIDIA, Amazon, Alphabet/Google, Meta, Tesla, JPMorgan Chase, Coca-Cola, Netflix).
  * In Live Mode, queries any public SEC filer using dynamic ticker/name resolution against SEC CIK indices.
* **9 Supported Financial Metrics:** 
  * Full-statement coverage across Income Statement (Revenue, Net Income, Gross Profit, Operating Income, R&D), Balance Sheet (Total Assets, Total Liabilities), Cash Flow (Operating Cash Flow), and Per-Share Facts (Diluted EPS).
* **Natural Language Parsing:** 
  * Hybrid rule-based parsing (<1ms) with local LLM fallback for multi-clause questions, synonyms, and multi-year comparisons.
* **Preserved Financial Tables:** 
  * Extracts Part II, Item 7 (MD&A) and renders structured HTML financial tables natively in Streamlit with merged currency and parenthetical negative formatting.
* **Dual Execution Modes:** 
  * **Offline Fixture Mode:** Instant, air-gapped demo mode using verified multi-year snapshots (no credentials required).
  * **Live Snowflake Mode:** Direct, read-only parameterized queries against `SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE`.
* **Zero Cloud LLM Dependency:** 
  * Runs 100% locally via Ollama (`qwen3.5:2b` on localhost). Zero financial queries or filing text are sent to third-party model APIs.

---

## Quickstart (Offline Fixture Mode)

Get started immediately with zero credentials:

```bash
# 1. Clone repository and create virtual environment
git clone https://github.com/smanika3/FilingForensics.git
cd FilingForensics
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Pull local explanation model (optional; deterministic math works without it)
ollama pull qwen3.5:2b

# 3. Run test suite
pytest -q    # 55 passed, 3 skipped

# 4. Launch web application
streamlit run app.py
```

Open `http://localhost:8501`. Type a query (e.g. *"How did Apple's revenue change from FY2022 to FY2023?"*) or click any curated company pill.

---

## Live Snowflake Mode

Live mode queries live 10-K filings and MD&A narratives directly from Snowflake Marketplace's free SEC dataset (`SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE`).

### Authentication Setup

FilingForensics supports `.env` configuration as well as automatic discovery of connections in `~/.snowflake/connections.toml`:

```bash
# Create a .env file (already included in .gitignore)
cp .env.example .env
```

Set either:
1. **Named Connection (Recommended):**
   ```bash
   SNOWFLAKE_CONNECTION_NAME=vlwhdrb-kb51087
   ```
2. **Direct Credentials:**
   ```bash
   SNOWFLAKE_ACCOUNT=<account_identifier>
   SNOWFLAKE_USER=<username>
   # Optional: defaults to externalbrowser SSO if password is not provided
   SNOWFLAKE_AUTHENTICATOR=externalbrowser
   ```

### Running Live Queries
Switch the sidebar toggle to **Data mode = live** or pass `FF_MODE=live`:

```bash
streamlit run app.py
```

Try live queries for any company or year:
* *"Compare Google's revenue from 2023 to 2024"*
* *"Microsoft net income 2023 vs 2024"*
* *"What was NVIDIA's diluted EPS in the latest year?"*

---

## Supported Financial Metrics

| Metric Key | Metric Name | Category | Primary XBRL Tags |
| :--- | :--- | :--- | :--- |
| `revenue` | Revenue / Net Sales | Income Statement | `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet` |
| `net_income` | Net Income / Profit | Income Statement | `NetIncomeLoss`, `ProfitLoss` |
| `gross_profit` | Gross Profit | Income Statement | `GrossProfit` |
| `operating_income` | Operating Income / EBIT | Income Statement | `OperatingIncomeLoss` |
| `rnd` | Research & Development | Income Statement | `ResearchAndDevelopmentExpense` |
| `eps_diluted` | Diluted EPS | Per-Share Fact | `EarningsPerShareDiluted` |
| `operating_cash_flow` | Operating Cash Flow | Cash Flow Statement | `NetCashProvidedByUsedInOperatingActivities` |
| `total_assets` | Total Assets | Balance Sheet | `Assets` |
| `total_liabilities` | Total Liabilities | Balance Sheet | `Liabilities` |

---

## Architecture & Codebase Map

```text
app.py                    Streamlit UI: centered landing, live telemetry, and results
src/
  ├── config.py           Environment config and automatic .env loading
  ├── query_parser.py     Hybrid regex rules + local LLM question parser
  ├── companies.py        Curated company directory and SEC ticker/alias resolution
  ├── metrics.py          Metric catalog, XBRL priority tags, and keywords
  ├── retrieval.py        EvidenceBundle contracts and mode dispatching
  ├── fixture_store.py    Offline snapshot loader and encoder
  ├── snowflake_client.py Live read-only parameterized Snowflake client & connection resolver
  ├── calculations.py     Deterministic change arithmetic and validation checks
  ├── mdna.py             Part II Item 7 parser, table extractor, and relevance ranker
  ├── models.py           Immutable dataclasses (MetricEvidence, TextEvidence, MetricChange)
  ├── ollama_client.py    Localhost Ollama caller with timeout and prompt construction
  └── answer_schema.py    Tolerant JSON schema parser with graceful fallback
scripts/
  └── refresh_fixtures.py Multi-company multi-metric fixture refresh snapshot tool
tests/                    55 automated tests (unit, app flow, calculations, live Snowflake)
```

---

## Integrity & Anti-Hallucination Guardrails

1. **Independent Filing Isolation:** Metrics are drawn directly from each year's primary 10-K filing to avoid distortion from subsequent revisions or restatements across filings.
2. **Period Matching & Units:** Prevents comparing mismatched durations (e.g. 1 quarter vs 4 quarters) or mixed currencies.
3. **Strict Model Grounding:** The prompt provides pre-calculated figures as authoritative facts. The model is temperature-locked (`temperature=0.0`) with `think=false` and must strictly cite the provided accessions.
4. **Resilient Fallback:** If the local model is offline or produces malformed JSON, the application automatically displays the deterministic calculation and narrative evidence tables with an explanatory warning.

---

## Testing

```bash
# Run standard offline test suite (55 tests)
.venv/bin/pytest tests/

# Run live Snowflake integration tests (requires active Snowflake connection)
FF_LIVE_SNOWFLAKE=1 .venv/bin/pytest tests/test_snowflake_client.py -k test_live_snowflake
```
