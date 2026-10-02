"""Optional live Snowflake retrieval. Read-only, parameterized, and configured from environment variables only.

Auth options (first match wins):
  1. SNOWFLAKE_CONNECTION_NAME -> named connection in ~/.snowflake/connections.toml (no secrets in env/repo)
  2. SNOWFLAKE_ACCOUNT + SNOWFLAKE_USER, with SNOWFLAKE_PASSWORD or SNOWFLAKE_AUTHENTICATOR
     (defaults to externalbrowser when no password is set)

Facts: each fiscal year's value comes from that year's own 10-K (SEC_CORPORATE_REPORT_ATTRIBUTES, clean totals only).
Narrative: MD&A (PART II, Item 7) from the newest requested year's 10-K, retrieved in a separate query.
"""
import os
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.companies import Company
from src.config import _load_env
from src.mdna import blocks_to_text, relevant_excerpt
from src.metrics import METRICS, Metric
from src.models import MetricEvidence, TextEvidence
from src.retrieval import EvidenceBundle, LiveModeUnavailable

_load_env()

MDNA_ITEM = "PART II, Item 7"
TEXT_LIMIT = 200000
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")

LATEST_YEAR_SQL = """SELECT MAX(TRY_TO_NUMBER(TO_VARCHAR(FISCAL_YEAR))) AS FISCAL_YEAR
FROM {db}.{schema}.SEC_CORPORATE_REPORT_INDEX
WHERE CIK = %(cik)s AND FORM_TYPE = '10-K'"""

FACTS_SQL = """WITH filings AS (
    SELECT DISTINCT ADSH, FORM_TYPE, FILED_DATE, TRY_TO_NUMBER(TO_VARCHAR(FISCAL_YEAR)) AS FISCAL_YEAR
    FROM {db}.{schema}.SEC_CORPORATE_REPORT_INDEX
    WHERE CIK = %(cik)s AND FORM_TYPE = '10-K'
      AND TRY_TO_NUMBER(TO_VARCHAR(FISCAL_YEAR)) IN (%(old_year)s, %(new_year)s)
)
SELECT DISTINCT a.ADSH, f.FORM_TYPE, f.FILED_DATE, f.FISCAL_YEAR, a.TAG, a.MEASURE_DESCRIPTION,
       a.UNIT, a.VALUE, a.PERIOD_START_DATE, a.PERIOD_END_DATE, a.COVERED_QTRS
FROM {db}.{schema}.SEC_CORPORATE_REPORT_ATTRIBUTES a
JOIN filings f ON a.ADSH = f.ADSH
WHERE a.CIK = %(cik)s
  AND a.TAG IN ({tag_binds})
  AND a.METADATA IS NULL
  AND a.COVERED_QTRS = %(covered_qtrs)s
ORDER BY f.FISCAL_YEAR, a.PERIOD_END_DATE"""

TEXT_SQL = """SELECT r.CIK, r.ADSH, r.FORM_TYPE, r.FILED_DATE, i.ITEM_NUMBER, i.ITEM_TITLE,
       LEFT(i.PLAINTEXT_CONTENT, %(text_limit)s) AS TEXT
FROM {db}.{schema}.SEC_CORPORATE_REPORT_INDEX r
JOIN {db}.{schema}.SEC_CORPORATE_REPORT_ITEM_ATTRIBUTES i ON i.ADSH = r.ADSH AND i.CIK = r.CIK
WHERE r.CIK = %(cik)s AND r.FORM_TYPE = '10-K'
  AND TRY_TO_NUMBER(TO_VARCHAR(r.FISCAL_YEAR)) = %(fiscal_year)s
  AND i.ITEM_NUMBER = %(item)s
LIMIT 1"""

LOOKUP_SQL = """SELECT DISTINCT s.CIK, s.COMPANY_NAME, c.PRIMARY_TICKER
FROM {db}.{schema}.SEC_CIK_INDEX s
LEFT JOIN {db}.{schema}.COMPANY_INDEX c ON c.CIK = s.CIK
WHERE s.SEC_FILER_CATEGORY IS NOT NULL
  AND (UPPER(c.PRIMARY_TICKER) = UPPER(%(text)s) OR s.COMPANY_NAME ILIKE %(pattern)s)
ORDER BY LENGTH(s.COMPANY_NAME)
LIMIT 6"""

