"""Optional live Snowflake retrieval. Read-only, parameterized, and configured from environment variables only.

Auth options (first match wins):
  1. SNOWFLAKE_CONNECTION_NAME -> named connection in ~/.snowflake/connections.toml (no secrets in env/repo)
  2. SNOWFLAKE_ACCOUNT + SNOWFLAKE_USER, with SNOWFLAKE_PASSWORD or SNOWFLAKE_AUTHENTICATOR
     (defaults to externalbrowser when no password is set)
"""
import os
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Mapping

from src.fixtures import APPLE_CIK
from src.models import MetricEvidence, TextEvidence
from src.retrieval import EvidenceBundle, LiveModeUnavailable

APPLE_MDNA_ADSH = "0000320193-23-000106"
MDNA_ITEM = "PART II, Item 7"
REVENUE_TAG = "RevenueFromContractWithCustomerExcludingAssessedTax"
REVENUE_VARIABLE = "NET SALES | ANNUAL"
TEXT_LIMIT = 8000

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

TEXT_SQL = """SELECT CIK, ADSH, FORM_TYPE, FILED_DATE, ITEM_NUMBER, ITEM_TITLE,
       LEFT(PLAINTEXT_CONTENT, %(text_limit)s) AS TEXT
FROM {db}.{schema}.SEC_CORPORATE_REPORT_ITEM_ATTRIBUTES
WHERE CIK = %(cik)s AND ADSH = %(adsh)s AND ITEM_NUMBER = %(item)s"""

METRIC_SQL = """WITH filings AS (
    SELECT DISTINCT ADSH, FORM_TYPE, FILED_DATE
    FROM {db}.{schema}.SEC_CORPORATE_REPORT_INDEX
    WHERE CIK = %(cik)s AND FORM_TYPE = '10-K'
)
SELECT m.ADSH, f.FORM_TYPE, f.FILED_DATE,
       TRY_TO_NUMBER(TO_VARCHAR(m.FISCAL_YEAR)) AS FISCAL_YEAR,
       m.FISCAL_PERIOD, m.VARIABLE_NAME, m.VALUE, m.UNIT,
       m.PERIOD_START_DATE, m.PERIOD_END_DATE, m.BUSINESS_SEGMENT, m.BUSINESS_SUBSEGMENT
FROM {db}.{schema}.SEC_METRICS_TIMESERIES m
JOIN filings f ON m.ADSH = f.ADSH
WHERE m.CIK = %(cik)s
  AND m.TAG = %(tag)s
  AND m.FISCAL_PERIOD = 'FY'
  AND TRY_TO_NUMBER(TO_VARCHAR(m.FISCAL_YEAR)) IN (%(old_year)s, %(new_year)s)
  AND m.VARIABLE_NAME = %(variable)s
  AND m.BUSINESS_SEGMENT IS NULL
  AND m.BUSINESS_SUBSEGMENT IS NULL
ORDER BY FISCAL_YEAR"""


def _identifier(value: str, name: str) -> str:
    if not _IDENTIFIER.match(value):
        raise LiveModeUnavailable(f"{name} is not a valid Snowflake identifier: {value!r}")
    return value


def connection_params(env: Mapping[str, str] = os.environ) -> Dict[str, Any]:
    """Build connector kwargs from the environment, or raise LiveModeUnavailable."""
    params: Dict[str, Any] = {"login_timeout": 60, "network_timeout": 60, "session_parameters": {"QUERY_TAG": "filingforensics"}}
    for key in ("warehouse", "role"):
        if env.get(f"SNOWFLAKE_{key.upper()}"):
            params[key] = env[f"SNOWFLAKE_{key.upper()}"]
    if env.get("SNOWFLAKE_CONNECTION_NAME"):
        params["connection_name"] = env["SNOWFLAKE_CONNECTION_NAME"]
        return params
    if not (env.get("SNOWFLAKE_ACCOUNT") and env.get("SNOWFLAKE_USER")):
        raise LiveModeUnavailable(
            "Live mode needs SNOWFLAKE_CONNECTION_NAME, or SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER. "
            "Switch to fixture mode or see .env.example."
        )
    params.update(account=env["SNOWFLAKE_ACCOUNT"], user=env["SNOWFLAKE_USER"])
    if env.get("SNOWFLAKE_PASSWORD"):
        params["password"] = env["SNOWFLAKE_PASSWORD"]
    params["authenticator"] = env.get("SNOWFLAKE_AUTHENTICATOR") or ("snowflake" if "password" in params else "externalbrowser")
    return params


