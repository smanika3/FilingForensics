"""Snapshot curated companies x metrics from Snowflake into src/fixture_data.json (read-only queries).

Usage: SNOWFLAKE_CONNECTION_NAME=<conn> .venv/bin/python scripts/refresh_fixtures.py
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.companies import CURATED  # noqa: E402
from src.fixture_store import FIXTURE_PATH, encode_blocks  # noqa: E402
from src.metrics import METRICS  # noqa: E402
from src.retrieval import LiveModeUnavailable  # noqa: E402
from src.snowflake_client import fetch_live_evidence, latest_fiscal_year  # noqa: E402

YEARS_BACK = 3  # facts for latest-3 .. latest


def main() -> None:
    out = {"source": "SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE", "companies": {}}
    for company in CURATED:
        latest = latest_fiscal_year(company.cik)
        entry = {"name": company.name, "ticker": company.ticker, "latest_year": latest, "facts": {}, "mdna": {}}
        for key in METRICS:
            facts = {}
            for new_year in range(latest - YEARS_BACK + 1, latest + 1):
                try:
                    bundle = fetch_live_evidence(company.cik, company.name, key, (new_year - 1, new_year))
                except LiveModeUnavailable as exc:
                    print(f"  skip {company.ticker} {key} FY{new_year}: {exc}")
                    continue
                for m in bundle.metrics:
                    facts.setdefault((m.fiscal_year, m.value), asdict(m))
                if bundle.text is not None:
                    mdna = entry["mdna"].setdefault(
                        str(new_year), {"filing": {k: v for k, v in asdict(bundle.text).items() if k != "text"}, "excerpts": {}}
                    )
                    mdna["excerpts"][key] = encode_blocks(bundle.text_blocks)
            entry["facts"][key] = sorted(facts.values(), key=lambda f: f["fiscal_year"])
            print(f"{company.ticker:5} {key:20} years={[f['fiscal_year'] for f in entry['facts'][key]]}")
        out["companies"][company.cik] = entry
    FIXTURE_PATH.write_text(json.dumps(out, indent=1))
    print(f"wrote {FIXTURE_PATH} ({FIXTURE_PATH.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
