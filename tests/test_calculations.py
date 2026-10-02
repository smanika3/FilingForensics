from dataclasses import replace

import pytest

from src.calculations import EvidenceError, revenue_change
from src.fixtures import APPLE_REVENUE_METRICS
from src.models import format_usd_billions

FY22, FY23 = APPLE_REVENUE_METRICS


def test_absolute_change():
    assert revenue_change(APPLE_REVENUE_METRICS, 2022, 2023).absolute_change == -11043000000


def test_percent_change():
    assert revenue_change(APPLE_REVENUE_METRICS, 2022, 2023).percent_change == pytest.approx(-2.8007, abs=1e-3)


def test_summary_and_formatting():
    change = revenue_change(APPLE_REVENUE_METRICS, 2022, 2023)
    assert change.summary == "Revenue decreased by $11.04B, or 2.8%, from FY2022 to FY2023."
    assert format_usd_billions(394328000000) == "$394.33B"
    assert change.old.value == 394328000000  # raw value retained


def test_missing_year_rejected():
    with pytest.raises(EvidenceError, match="FY2022"):
        revenue_change([FY23], 2022, 2023)


def test_duplicate_row_rejected():
    with pytest.raises(EvidenceError, match="duplicate"):
        revenue_change([FY22, FY23, replace(FY23, adsh="dup")], 2022, 2023)


def test_non_usd_rejected():
    with pytest.raises(EvidenceError, match="USD"):
        revenue_change([FY22, replace(FY23, unit="EUR")], 2022, 2023)


def test_segment_row_rejected():
    with pytest.raises(EvidenceError, match="segment"):
        revenue_change([FY22, replace(FY23, business_segment="Americas")], 2022, 2023)


def test_non_adjacent_periods_rejected():
    with pytest.raises(EvidenceError, match="adjacent"):
        revenue_change([FY22, replace(FY23, period_start="2022-10-01")], 2022, 2023)
