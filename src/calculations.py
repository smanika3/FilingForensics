"""Deterministic revenue calculations and evidence validation (never delegated to the LLM)."""
from datetime import date, timedelta
from typing import Dict, List, Sequence

from src.models import MetricEvidence, RevenueChange


class EvidenceError(ValueError):
    """Raised when metric evidence is missing, duplicated, or inconsistent."""


def select_annual_rows(rows: Sequence[MetricEvidence], years: Sequence[int]) -> Dict[int, MetricEvidence]:
    selected: Dict[int, List[MetricEvidence]] = {y: [] for y in years}
    for row in rows:
        if row.fiscal_year not in selected:
            continue
        if row.unit != "USD":
            raise EvidenceError(f"FY{row.fiscal_year}: unit {row.unit!r} is not USD")
        if row.business_segment or row.business_subsegment:
            raise EvidenceError(f"FY{row.fiscal_year}: segment row is not total revenue")
        if not row.period_start or not row.period_end:
            raise EvidenceError(f"FY{row.fiscal_year}: missing period dates")
        if not row.adsh:
            raise EvidenceError(f"FY{row.fiscal_year}: missing accession (ADSH)")
        selected[row.fiscal_year].append(row)
    result = {}
    for year, matches in selected.items():
        if not matches:
            raise EvidenceError(f"FY{year}: no total annual revenue row")
        if len(matches) > 1:
            raise EvidenceError(f"FY{year}: {len(matches)} duplicate total annual revenue rows")
        result[year] = matches[0]
    return result


def validate_adjacent_periods(old: MetricEvidence, new: MetricEvidence) -> None:
    old_end = date.fromisoformat(old.period_end)
    new_start = date.fromisoformat(new.period_start)
    if new_start != old_end + timedelta(days=1):
        raise EvidenceError(
            f"Periods not adjacent: FY{old.fiscal_year} ends {old.period_end}, "
            f"FY{new.fiscal_year} starts {new.period_start}"
        )


def revenue_change(rows: Sequence[MetricEvidence], old_year: int, new_year: int) -> RevenueChange:
    selected = select_annual_rows(rows, [old_year, new_year])
    old, new = selected[old_year], selected[new_year]
    validate_adjacent_periods(old, new)
    if old.value == 0:
        raise EvidenceError(f"FY{old_year}: zero base revenue")
    absolute = new.value - old.value
    return RevenueChange(old=old, new=new, absolute_change=absolute, percent_change=absolute / old.value * 100)
