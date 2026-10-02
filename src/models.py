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
    value: float  # int for USD totals, float for per-share values
    unit: str
    period_start: str
    period_end: str
    adsh: str
    filed_date: str
    variable_name: str
    business_segment: Optional[str] = None
    business_subsegment: Optional[str] = None


@dataclass(frozen=True)
class MetricChange:
    old: MetricEvidence
    new: MetricEvidence
    absolute_change: float
    percent_change: float
    label: str = "Revenue"
    unit: str = "USD"
    company: str = ""

    @property
    def summary(self) -> str:
        direction = "decreased" if self.absolute_change < 0 else "increased" if self.absolute_change > 0 else "was unchanged"
        subject = f"{self.company} {self.label[:1].lower() + self.label[1:]}" if self.company else self.label
        if self.absolute_change == 0:
            return f"{subject} was unchanged from FY{self.old.fiscal_year} to FY{self.new.fiscal_year}."
        return (
            f"{subject} {direction} by {format_value(abs(self.absolute_change), self.unit)}, "
            f"or {abs(self.percent_change):.1f}%, from FY{self.old.fiscal_year} to FY{self.new.fiscal_year}."
        )


RevenueChange = MetricChange  # backwards-compatible name


def format_usd_billions(value: float, decimals: int = 2) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value) / 1e9:,.{decimals}f}B"


def format_value(value: float, unit: str = "USD") -> str:
    """Display formatting only; raw values are always retained alongside."""
    sign = "-" if value < 0 else ""
    if unit != "USD":
        return f"{sign}${abs(value):,.2f}"
    if abs(value) >= 1e9:
        return format_usd_billions(value)
    return f"{sign}${abs(value) / 1e6:,.1f}M"
