import json
import os
from unittest import mock

import pytest
import requests

from src.answer_schema import parse_model_answer
from src.calculations import revenue_change
from src.config import Config
from src.fixtures import APPLE_MDNA_TEXT, APPLE_REVENUE_METRICS
from src.ollama_client import build_prompt, synthesize

GOOD = {
    "answer": "Revenue fell.",
    "calculation": "-11.04B",
    "narrative_evidence": "MD&A",
    "citations": ["0000320193-23-000106"],
    "limitations": ["Fixture data"],
}


def _prompt():
    change = revenue_change(APPLE_REVENUE_METRICS, 2022, 2023)
    return build_prompt("How did revenue change?", change, APPLE_REVENUE_METRICS, APPLE_MDNA_TEXT)


def test_prompt_contains_evidence():
    p = _prompt()
    for adsh in ("0000320193-23-000106", "0000320193-24-000123", "0000320193-25-000079"):
        assert adsh in p
    assert "-11043000000" in p and "-2.8005%" in p


def test_parse_valid_and_fenced_json():
    assert parse_model_answer(json.dumps(GOOD)).ok
    fenced = parse_model_answer("Here:\n```json\n" + json.dumps(GOOD) + "\n```")
    assert fenced.ok and fenced.citations == ["0000320193-23-000106"]


def test_parse_malformed_and_empty():
    bad = parse_model_answer("not json {oops")
    assert not bad.ok and bad.raw == "not json {oops"
    assert parse_model_answer("").error == "Empty model output"


def test_parse_missing_fields_and_string_lists():
    r = parse_model_answer(json.dumps({"answer": "x", "citations": "A", "limitations": None}))
    assert not r.ok and "calculation" in r.error and r.citations == ["A"] and r.limitations == []


@pytest.mark.parametrize(
    "exc,msg",
    [(requests.Timeout(), "timed out"), (requests.ConnectionError(), "unavailable")],
)
def test_network_failures_fall_back(exc, msg):
    with mock.patch("src.ollama_client.requests.post", side_effect=exc):
        r = synthesize("p", Config())
    assert not r.ok and msg in r.error and r.latency_s is not None


def test_non_localhost_refused():
    with mock.patch("src.ollama_client.requests.post") as post:
        r = synthesize("p", Config(ollama_host="http://example.com:11434"))
    post.assert_not_called()
    assert "non-localhost" in r.error


def test_successful_mocked_call_uses_think_false():
    resp = mock.Mock(json=lambda: {"response": json.dumps(GOOD)}, raise_for_status=lambda: None)
    with mock.patch("src.ollama_client.requests.post", return_value=resp) as post:
        r = synthesize("p", Config())
    body = post.call_args.kwargs["json"]
    assert body["think"] is False and body["options"]["temperature"] == 0 and r.ok


@pytest.mark.skipif(not os.getenv("FF_LIVE_OLLAMA"), reason="set FF_LIVE_OLLAMA=1 for live localhost smoke test")
def test_live_ollama_smoke():
    r = synthesize(_prompt(), Config(ollama_timeout=60))
    print(f"\nlatency={r.latency_s}s ok={r.ok} error={r.error}\nraw={r.raw[:600]}")
    assert r.raw or r.error  # structured result either way
