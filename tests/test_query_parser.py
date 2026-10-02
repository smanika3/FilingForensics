import json
from unittest import mock

import pytest
import requests

from src.config import Config
from src.query_parser import parse_question, parse_rules


@pytest.mark.parametrize(
    "question,cik,metric,years",
    [
        ("How did Apple's revenue change from FY2022 to FY2023?", "0000320193", "revenue", (2022, 2023)),
        ("Microsoft net income 2023 vs 2024", "0000789019", "net_income", (2023, 2024)),
        ("What was NVDA EPS in FY24?", "0001045810", "eps_diluted", (2023, 2024)),
        ("Tesla gross margin 2022 to 2023", "0001318605", "gross_profit", (2022, 2023)),
        ("total assets of Netflix", "0001065280", "total_assets", None),
        ("R&D spending for Alphabet 2021 to 2023", "0001652044", "rnd", (2021, 2023)),
        ("Google operating cash flow 2024", "0001652044", "operating_cash_flow", (2023, 2024)),
    ],
)
def test_rules(question, cik, metric, years):
    p = parse_rules(question)
    assert (p.cik, p.metric_key, p.years) == (cik, metric, years) and p.complete


def test_uncurated_company_text_extracted():
    p = parse_rules("What is Walmart's operating cash flow in 2023?")
    assert p.company_text == "Walmart" and p.cik is None and p.metric_key == "operating_cash_flow"


def test_llm_fallback_fills_company():
    resp = mock.Mock(raise_for_status=lambda: None,
                     json=lambda: {"response": json.dumps({"company": "Costco", "metric": "revenue", "start_year": 2022, "end_year": 2023})})
    with mock.patch("src.ollama_client.requests.post", return_value=resp):
        p = parse_question("how is costco doing lately", Config())
    assert p.source == "rules+llm" and p.company_text == "Costco" and p.metric_key == "revenue" and p.years == (2022, 2023)


def test_llm_invalid_metric_rejected_and_defaults_to_revenue():
    resp = mock.Mock(raise_for_status=lambda: None,
                     json=lambda: {"response": json.dumps({"company": "Costco", "metric": "vibes", "start_year": "x"})})
    with mock.patch("src.ollama_client.requests.post", return_value=resp):
        p = parse_question("how is costco doing lately", Config())
    assert p.metric_key == "revenue" and p.years is None and any("defaulting" in n for n in p.notes)


def test_llm_unavailable_is_noted_not_raised():
    with mock.patch("src.ollama_client.requests.post", side_effect=requests.ConnectionError()):
        p = parse_question("how is it going", Config())
    assert p.company_text is None and any("unavailable" in n for n in p.notes)
