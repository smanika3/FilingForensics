import os
from datetime import date
from decimal import Decimal
from unittest import mock

import pytest

from src.calculations import revenue_change
from src.retrieval import LiveModeUnavailable
from src import snowflake_client as sc

TEXT_ROW = {
    "CIK": "0000320193", "ADSH": "0000320193-23-000106", "FORM_TYPE": "10-K", "FILED_DATE": date(2023, 11, 3),
    "ITEM_NUMBER": "PART II, Item 7", "ITEM_TITLE": "MD&A", "TEXT": "total net sales decreased 3%",
}
METRIC_ROWS = [
    {"ADSH": "0000320193-24-000123", "FORM_TYPE": "10-K", "FILED_DATE": date(2024, 11, 1), "FISCAL_YEAR": Decimal(2022),
     "FISCAL_PERIOD": "FY", "VARIABLE_NAME": "NET SALES | ANNUAL", "VALUE": 394328000000.0, "UNIT": "USD",
     "PERIOD_START_DATE": date(2021, 9, 26), "PERIOD_END_DATE": date(2022, 9, 24),
     "BUSINESS_SEGMENT": None, "BUSINESS_SUBSEGMENT": None},
    {"ADSH": "0000320193-25-000079", "FORM_TYPE": "10-K", "FILED_DATE": date(2025, 10, 31), "FISCAL_YEAR": Decimal(2023),
     "FISCAL_PERIOD": "FY", "VARIABLE_NAME": "NET SALES | ANNUAL", "VALUE": Decimal("383285000000"), "UNIT": "USD",
     "PERIOD_START_DATE": date(2022, 9, 25), "PERIOD_END_DATE": date(2023, 9, 30),
     "BUSINESS_SEGMENT": None, "BUSINESS_SUBSEGMENT": None},
]
ENV = {"SNOWFLAKE_CONNECTION_NAME": "test"}


def test_missing_credentials_raise_recoverable_error():
    with pytest.raises(LiveModeUnavailable, match="fixture mode"):
        sc.connection_params({})


def test_connection_params_variants():
    assert sc.connection_params({"SNOWFLAKE_CONNECTION_NAME": "c", "SNOWFLAKE_WAREHOUSE": "WH"})["connection_name"] == "c"
    sso = sc.connection_params({"SNOWFLAKE_ACCOUNT": "a", "SNOWFLAKE_USER": "u"})
    assert sso["authenticator"] == "externalbrowser" and "password" not in sso
    pw = sc.connection_params({"SNOWFLAKE_ACCOUNT": "a", "SNOWFLAKE_USER": "u", "SNOWFLAKE_PASSWORD": "p"})
    assert pw["authenticator"] == "snowflake"


def test_sql_is_read_only_parameterized_and_independent():
    for sql in (sc.TEXT_SQL, sc.METRIC_SQL):
        upper = sql.upper()
        assert upper.lstrip().startswith(("SELECT", "WITH"))
        for word in ("INSERT", "UPDATE", "DELETE", "MERGE", "CREATE", "DROP", "ON TRUE"):
            assert word not in upper
        assert "%(cik)s" in sql and "0000320193" not in sql
    assert "SEC_METRICS_TIMESERIES" not in sc.TEXT_SQL
    assert "ITEM_ATTRIBUTES" not in sc.METRIC_SQL


def test_invalid_identifier_rejected():
    with pytest.raises(LiveModeUnavailable, match="identifier"):
        sc.fetch_live_evidence(env={**ENV, "SNOWFLAKE_DATABASE": "X; DROP TABLE Y"})


def test_normalization_matches_fixture_contract():
    bundle = _fetch_with_fake_rows([TEXT_ROW], METRIC_ROWS)
    assert bundle.mode == "live" and bundle.row_counts == {"text_rows": 1, "metric_rows": 2}
    assert bundle.text.filed_date == "2023-11-03"
    assert [m.value for m in bundle.metrics] == [394328000000, 383285000000]
    assert bundle.metrics[0].period_end == "2022-09-24" and bundle.metrics[1].fiscal_year == 2023
    assert revenue_change(bundle.metrics, 2022, 2023).absolute_change == -11043000000


def test_connect_failure_is_recoverable():
    with mock.patch("snowflake.connector.connect", side_effect=Exception("bad auth")):
        with pytest.raises(LiveModeUnavailable, match="bad auth"):
            sc.fetch_live_evidence(env=ENV)


def test_wrong_text_row_count_is_recoverable():
    with pytest.raises(LiveModeUnavailable, match="1 MD&A row"):
        _fetch_with_fake_rows([], METRIC_ROWS)


def _fetch_with_fake_rows(text_rows, metric_rows):
    conn = mock.MagicMock()
    with mock.patch("snowflake.connector.connect", return_value=conn), \
            mock.patch.object(sc, "_query", side_effect=[text_rows, metric_rows]):
        bundle = sc.fetch_live_evidence(env=ENV)
    conn.close.assert_called_once()
    return bundle


@pytest.mark.skipif(not os.getenv("FF_LIVE_SNOWFLAKE"), reason="set FF_LIVE_SNOWFLAKE=1 plus Snowflake env vars")
def test_live_snowflake():
    bundle = sc.fetch_live_evidence()
    change = revenue_change(bundle.metrics, 2022, 2023)
    print(f"\nlive rows={bundle.row_counts} change={change.absolute_change} pct={change.percent_change:.4f}")
    assert change.absolute_change == -11043000000
    assert {m.adsh for m in bundle.metrics} == {"0000320193-24-000123", "0000320193-25-000079"}