_CONN: Dict[Tuple, Any] = {}


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
    conn_name = env.get("SNOWFLAKE_CONNECTION_NAME")
    if not conn_name and env is os.environ and not (env.get("SNOWFLAKE_ACCOUNT") and env.get("SNOWFLAKE_USER")):
        try:
            from snowflake.connector.config_manager import CONFIG_MANAGER
            conns = list(CONFIG_MANAGER["connections"].keys())
            if "default" in conns:
                conn_name = "default"
            elif len(conns) == 1:
                conn_name = conns[0]
        except Exception:
            pass
    if conn_name:
        params["connection_name"] = conn_name
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


def _db_schema(env: Mapping[str, str]) -> Tuple[str, str]:
    return (
        _identifier(env.get("SNOWFLAKE_DATABASE") or "SNOWFLAKE_PUBLIC_DATA_FREE", "SNOWFLAKE_DATABASE"),
        _identifier(env.get("SNOWFLAKE_SCHEMA") or "PUBLIC_DATA_FREE", "SNOWFLAKE_SCHEMA"),
    )


def _connect(env: Mapping[str, str]):
    """Reuse one connection per credential set so OAuth/SSO doesn't prompt on every query."""
    params = connection_params(env)
    key = tuple(sorted((k, str(v)) for k, v in params.items() if k != "password"))
    conn = _CONN.get(key)
    if conn is not None and not conn.is_closed():
        return conn
    try:
        import snowflake.connector

        conn = snowflake.connector.connect(**params)
    except ImportError as exc:
        raise LiveModeUnavailable("snowflake-connector-python is not installed. Switch to fixture mode.") from exc
    except Exception as exc:  # connector raises many error types; surface them all as recoverable
        raise LiveModeUnavailable(f"Could not connect to Snowflake: {exc}. Switch to fixture mode.") from exc
    _CONN[key] = conn
    return conn


def _query(conn, sql: str, binds: Dict[str, Any]) -> List[Dict[str, Any]]:
    from snowflake.connector import DictCursor

    try:
        with conn.cursor(DictCursor) as cur:
            cur.execute(sql, binds)
            return list(cur.fetchall())
    except Exception as exc:
        raise LiveModeUnavailable(f"Snowflake query failed: {exc}. Switch to fixture mode.") from exc


def _iso(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)[:10] if value is not None else ""


def _number(value: Any):
    number = Decimal(str(value))
    return int(number) if number == number.to_integral_value() else float(number)


def _int(value: Any) -> int:
    number = _number(value)
    if not isinstance(number, int):
        raise ValueError(f"Expected whole number, got {value!r}")
    return number


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


def normalize_facts(rows: Sequence[Mapping[str, Any]], metric: Metric, years: Sequence[int]) -> List[MetricEvidence]:
    """One row per fiscal year: that year's own 10-K, its latest period, first tag (by priority) present.

    Identical duplicate rows are collapsed; conflicting values are kept so validation rejects them.
    """
    by_year: Dict[int, List[Mapping[str, Any]]] = {}
    for row in rows:
        by_year.setdefault(_int(row["FISCAL_YEAR"]), []).append(row)
    out: List[MetricEvidence] = []
    for year in years:
        year_rows = by_year.get(year, [])
        tag = next((t for t in metric.tags if any(r["TAG"] == t for r in year_rows)), None)
        if tag is None:
            continue
        tagged = [r for r in year_rows if r["TAG"] == tag]
        latest_end = max(_iso(r["PERIOD_END_DATE"]) for r in tagged)
        current = [r for r in tagged if _iso(r["PERIOD_END_DATE"]) == latest_end]
        seen = set()
        for r in current:
            value = _number(r["VALUE"])
            if value in seen:
                continue
            seen.add(value)
            out.append(
                MetricEvidence(
                    fiscal_year=year,
                    value=value,
                    unit=str(r["UNIT"]),
                    period_start="" if metric.kind == "instant" else _iso(r["PERIOD_START_DATE"]),
                    period_end=latest_end,
                    adsh=str(r["ADSH"]),
                    filed_date=_iso(r["FILED_DATE"]),
                    variable_name=f"{tag} | {r.get('MEASURE_DESCRIPTION') or metric.label}",
                )
            )
    return out


