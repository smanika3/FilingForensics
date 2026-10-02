"""Deterministic metric calculations and evidence validation (never delegated to the LLM)."""
from datetime import date, timedelta
from typing import Dict, List, Sequence

from src.models import MetricChange, MetricEvidence


class EvidenceError(ValueError):
    """Raised when metric evidence is missing, duplicated, or inconsistent."""


def select_annual_rows(
    rows: Sequence[MetricEvidence], years: Sequence[int], unit: str = "USD", require_period_start: bool = True
) -> Dict[int, MetricEvidence]:
    selected: Dict[int, List[MetricEvidence]] = {y: [] for y in years}
    for row in rows:
        if row.fiscal_year not in selected:
            continue
        if row.unit != unit:
            raise EvidenceError(f"FY{row.fiscal_year}: unit {row.unit!r} is not {unit}")
        if row.business_segment or row.business_subsegment:
            raise EvidenceError(f"FY{row.fiscal_year}: segment row is not a company total")
        if not row.period_end or (require_period_start and not row.period_start):
            raise EvidenceError(f"FY{row.fiscal_year}: missing period dates")
        if not row.adsh:
            raise EvidenceError(f"FY{row.fiscal_year}: missing accession (ADSH)")
        selected[row.fiscal_year].append(row)
    result = {}
    for year, matches in selected.items():
        if not matches:
            raise EvidenceError(f"FY{year}: no total annual row")
        if len(matches) > 1:
            raise EvidenceError(f"FY{year}: {len(matches)} duplicate total annual rows")
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


def validate_instant_gap(old: MetricEvidence, new: MetricEvidence) -> None:
    gap = (date.fromisoformat(new.period_end) - date.fromisoformat(old.period_end)).days
    expected = 365 * (new.fiscal_year - old.fiscal_year)
    if abs(gap - expected) > 40:
        raise EvidenceError(f"Balance dates {old.period_end} and {new.period_end} are not {new.fiscal_year - old.fiscal_year} year(s) apart")


def metric_change(
    rows: Sequence[MetricEvidence],
    old_year: int,
    new_year: int,
    label: str = "Revenue",
    unit: str = "USD",
    kind: str = "duration",
    company: str = "",
    display_unit: str = "",
) -> MetricChange:
    if new_year <= old_year:
        raise EvidenceError(f"End year FY{new_year} must be after start year FY{old_year}")
    selected = select_annual_rows(rows, [old_year, new_year], unit=unit, require_period_start=kind == "duration")
    old, new = selected[old_year], selected[new_year]
    if kind == "instant":
        validate_instant_gap(old, new)
    elif new_year - old_year == 1:
        validate_adjacent_periods(old, new)
    if old.value == 0:
        raise EvidenceError(f"FY{old_year}: zero base value; percent change undefined")
    absolute = new.value - old.value
    if isinstance(absolute, float):
        absolute = round(absolute, 6)
    return MetricChange(
        old=old, new=new, absolute_change=absolute, percent_change=absolute / abs(old.value) * 100,
        label=label, unit=display_unit or unit, company=company,
    )


def change_for_metric(rows: Sequence[MetricEvidence], metric, old_year: int, new_year: int, company: str = "") -> MetricChange:
    return metric_change(rows, old_year, new_year, label=metric.label, unit=metric.unit, kind=metric.kind,
                         company=company, display_unit=metric.display_unit)


def revenue_change(rows: Sequence[MetricEvidence], old_year: int, new_year: int) -> MetricChange:
    return metric_change(rows, old_year, new_year)
