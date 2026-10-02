import os
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from src import snowflake_client as sc
from src.calculations import EvidenceError, change_for_metric
from src.metrics import METRICS
from src.retrieval import LiveModeUnavailable

ENV = {"SNOWFLAKE_CONNECTION_NAME": "test"}
MDNA = ("Overview.   Total net sales decreased 3% or $11.0 billion during 2023.   "
        "<table><tr><td>Total net sales</td><td>$</td><td>383,285</td></tr></table>")
TEXT_ROW = {"CIK": "0000320193", "ADSH": "0000320193-23-000106", "FORM_TYPE": "10-K", "FILED_DATE": date(2023, 11, 3),
            "ITEM_NUMBER": "PART II, Item 7", "ITEM_TITLE": "MD&A", "TEXT": MDNA}


def fact(fy, adsh, tag, value, start, end, unit="USD"):
    return {"ADSH": adsh, "FORM_TYPE": "10-K", "FILED_DATE": date(fy, 11, 1), "FISCAL_YEAR": Decimal(fy), "TAG": tag,
            "MEASURE_DESCRIPTION": "Net sales", "UNIT": unit, "VALUE": value, "PERIOD_START_DATE": start,
            "PERIOD_END_DATE": end, "COVERED_QTRS": 4}


REV = "RevenueFromContractWithCustomerExcludingAssessedTax"
FACTS = [
    # FY2022 10-K: current year + comparative prior years (prior must be ignored)
    fact(2022, "A22", REV, Decimal("394328000000"), date(2021, 9, 26), date(2022, 9, 24)),
    fact(2022, "A22", REV, Decimal("365817000000"), date(2020, 9, 27), date(2021, 9, 25)),
    fact(2023, "A23", REV, 383285000000.0, date(2022, 9, 25), date(2023, 9, 30)),
    fact(2023, "A23", REV, 383285000000.0, date(2022, 9, 25), date(2023, 9, 30)),  # identical duplicate
    fact(2023, "A23", "Revenues", 1.0, date(2022, 9, 25), date(2023, 9, 30)),  # lower-priority tag ignored
]


def test_missing_credentials_raise_recoverable_error():
    with pytest.raises(LiveModeUnavailable, match="fixture mode"):
        sc.connection_params({})


def test_connection_params_variants():
    assert sc.connection_params({"SNOWFLAKE_CONNECTION_NAME": "c", "SNOWFLAKE_WAREHOUSE": "WH"})["connection_name"] == "c"
    sso = sc.connection_params({"SNOWFLAKE_ACCOUNT": "a", "SNOWFLAKE_USER": "u"})
    assert sso["authenticator"] == "externalbrowser" and "password" not in sso
    assert sc.connection_params({"SNOWFLAKE_ACCOUNT": "a", "SNOWFLAKE_USER": "u", "SNOWFLAKE_PASSWORD": "p"})["authenticator"] == "snowflake"


def test_sql_is_read_only_parameterized_and_independent():
    for sql in (sc.LATEST_YEAR_SQL, sc.FACTS_SQL, sc.TEXT_SQL, sc.LOOKUP_SQL):
        upper = sql.upper()
        assert upper.lstrip().startswith(("SELECT", "WITH"))
        for word in ("INSERT", "UPDATE", "DELETE", "MERGE", "CREATE", "DROP", "ON TRUE"):
            assert word not in upper
        assert "0000320193" not in sql
    assert "ITEM_ATTRIBUTES" not in sc.FACTS_SQL and "REPORT_ATTRIBUTES a" not in sc.TEXT_SQL


def test_normalize_facts_picks_own_filing_current_period_and_dedupes():
    rows = sc.normalize_facts(FACTS, METRICS["revenue"], (2022, 2023))
    assert [(r.fiscal_year, r.value, r.adsh) for r in rows] == [(2022, 394328000000, "A22"), (2023, 383285000000, "A23")]
    assert change_for_metric(rows, METRICS["revenue"], 2022, 2023).absolute_change == -11043000000


