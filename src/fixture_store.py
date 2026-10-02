"""Offline multi-scenario evidence snapshotted from Snowflake by scripts/refresh_fixtures.py."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.mdna import Block, Table, blocks_to_text
from src.models import MetricEvidence, TextEvidence
from src.retrieval import EvidenceBundle

FIXTURE_PATH = Path(__file__).with_name("fixture_data.json")


class FixtureMissing(LookupError):
    pass


def encode_blocks(blocks: List[Block]) -> List[Dict[str, Any]]:
    return [{"table": b.rows} if isinstance(b, Table) else {"p": b} for b in blocks]


def decode_blocks(items: List[Dict[str, Any]]) -> List[Block]:
    return [Table(rows=i["table"]) if "table" in i else i["p"] for i in items]


@lru_cache(maxsize=4)
def _load(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"companies": {}}
    return json.loads(p.read_text())


def load() -> Dict[str, Any]:
    return _load(str(FIXTURE_PATH))


def available_years(cik: str, metric_key: str) -> List[int]:
    company = load()["companies"].get(cik, {})
    return sorted({int(f["fiscal_year"]) for f in company.get("facts", {}).get(metric_key, [])})


def get_fixture_evidence(cik: str, metric_key: str, years: Optional[Tuple[int, int]] = None) -> EvidenceBundle:
    company = load()["companies"].get(cik)
    if company is None:
        raise FixtureMissing("This company is not in the offline fixture set. Switch to live mode to query it.")
    have = available_years(cik, metric_key)
    if not have:
        raise FixtureMissing(f"No offline facts for this metric. Switch to live mode.")
    if years is None:
        years = (have[-2], have[-1]) if len(have) > 1 else (have[0] - 1, have[0])
    missing = [y for y in years if y not in have]
    if missing:
        raise FixtureMissing(
            f"Offline fixtures cover FY{have[0]}–FY{have[-1]} for this company; FY{', FY'.join(map(str, missing))} "
            "is not included. Switch to live mode or choose another year."
        )
    metrics = [MetricEvidence(**f) for f in company["facts"][metric_key] if f["fiscal_year"] in years]
    mdna = company.get("mdna", {}).get(str(years[1]))
    text, blocks, notes = None, [], []
    if mdna:
        blocks = decode_blocks(mdna["excerpts"].get(metric_key, []))
        text = TextEvidence(**{**mdna["filing"], "text": blocks_to_text(blocks)})
        if not blocks:
            notes.append("MD&A found, but no passage mentions this metric.")
    else:
        notes.append(f"No MD&A narrative in the fixtures for FY{years[1]}; showing financial facts only.")
    return EvidenceBundle(
        mode="fixture", text=text, metrics=metrics, sql=[], text_rows=1 if mdna else 0,
        company_name=company["name"], cik=cik, metric_key=metric_key, years=years, text_blocks=blocks, notes=notes,
    )
