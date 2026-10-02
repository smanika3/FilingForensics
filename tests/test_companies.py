import pytest

from src.companies import AmbiguousCompany, Company, CompanyNotFound, match_curated, resolve


def test_curated_alias_and_ticker():
    assert match_curated("google R&D").ticker == "GOOGL"
    assert match_curated("what about KO").ticker == "KO"
    assert match_curated("I like apples pie") is None  # word boundary


def test_unknown_company_without_lookup_is_fixture_error():
    with pytest.raises(CompanyNotFound, match="live mode"):
        resolve("Costco")


def test_lookup_zero_one_many():
    with pytest.raises(CompanyNotFound):
        resolve("Zzqxy", lookup=lambda t: [])
    one = Company("0000104169", "WALMART INC.", "WMT")
    assert resolve("Walmart", lookup=lambda t: [one]) == one
    many = [Company("1", "FORD MOTOR CO", "F"), Company("2", "FORD MOTOR CREDIT CO LLC", "")]
    with pytest.raises(AmbiguousCompany) as exc:
        resolve("Ford", lookup=lambda t: many)
    assert len(exc.value.matches) == 2
    assert resolve("F", lookup=lambda t: many).cik == "1"  # exact ticker wins
