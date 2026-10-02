import pytest

from src.calculations import change_for_metric
from src.fixture_store import FixtureMissing, get_fixture_evidence
from src.mdna import Table
from src.metrics import METRICS

APPLE = "0000320193"


def test_fixture_bundle_default_years_and_blocks():
    b = get_fixture_evidence(APPLE, "revenue")
    assert b.years == (2022, 2023) and b.mode == "fixture" and b.text.adsh == "0000320193-23-000106"
    assert isinstance(b.text_blocks[1], Table)
    assert change_for_metric(b.metrics, METRICS["revenue"], *b.years).absolute_change == -11043000000


@pytest.mark.parametrize("cik,metric,years,msg", [
    ("0000789019", "revenue", None, "not in the offline"),
    (APPLE, "net_income", None, "No offline facts"),
    (APPLE, "revenue", (2019, 2020), "not included"),
])
def test_missing_scenarios_raise(cik, metric, years, msg):
    with pytest.raises(FixtureMissing, match=msg):
        get_fixture_evidence(cik, metric, years)