def test_conflicting_values_are_rejected_by_validation():
    conflict = FACTS + [fact(2023, "A23", REV, Decimal("1"), date(2022, 9, 25), date(2023, 9, 30))]
    rows = sc.normalize_facts(conflict, METRICS["revenue"], (2022, 2023))
    with pytest.raises(EvidenceError, match="duplicate"):
        change_for_metric(rows, METRICS["revenue"], 2022, 2023)


def test_instant_metric_and_eps():
    assets = [dict(fact(2022, "A22", "Assets", 352755000000, date(2022, 9, 24), date(2022, 9, 24)), COVERED_QTRS=0),
              dict(fact(2023, "A23", "Assets", 352583000000, date(2023, 9, 30), date(2023, 9, 30)), COVERED_QTRS=0)]
    rows = sc.normalize_facts(assets, METRICS["total_assets"], (2022, 2023))
    assert rows[0].period_start == "" and change_for_metric(rows, METRICS["total_assets"], 2022, 2023).absolute_change == -172000000
    eps = [fact(2022, "A22", "EarningsPerShareDiluted", Decimal("6.11"), date(2021, 9, 26), date(2022, 9, 24)),
           fact(2023, "A23", "EarningsPerShareDiluted", Decimal("6.13"), date(2022, 9, 25), date(2023, 9, 30))]
    change = change_for_metric(sc.normalize_facts(eps, METRICS["eps_diluted"], (2022, 2023)), METRICS["eps_diluted"], 2022, 2023)
    assert change.unit == "USD/shares" and change.absolute_change == pytest.approx(0.02)


def test_invalid_identifier_rejected():
    with pytest.raises(LiveModeUnavailable, match="identifier"):
        sc.fetch_live_evidence("0000320193", "Apple", "revenue", (2022, 2023), env={**ENV, "SNOWFLAKE_DATABASE": "X; DROP TABLE Y"})


def _fetch(fact_rows, text_rows):
    conn = mock.MagicMock(is_closed=lambda: False)
    sc._CONN.clear()
    with mock.patch("snowflake.connector.connect", return_value=conn), \
            mock.patch.object(sc, "_query", side_effect=[fact_rows, text_rows]) as q:
        bundle = sc.fetch_live_evidence("0000320193", "Apple Inc.", "revenue", (2022, 2023), env=ENV)
    binds = [call.args[2] for call in q.call_args_list]
    assert binds[0]["cik"] == "0000320193" and binds[0]["tag0"] == REV and binds[1]["fiscal_year"] == 2023
    return bundle


def test_fetch_builds_bundle_with_excerpt_and_tables():
    bundle = _fetch(FACTS, [TEXT_ROW])
    assert bundle.mode == "live" and bundle.row_counts == {"text_rows": 1, "metric_rows": 2}
    assert bundle.text.filed_date == "2023-11-03" and "<table" not in bundle.text.text
    assert any(type(b).__name__ == "Table" for b in bundle.text_blocks)


def test_missing_mdna_is_a_note_not_an_error():
    bundle = _fetch(FACTS, [])
    assert bundle.text is None and "No MD&A" in bundle.notes[0]


def test_connect_failure_is_recoverable():
    sc._CONN.clear()
    with mock.patch("snowflake.connector.connect", side_effect=Exception("bad auth")):
        with pytest.raises(LiveModeUnavailable, match="bad auth"):
            sc.fetch_live_evidence("0000320193", "Apple", "revenue", (2022, 2023), env=ENV)


@pytest.mark.skipif(not os.getenv("FF_LIVE_SNOWFLAKE"), reason="set FF_LIVE_SNOWFLAKE=1 plus Snowflake env vars")
@pytest.mark.parametrize("cik,name,metric,years,expected", [
    ("0000320193", "Apple", "revenue", (2022, 2023), -11043000000),
    ("0000789019", "Microsoft", "net_income", (2023, 2024), 15775000000),
])
def test_live_snowflake(cik, name, metric, years, expected):
    env = dict(os.environ)
    bundle = sc.fetch_live_evidence(cik, name, metric, years, env=env)
    change = change_for_metric(bundle.metrics, METRICS[metric], *years)
    print(f"\n{name} {metric}: rows={bundle.row_counts} change={change.absolute_change}")
    assert change.absolute_change == expected and bundle.text is not None
    assert sc.lookup_companies("WMT", env=env)[0].cik == "0000104169"
