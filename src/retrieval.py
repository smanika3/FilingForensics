"""Retrieve narrative text and metrics independently (never a text x metric join)."""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from src.fixtures import APPLE_MDNA_TEXT, APPLE_REVENUE_METRICS
from src.models import MetricEvidence, TextEvidence


class LiveModeUnavailable(RuntimeError):
    """Raised when live Snowflake retrieval is requested but not configured or fails."""


@dataclass
class EvidenceBundle:
    mode: str
    text: Optional[TextEvidence]
    metrics: List[MetricEvidence]
    sql: List[str] = field(default_factory=list)
    text_rows: int = 1
    company_name: str = "Apple Inc."
    cik: str = "0000320193"
    metric_key: str = "revenue"
    years: Tuple[int, int] = (2022, 2023)
    text_blocks: list = field(default_factory=list)  # mdna.Block items for rendering
    notes: List[str] = field(default_factory=list)

    @property
    def row_counts(self) -> dict:
        return {"text_rows": self.text_rows, "metric_rows": len(self.metrics)}


def get_evidence(mode: str = "fixture", old_year: int = 2022, new_year: int = 2023) -> EvidenceBundle:
    """Legacy Apple revenue preset (kept as the verified baseline)."""
    if mode == "fixture":
        return EvidenceBundle(mode="fixture", text=APPLE_MDNA_TEXT, metrics=list(APPLE_REVENUE_METRICS))
    if mode == "live":
        from src.snowflake_client import fetch_live_evidence  # lazy: fixture mode never needs the connector

        return fetch_live_evidence("0000320193", "Apple Inc.", "revenue", (old_year, new_year))
    raise ValueError(f"Unknown mode: {mode}")
