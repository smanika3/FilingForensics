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

    @property
    def row_counts(self) -> dict:
        return {"text_rows": 1, "metric_rows": len(self.metrics)}


def get_evidence(mode: str = "fixture") -> EvidenceBundle:
    if mode == "fixture":
        return EvidenceBundle(mode="fixture", text=APPLE_MDNA_TEXT, metrics=list(APPLE_REVENUE_METRICS))
    if mode == "live":
        raise LiveModeUnavailable(
            "Live Snowflake mode is not implemented yet (optional Stage 4). Switch to fixture mode."
        )
    raise ValueError(f"Unknown mode: {mode}")
