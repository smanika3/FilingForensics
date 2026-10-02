"""Retrieve narrative text and metrics independently (never a text x metric join)."""
from dataclasses import dataclass, field
from typing import List

from src.fixtures import APPLE_MDNA_TEXT, APPLE_REVENUE_METRICS
from src.models import MetricEvidence, TextEvidence


class LiveModeUnavailable(RuntimeError):
    """Raised when live Snowflake retrieval is requested but not configured."""


@dataclass
class EvidenceBundle:
    mode: str
    text: TextEvidence
    metrics: List[MetricEvidence]
    sql: List[str] = field(default_factory=list)
    text_rows: int = 1

    @property
    def row_counts(self) -> dict:
        return {"text_rows": self.text_rows, "metric_rows": len(self.metrics)}


def get_evidence(mode: str = "fixture", old_year: int = 2022, new_year: int = 2023) -> EvidenceBundle:
    if mode == "fixture":
        return EvidenceBundle(mode="fixture", text=APPLE_MDNA_TEXT, metrics=list(APPLE_REVENUE_METRICS))
    if mode == "live":
        from src.snowflake_client import fetch_live_evidence  # lazy: fixture mode never needs the connector

        return fetch_live_evidence(old_year, new_year)
    raise ValueError(f"Unknown mode: {mode}")
