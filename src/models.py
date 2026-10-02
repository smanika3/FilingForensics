"""Typed evidence and result objects."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TextEvidence:
    cik: str
    adsh: str
    form_type: str
    filed_date: str
    item_number: str
    item_title: str
    text: str


@dataclass(frozen=True)
class MetricEvidence:
    fiscal_year: int
    value: int
    unit: str
    period_start: str
    period_end: str
    adsh: str
    filed_date: str
    variable_name: str
    business_segment: Optional[str] = None
    business_subsegment: Optional[str] = None


@dataclass(frozen=True)
class RevenueChange:
    old: MetricEvidence
    new: MetricEvidence
    absolute_change: int
    percent_change: float

    @property
    def summary(self) -> str:
        direction = "decreased" if self.absolute_change < 0 else "increased"
        return (
            f"Revenue {direction} by {format_usd_billions(abs(self.absolute_change))}, "
            f"or {abs(self.percent_change):.1f}%, from FY{self.old.fiscal_year} to FY{self.new.fiscal_year}."
        )


def format_usd_billions(value: float, decimals: int = 2) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value) / 1e9:,.{decimals}f}B"
