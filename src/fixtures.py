"""Verified Apple evidence for fixture mode (no credentials required).

Text excerpt retrieved from SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.SEC_CORPORATE_REPORT_ITEM_ATTRIBUTES
(CIK 0000320193, ADSH 0000320193-23-000106, PART II, Item 7).
"""
from typing import List

from src.models import MetricEvidence, TextEvidence

APPLE_CIK = "0000320193"

APPLE_MDNA_TEXT = TextEvidence(
    cik=APPLE_CIK,
    adsh="0000320193-23-000106",
    form_type="10-K",
    filed_date="2023-11-03",
    item_number="PART II, Item 7",
    item_title="Management's Discussion and Analysis of Financial Condition and Results of Operations",
    text=(
        "Fiscal Period. The Company's fiscal year is the 52- or 53-week period that ends on the last "
        "Saturday of September. An additional week is included in the first fiscal quarter every five or "
        "six years to realign the Company's fiscal quarters with calendar quarters, which occurred in the "
        "first quarter of 2023. The Company's fiscal year 2023 spanned 53 weeks, whereas fiscal years 2022 "
        "and 2021 spanned 52 weeks each.\n\n"
        "Fiscal Year Highlights. The Company's total net sales were $383.3 billion and net income was "
        "$97.0 billion during 2023.\n\n"
        "The Company's total net sales decreased 3% or $11.0 billion during 2023 compared to 2022. The "
        "weakness in foreign currencies relative to the U.S. dollar accounted for more than the entire "
        "year-over-year decrease in total net sales, which consisted primarily of lower net sales of Mac "
        "and iPhone, partially offset by higher net sales of Services."
    ),
)

APPLE_REVENUE_METRICS: List[MetricEvidence] = [
    MetricEvidence(
        fiscal_year=2022,
        value=394328000000,
        unit="USD",
        period_start="2021-09-26",
        period_end="2022-09-24",
        adsh="0000320193-24-000123",
        filed_date="2024-11-01",
        variable_name="NET SALES | ANNUAL",
    ),
    MetricEvidence(
        fiscal_year=2023,
        value=383285000000,
        unit="USD",
        period_start="2022-09-25",
        period_end="2023-09-30",
        adsh="0000320193-25-000079",
        filed_date="2025-10-31",
        variable_name="NET SALES | ANNUAL",
    ),
]
