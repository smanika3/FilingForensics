"""Curated company list plus resolution of free-text company names/tickers."""
import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Company:
    cik: str
    name: str
    ticker: str
    aliases: Tuple[str, ...] = ()


CURATED: Tuple[Company, ...] = (
    Company("0000320193", "Apple Inc.", "AAPL", ("apple",)),
    Company("0000789019", "Microsoft Corp", "MSFT", ("microsoft", "msft")),
    Company("0001045810", "NVIDIA Corp", "NVDA", ("nvidia",)),
    Company("0001018724", "Amazon.com Inc", "AMZN", ("amazon",)),
    Company("0001652044", "Alphabet Inc.", "GOOGL", ("alphabet", "google")),
    Company("0001326801", "Meta Platforms, Inc.", "META", ("meta", "facebook")),
    Company("0001318605", "Tesla, Inc.", "TSLA", ("tesla",)),
    Company("0000019617", "JPMorgan Chase & Co", "JPM", ("jpmorgan", "jp morgan", "chase")),
    Company("0000021344", "Coca-Cola Co", "KO", ("coca-cola", "coca cola", "coke")),
    Company("0001065280", "Netflix Inc", "NFLX", ("netflix",)),
)


class CompanyNotFound(LookupError):
    pass


class AmbiguousCompany(LookupError):
    def __init__(self, query: str, matches: Sequence[Company]):
        super().__init__(f"'{query}' matches several companies")
        self.query, self.matches = query, list(matches)


def match_curated(text: str) -> Optional[Company]:
    """Find a curated company mentioned anywhere in free text (name, alias, or uppercase ticker)."""
    lower = text.lower()
    for company in CURATED:
        if any(re.search(rf"\b{re.escape(a)}\b", lower) for a in company.aliases):
            return company
        if re.search(rf"\b{company.ticker}\b", text):
            return company
    return None


def by_cik(cik: str) -> Optional[Company]:
    return next((c for c in CURATED if c.cik == cik), None)


Lookup = Callable[[str], List[Company]]


def resolve(company_text: str, lookup: Optional[Lookup] = None) -> Company:
    """Curated first; otherwise a live SEC lookup (if provided). Raises CompanyNotFound / AmbiguousCompany."""
    curated = match_curated(company_text)
    if curated:
        return curated
    if lookup is None:
        raise CompanyNotFound(
            f"'{company_text}' is not in the fixture company list. Switch to live mode to search all SEC filers."
        )
    matches = lookup(company_text.strip())
    if not matches:
        raise CompanyNotFound(f"No SEC filer found matching '{company_text}'.")
    exact = [m for m in matches if m.ticker.upper() == company_text.strip().upper() or m.name.lower() == company_text.strip().lower()]
    if len(exact) == 1:
        return exact[0]
    if len(matches) == 1:
        return matches[0]
    raise AmbiguousCompany(company_text, matches)
