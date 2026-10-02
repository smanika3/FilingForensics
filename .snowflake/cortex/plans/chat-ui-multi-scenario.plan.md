---
name: "chat-ui-multi-scenario"
created: "2026-10-02T21:25:05.751Z"
status: pending
---

# Plan: Chat UI + multi-company, multi-metric queries

## Findings (verified read-only in Snowflake)

- **Table bug:** MD\&A `PLAINTEXT_CONTENT` embeds raw HTML `<table>` markup, so `st.text` shows code.
- **More scenarios:** `SEC_CORPORATE_REPORT_ATTRIBUTES` holds the full XBRL facts per 10-K. Clean totals = `METADATA IS NULL`. Duration facts (revenue, net income…) use `COVERED_QTRS = 4`; balance-sheet facts (assets…) use `COVERED_QTRS = 0` with start = end date. Each 10-K carries the current and prior year, so both values share one accession. Duplicate identical rows exist (dedupe); differing values are a conflict and are rejected.
- MD\&A (`PART II, Item 7`) exists for **2022+ 10-Ks** of large filers. Older years get metrics only, with a clear note.
- Revenue tag varies by company (`RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet`, …), so try them in priority order.
- `SEC_CIK_INDEX` (CIK, COMPANY\_NAME, FISCAL\_YEAR\_END) and `COMPANY_INDEX` (PRIMARY\_TICKER, CIK) support name/ticker resolution.

## 1. Narrative rendering fix — `src/mdna.py` (new)

- Split MD\&A text into ordered blocks: paragraphs and tables. Parse `<table>` with stdlib `html.parser` into rows and drop empty spacer cells.
- `relevant_excerpt(text, metric)` picks the paragraphs/tables that mention the metric's keywords (e.g. "net sales", "gross margin", "research and development"), capped at about 3,000 characters. This also cuts model latency, since we no longer send 8,000 characters.
- UI renders paragraphs with `st.markdown` (with `$` escaped) and tables with `st.dataframe`.

## 2. Query understanding — `src/query_parser.py` (new)

- `ParsedQuery(company_text, cik?, metric_key, old_year, new_year)`.
- **Metric catalog** (`src/metrics.py`): revenue, net income, gross profit, operating income, R\&D expense, diluted EPS (USD/share), operating cash flow, total assets, total liabilities. Each entry has XBRL tag(s), kind (`duration` | `instant`), keywords, and MD\&A keywords.
- **Rules first:** match curated company names/tickers, metric keywords/synonyms, and years (`FY2023`, `2022 to 2023`, "last year" defaults to the latest pair). If only one year is given, compare it to the prior year.
- **LLM fallback** (only when the rules can't resolve company or metric): Qwen with `format=json`, constrained to the allowed metric keys. The result is validated, and anything invalid becomes a friendly "try e.g. …" hint. The LLM never supplies numbers.

## 3. Company resolution — `src/companies.py` (new)

- Curated list (\~10, CIKs verified): Apple, Microsoft, NVIDIA, Amazon, Alphabet, Meta, Tesla, JPMorgan, Coca-Cola, Netflix. These are shown as a preview above the chat box.

- Unknown company in live mode: a quick parameterized lookup (`COMPANY_INDEX.PRIMARY_TICKER = %s` or `SEC_CIK_INDEX.COMPANY_NAME ILIKE %s`, `LIMIT 5`).

  - 0 matches: "Company not found in SEC data".
  - More than 1: show the top matches as clickable choices.
  - Exactly 1: proceed.

- Fixture mode: curated companies only, with an explanatory message otherwise.

## 4. Generalized retrieval — `src/snowflake_client.py`, `src/retrieval.py`

- `fetch_facts(cik, metric, new_year)`: pick the 10-K whose `FISCAL_YEAR = new_year` from `SEC_CORPORATE_REPORT_INDEX`, then read the two latest clean periods for the metric's tags from that one filing. All values are bound parameters; text and facts are still retrieved independently.
- `fetch_mdna(adsh)`: full text for that filing, then `relevant_excerpt` in Python.
- `fetch_live_evidence(parsed)` returns the same `EvidenceBundle`, now including `company_name` and `metric`.
- Keep the existing Apple revenue path working, so the current tests and verified values stay valid.

## 5. Generalized calculation — `src/calculations.py`

- Rename to `metric_change()` with a `revenue_change()` wrapper kept for the tests. Unit rule: `USD` or `USD/shares` per the metric.
- Adjacency check for duration metrics; for instant metrics, check that the period ends are about one year apart.
- Formatting: `$X.XXB` for USD and `$X.XX` for EPS. Summary text names the metric and company.

## 6. Fixtures — `src/fixture_data.json` + `scripts/refresh_fixtures.py`

- The script (run manually, read-only) snapshots the curated companies × all metrics for their latest MD\&A year pair, plus the relevant MD\&A excerpts, into JSON (well under 1 MB).
- Fixture mode loads the JSON, so offline queries cover \~10 companies × 9 metrics. The existing Apple revenue fixture stays as the verified baseline.

## 7. Chat-style UI — `app.py`

- `layout="centered"`. The sidebar keeps only the settings (data mode, model toggle).

- **Landing state:** vertical spacer, then title and caption, then curated company **pills** plus a few example-question pills (clicking fills the box), then a centered `st.form` with a `text_input` and a send button.

- **After submit:** the query bar moves to the top (same form, prefilled with the last question), and results render below:

  - answer card
  - model explanation
  - metric table/chart
  - narrative paragraphs plus real tables
  - provenance/limitations
  - debug

- **Interactive progress** via `st.status`, updated step by step with an elapsed time per step:

  1. Understanding question (rules / LLM fallback)
  2. Resolving company
  3. Querying financial facts (Snowflake or fixtures)
  4. Retrieving MD\&A narrative
  5. Calculating change deterministically
  6. Asking qwen3.5:2b to explain evidence
  7. Done, after which the status collapses

- Errors at any step mark the status as `error` with a recovery hint (fixture switch, rephrase, pick a company).

## 8. Tests

- `test_mdna.py`: table parsing and excerpt selection.
- `test_query_parser.py`: rules for several phrasings, single year, ticker, unknown company, LLM fallback mocked, invalid LLM output rejected.
- `test_companies.py`: lookup 0/1/many (mocked).
- Extend `test_snowflake_client.py`: fact dedupe/conflict, instant vs duration, SQL read-only and parameterized.
- Update `test_app.py` (AppTest): landing has the text input, submit renders the answer, model failure and live failure are recoverable.
- Live checks (opt-in): Microsoft net income, NVIDIA revenue, an unknown-company lookup.

## 9. Docs/commit

- Update README (new query examples, metric catalog, fixture refresh) and CURRENT\_STATE.md (new stage "6: chat UI + multi-scenario").
- Local commit only; push when you ask.

## Notes / tradeoffs

- The rules parser handles common phrasings instantly; the LLM fallback adds about 3–5s only when needed.
- For companies outside the curated list, MD\&A or facts may be missing. That's handled with clear messages and metrics-only answers.
- No new dependencies (stdlib HTML parsing).
