# FilingForensics

Evidence-first SEC filing review. FilingForensics answers a narrow filing question — *how did Apple's total revenue change from FY2022 to FY2023, and what does the MD&A say about it?* — and shows the evidence, deterministic calculation, provenance, and limitations behind the answer. A local open-weight model (Qwen via Ollama) only explains the supplied evidence; it is never the source of truth.

Not investment, legal, or compliance advice.

## Quick start (fixture mode, no credentials)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ollama pull qwen3.5:2b          # once; app still works if Ollama is down
.venv/bin/python -m pytest -q   # 21 passed, 1 skipped
.venv/bin/streamlit run app.py  # http://localhost:8501
```

In the sidebar keep **Data mode = fixture**, leave **Explain with local model** on, and click **Analyze**. The model explanation takes ~14s on `qwen3.5:2b`.

Optional live Ollama smoke test: `FF_LIVE_OLLAMA=1 .venv/bin/python -m pytest -q -s tests/test_ollama_client.py::test_live_ollama_smoke`

Configuration (all optional) is documented in `.env.example`. Never commit `.env`.

## Expected result

| | Value | Source accession | Period |
|---|---|---|---|
| FY2022 net sales | $394,328,000,000 | 0000320193-24-000123 | 2021-09-26 → 2022-09-24 |
| FY2023 net sales | $383,285,000,000 | 0000320193-25-000079 | 2022-09-25 → 2023-09-30 |
| Change | **−$11,043,000,000 (−2.8005%)** | computed in Python | |

Narrative evidence: Apple 10-K `0000320193-23-000106`, filed 2023-11-03, PART II Item 7 (MD&A): *"total net sales decreased 3% or $11.0 billion during 2023 compared to 2022."*

## Architecture

```text
Streamlit (app.py)  — single local process, no separate backend
  ├── src/retrieval.py      text and metrics fetched independently (no text×metric join)
  │     ├── src/fixtures.py         verified Apple evidence (always available)
  │     └── live Snowflake mode     optional Stage 4, not implemented → graceful error
  ├── src/calculations.py   deterministic change + validation (missing/duplicate/non-USD/segment/non-adjacent)
  ├── src/models.py         typed evidence objects, USD formatting
  ├── src/ollama_client.py  localhost-only Ollama call: think=false, temperature 0, JSON format, timeout
  └── src/answer_schema.py  tolerant JSON parsing; structured fallback on any failure
```

### Roles

- **Snowflake source:** `SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE` (SEC_CORPORATE_REPORT_INDEX, SEC_CORPORATE_REPORT_ITEM_ATTRIBUTES, SEC_METRICS_TIMESERIES). Fixture values were verified against this source; the MD&A excerpt was retrieved read-only by Cortex Code.
- **Cortex Code (CoCo):** schema/query discovery, verification of the Apple metric rows and MD&A filing, and staged implementation of this repo (see `FilingForensics-agent-handoff/`).
- **Open-weight model:** `qwen3.5:2b` served locally by Ollama at `127.0.0.1:11434`. Non-localhost hosts are refused. The model receives the deterministic result as authoritative and only writes the explanation.

## Five-case smoke checklist

| # | Case | Expected | Verified by |
|---|---|---|---|
| 1 | Fixture mode, normal evidence | −$11.04B / −2.8% answer, evidence, provenance, model explanation | `tests/test_app.py::test_fixture_mode_without_model` + manual browser run with live Qwen (14.3s) |
| 2 | Fixture mode, Ollama unavailable | Warning + deterministic answer, no crash | `tests/test_app.py::test_model_failure_does_not_crash`; real closed port → `Ollama unavailable at http://127.0.0.1:11999` |
| 3 | Missing metric row | `EvidenceError: FY2022: no total annual revenue row` shown | `tests/test_calculations.py::test_missing_year_rejected` |
| 4 | Duplicate metric row | `EvidenceError: ... duplicate total annual revenue rows` | `tests/test_calculations.py::test_duplicate_row_rejected` |
| 5 | Live mode unavailable | Visible error telling user to switch to fixture mode | `tests/test_app.py::test_live_mode_fails_gracefully` |

## Demo sequence

1. Show the CoCo schema/query work (the read-only SEC queries in `FilingForensics-agent-handoff/CODING-AGENT-HANDOFF.md`).
2. Show the installed `SNOWFLAKE_PUBLIC_DATA_FREE` SEC source in Snowsight.
3. Run `.venv/bin/streamlit run app.py` and open http://localhost:8501.
4. Select the Apple revenue question and click **Analyze**.
5. Point to the deterministic calculation line under the answer.
6. Expand **Narrative evidence** and **Provenance and limitations**.
7. Explain that Qwen runs locally through Ollama (caption shows model + latency; **Debug** shows raw JSON).
8. Show the limitations list and the non-advice boundary.

## Known limitations

- Single preset: Apple, total net sales, FY2022 vs FY2023.
- Metric rows come from later 10-K filings (comparative periods), so their accessions differ from the MD&A filing.
- FY2023 had 53 weeks vs 52 for FY2022.
- Live Snowflake mode is not implemented (optional Stage 4).
- The model's own citation list usually omits the MD&A accession; the deterministic provenance section always lists all three.
- ~14s model latency on `qwen3.5:2b`.