def latest_fiscal_year(cik: str, env: Mapping[str, str] = os.environ) -> int:
    db, schema = _db_schema(env)
    rows = _query(_connect(env), LATEST_YEAR_SQL.format(db=db, schema=schema), {"cik": cik})
    if not rows or rows[0]["FISCAL_YEAR"] is None:
        raise LiveModeUnavailable("No 10-K filings with a fiscal year were found for this company.")
    return _int(rows[0]["FISCAL_YEAR"])


def lookup_companies(text: str, env: Mapping[str, str] = os.environ) -> List[Company]:
    """Quick read-only check that a company exists (ticker exact match or name prefix)."""
    db, schema = _db_schema(env)
    rows = _query(
        _connect(env), LOOKUP_SQL.format(db=db, schema=schema), {"text": text.strip(), "pattern": f"{text.strip()}%"}
    )
    return [Company(str(r["CIK"]), str(r["COMPANY_NAME"]), str(r.get("PRIMARY_TICKER") or "")) for r in rows]


def fetch_live_evidence(
    cik: str,
    company_name: str,
    metric_key: str,
    years: Optional[Tuple[int, int]] = None,
    env: Mapping[str, str] = os.environ,
) -> EvidenceBundle:
    """Run independent read-only queries (facts, then MD&A) and normalize. Raises LiveModeUnavailable on failure."""
    metric = METRICS[metric_key]
    db, schema = _db_schema(env)
    conn = _connect(env)
    if years is None:
        new_year = latest_fiscal_year(cik, env)
        years = (new_year - 1, new_year)
    old_year, new_year = years
    tag_binds = ", ".join(f"%(tag{i})s" for i in range(len(metric.tags)))
    facts_sql = FACTS_SQL.format(db=db, schema=schema, tag_binds=tag_binds)
    fact_binds: Dict[str, Any] = {
        "cik": cik, "old_year": old_year, "new_year": new_year,
        "covered_qtrs": 0 if metric.kind == "instant" else 4,
        **{f"tag{i}": t for i, t in enumerate(metric.tags)},
    }
    text_sql = TEXT_SQL.format(db=db, schema=schema)
    text_binds = {"cik": cik, "fiscal_year": new_year, "item": MDNA_ITEM, "text_limit": TEXT_LIMIT}

    fact_rows = _query(conn, facts_sql, fact_binds)
    text_rows = _query(conn, text_sql, text_binds)
    try:
        metrics = normalize_facts(fact_rows, metric, years)
        text = normalize_text(text_rows[0]) if text_rows else None
    except (KeyError, ValueError) as exc:
        raise LiveModeUnavailable(f"Unexpected live row shape: {exc}. Switch to fixture mode.") from exc

    notes: List[str] = []
    blocks: list = []
    if text is None:
        notes.append(f"No MD&A section found for the FY{new_year} 10-K; showing financial facts only.")
    else:
        blocks = relevant_excerpt(text.text, metric.mdna_keywords)
        if not blocks:
            notes.append("MD&A found, but no passage mentions this metric; showing the opening of the section.")
            blocks = relevant_excerpt(text.text, [""], max_chars=1500)
        text = TextEvidence(**{**text.__dict__, "text": blocks_to_text(blocks)})
    return EvidenceBundle(
        mode="live", text=text, metrics=metrics, sql=[facts_sql, text_sql], text_rows=len(text_rows),
        company_name=company_name, cik=cik, metric_key=metric_key, years=years, text_blocks=blocks, notes=notes,
    )