def _iso(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)[:10] if value is not None else ""


def _int(value: Any) -> int:
    number = Decimal(str(value))
    if number != number.to_integral_value():
        raise ValueError(f"Expected whole-dollar value, got {value!r}")
    return int(number)


def normalize_text(row: Mapping[str, Any]) -> TextEvidence:
    return TextEvidence(
        cik=str(row["CIK"]),
        adsh=str(row["ADSH"]),
        form_type=str(row["FORM_TYPE"]),
        filed_date=_iso(row["FILED_DATE"]),
        item_number=str(row["ITEM_NUMBER"]),
        item_title=str(row["ITEM_TITLE"]),
        text=str(row["TEXT"] or ""),
    )


def normalize_metric(row: Mapping[str, Any]) -> MetricEvidence:
    return MetricEvidence(
        fiscal_year=_int(row["FISCAL_YEAR"]),
        value=_int(row["VALUE"]),
        unit=str(row["UNIT"]),
        period_start=_iso(row["PERIOD_START_DATE"]),
        period_end=_iso(row["PERIOD_END_DATE"]),
        adsh=str(row["ADSH"]),
        filed_date=_iso(row["FILED_DATE"]),
        variable_name=str(row["VARIABLE_NAME"]),
        business_segment=row.get("BUSINESS_SEGMENT"),
        business_subsegment=row.get("BUSINESS_SUBSEGMENT"),
    )


def _query(conn, sql: str, binds: Dict[str, Any]) -> List[Dict[str, Any]]:
    from snowflake.connector import DictCursor

    with conn.cursor(DictCursor) as cur:
        cur.execute(sql, binds)
        return list(cur.fetchall())


def fetch_live_evidence(old_year: int = 2022, new_year: int = 2023, env: Mapping[str, str] = os.environ) -> EvidenceBundle:
    """Run the two independent read-only queries and normalize them. Raises LiveModeUnavailable on any failure."""
    params = connection_params(env)
    db = _identifier(env.get("SNOWFLAKE_DATABASE") or "SNOWFLAKE_PUBLIC_DATA_FREE", "SNOWFLAKE_DATABASE")
    schema = _identifier(env.get("SNOWFLAKE_SCHEMA") or "PUBLIC_DATA_FREE", "SNOWFLAKE_SCHEMA")
    text_sql, metric_sql = TEXT_SQL.format(db=db, schema=schema), METRIC_SQL.format(db=db, schema=schema)
    text_binds = {"cik": APPLE_CIK, "adsh": APPLE_MDNA_ADSH, "item": MDNA_ITEM, "text_limit": TEXT_LIMIT}
    metric_binds = {"cik": APPLE_CIK, "tag": REVENUE_TAG, "variable": REVENUE_VARIABLE, "old_year": old_year, "new_year": new_year}
    try:
        import snowflake.connector

        conn = snowflake.connector.connect(**params)
    except ImportError as exc:
        raise LiveModeUnavailable("snowflake-connector-python is not installed. Switch to fixture mode.") from exc
    except Exception as exc:  # connector raises many error types; surface them all as recoverable
        raise LiveModeUnavailable(f"Could not connect to Snowflake: {exc}. Switch to fixture mode.") from exc
    try:
        text_rows = _query(conn, text_sql, text_binds)
        metric_rows = _query(conn, metric_sql, metric_binds)
    except Exception as exc:
        raise LiveModeUnavailable(f"Snowflake query failed: {exc}. Switch to fixture mode.") from exc
    finally:
        conn.close()
    if len(text_rows) != 1:
        raise LiveModeUnavailable(f"Expected 1 MD&A row, got {len(text_rows)}. Switch to fixture mode.")
    try:
        text = normalize_text(text_rows[0])
        metrics = [normalize_metric(r) for r in metric_rows]
    except (KeyError, ValueError) as exc:
        raise LiveModeUnavailable(f"Unexpected live row shape: {exc}. Switch to fixture mode.") from exc
    return EvidenceBundle(mode="live", text=text, metrics=metrics, sql=[text_sql, metric_sql], text_rows=len(text_rows))
