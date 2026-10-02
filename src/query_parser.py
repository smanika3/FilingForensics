"""Turn a free-text question into (company, metric, years). Rules first; local LLM only as a fallback."""
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from src.answer_schema import _extract_json
from src.companies import match_curated
from src.config import Config
from src.metrics import METRICS

_YEAR = re.compile(r"\b(?:FY\s?'?)?((?:19|20)\d{2})\b", re.I)
_SHORT_FY = re.compile(r"\bFY\s?'?(\d{2})\b", re.I)
_STOPWORDS = {"FY", "MD", "MDA", "USD", "EPS", "R", "D", "SEC", "How", "What", "Did", "Does", "Show", "Compare", "The", "Why", "Is", "Was"}
_COMPANY_PATTERNS = (
    re.compile(r"\b([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,3})'s\b"),
    re.compile(r"\b(?:for|of|at|did|does)\s+([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,3})"),
)

LLM_PROMPT = """Extract fields from a question about a public company's SEC filings.
Return only JSON: {{"company": string or null, "metric": one of {metrics} or null, "start_year": integer or null, "end_year": integer or null}}.
Use null when the question does not say. Do not guess numbers.

Question: {question}
"""


@dataclass
class ParsedQuery:
    question: str
    company_text: Optional[str] = None
    cik: Optional[str] = None
    metric_key: Optional[str] = None
    years: Optional[Tuple[int, int]] = None  # (old, new); None -> latest available pair
    source: str = "rules"
    notes: List[str] = field(default_factory=list)
    llm_raw: str = ""

    @property
    def complete(self) -> bool:
        return bool(self.company_text and self.metric_key)


def _match_metric(question: str) -> Optional[str]:
    lower = question.lower()
    best, best_len = None, 0
    for metric in METRICS.values():
        for syn in metric.synonyms:
            if re.search(rf"(?<![\w]){re.escape(syn)}(?![\w])", lower) and len(syn) > best_len:
                best, best_len = metric.key, len(syn)
    return best


def _match_years(question: str) -> Optional[Tuple[int, int]]:
    years = sorted({int(y) for y in _YEAR.findall(question)} | {2000 + int(y) for y in _SHORT_FY.findall(question)})
    if not years:
        return None
    if len(years) == 1:
        return years[0] - 1, years[0]
    return years[0], years[-1]


def _match_company_text(question: str) -> Optional[str]:
    for pattern in _COMPANY_PATTERNS:
        for match in pattern.finditer(question):
            words = [w for w in match.group(1).split() if w not in _STOPWORDS and not _YEAR.fullmatch(w)]
            if words:
                return " ".join(words)
    return None


def parse_rules(question: str) -> ParsedQuery:
    parsed = ParsedQuery(question=question)
    company = match_curated(question)
    if company:
        parsed.company_text, parsed.cik = company.name, company.cik
    else:
        parsed.company_text = _match_company_text(question)
    parsed.metric_key = _match_metric(question)
    parsed.years = _match_years(question)
    return parsed


def parse_with_llm(question: str, config: Config) -> ParsedQuery:
    from src.ollama_client import generate_json  # local import keeps parsing usable without requests in tests

    prompt = LLM_PROMPT.format(metrics=json.dumps(sorted(METRICS)), question=question)
    raw, error, _ = generate_json(prompt, config, num_predict=120)
    parsed = ParsedQuery(question=question, source="llm", llm_raw=raw)
    if error:
        parsed.notes.append(f"LLM parser unavailable: {error}")
        return parsed
    data = _extract_json(raw) or {}
    company = data.get("company")
    if isinstance(company, str) and company.strip():
        curated = match_curated(company)
        parsed.company_text = curated.name if curated else company.strip()
        parsed.cik = curated.cik if curated else None
    metric = data.get("metric")
    if metric in METRICS:
        parsed.metric_key = metric
    years = [y for y in (data.get("start_year"), data.get("end_year")) if isinstance(y, int) and 1990 < y < 2100]
    if years:
        parsed.years = (min(years), max(years)) if len(set(years)) > 1 else (years[0] - 1, years[0])
    return parsed


def parse_question(question: str, config: Optional[Config] = None, use_llm: bool = True) -> ParsedQuery:
    """Rules first; fill gaps with the local LLM; default the metric to revenue if still unknown."""
    parsed = parse_rules(question)
    if not parsed.complete and use_llm:
        llm = parse_with_llm(question, config or Config())
        parsed.source = "rules+llm"
        parsed.llm_raw = llm.llm_raw
        parsed.notes.extend(llm.notes)
        if not parsed.company_text and llm.company_text:
            parsed.company_text, parsed.cik = llm.company_text, llm.cik
        if not parsed.metric_key and llm.metric_key:
            parsed.metric_key = llm.metric_key
        if not parsed.years and llm.years:
            parsed.years = llm.years
    if parsed.company_text and not parsed.metric_key:
        parsed.metric_key = "revenue"
        parsed.notes.append("No metric recognized; defaulting to total revenue.")
    return parsed
