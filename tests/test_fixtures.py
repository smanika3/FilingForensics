from src.fixtures import APPLE_CIK, APPLE_MDNA_TEXT, APPLE_REVENUE_METRICS


def test_text_evidence_provenance():
    assert APPLE_MDNA_TEXT.cik == APPLE_CIK
    assert APPLE_MDNA_TEXT.adsh == "0000320193-23-000106"
    assert APPLE_MDNA_TEXT.item_number == "PART II, Item 7"
    assert "decreased 3% or $11.0 billion" in APPLE_MDNA_TEXT.text


def test_metric_evidence_provenance():
    by_year = {m.fiscal_year: m for m in APPLE_REVENUE_METRICS}
    assert by_year[2022].adsh == "0000320193-24-000123"
    assert by_year[2023].adsh == "0000320193-25-000079"
    for m in APPLE_REVENUE_METRICS:
        assert m.unit == "USD" and m.filed_date and m.period_start and m.period_end
