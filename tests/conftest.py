import json
import os

import pytest

import src.fixture_store as fs

APPLE = "0000320193"
SAMPLE = {
    "companies": {
        APPLE: {
            "name": "Apple Inc.", "ticker": "AAPL", "latest_year": 2023,
            "facts": {
                "revenue": [
                    {"fiscal_year": 2022, "value": 394328000000, "unit": "USD", "period_start": "2021-09-26",
                     "period_end": "2022-09-24", "adsh": "0000320193-22-000108", "filed_date": "2022-10-28",
                     "variable_name": "RevenueFromContractWithCustomerExcludingAssessedTax | Net sales",
                     "business_segment": None, "business_subsegment": None},
                    {"fiscal_year": 2023, "value": 383285000000, "unit": "USD", "period_start": "2022-09-25",
                     "period_end": "2023-09-30", "adsh": "0000320193-23-000106", "filed_date": "2023-11-03",
                     "variable_name": "RevenueFromContractWithCustomerExcludingAssessedTax | Net sales",
                     "business_segment": None, "business_subsegment": None},
                ],
            },
            "mdna": {
                "2023": {
                    "filing": {"cik": APPLE, "adsh": "0000320193-23-000106", "form_type": "10-K", "filed_date": "2023-11-03",
                               "item_number": "PART II, Item 7", "item_title": "MD&A"},
                    "excerpts": {"revenue": [
                        {"p": "The Company's total net sales decreased 3% or $11.0 billion during 2023 compared to 2022."},
                        {"table": [["", "2023", "Change", "2022"], ["Total net sales", "$383,285", "(3)%", "$394,328"]]},
                    ]},
                }
            },
        }
    }
}


@pytest.fixture(autouse=True)
def sample_fixtures(tmp_path, monkeypatch):
    """Point fixture mode at a small sample so tests don't depend on the full snapshot."""
    path = tmp_path / "fixture_data.json"
    path.write_text(json.dumps(SAMPLE))
    monkeypatch.setattr(fs, "FIXTURE_PATH", path)
    fs._load.cache_clear()
    if not os.getenv("FF_LIVE_SNOWFLAKE"):
        for key in ("SNOWFLAKE_CONNECTION_NAME", "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER"):
            monkeypatch.delenv(key, raising=False)
    yield path
    fs._load.cache_clear()
