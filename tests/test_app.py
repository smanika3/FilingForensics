from unittest import mock

import requests
from streamlit.testing.v1 import AppTest

from src.retrieval import LiveModeUnavailable


def _ask(question, mode="fixture", use_model=False, post_effect=requests.ConnectionError()):
    # mock st.pills to avoid ButtonGroup serialization bug in AppTest:
    # selection_mode="single" defaults value to None which is not iterable,
    # crashing get_widget_states() on subsequent .run() calls.
    with mock.patch("src.ollama_client.requests.post", side_effect=post_effect), \
         mock.patch("streamlit.pills", return_value=None):
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        at.session_state["mode"] = mode
        at.sidebar.toggle[0].set_value(use_model)
        at.text_input(key="q").input(question)
        at.button(key="send").click().run()
    return at


def _page(at):
    return " ".join(m.value for m in at.markdown)


def test_landing_shows_centered_box_and_suggestions():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    assert at.text_input(key="q") is not None
    assert any("Fixture mode" in c.value for c in at.caption)


def test_fixture_question_renders_answer_evidence_and_tables():
    at = _ask("How did Apple's revenue change from FY2022 to FY2023?")
    assert not at.exception
    page = _page(at)
    assert "Apple Inc. revenue decreased by \\$11.04B, or 2.8%, from FY2022 to FY2023." in page
    assert "0000320193-23-000106" in page
    assert len(at.dataframe) >= 2  # metric table + MD&A table
    assert "Question understood" in page and "Change calculated" in page


def test_model_failure_does_not_crash():
    at = _ask("Apple revenue 2022 to 2023", use_model=True)
    assert not at.exception
    assert any("Model explanation unavailable" in w.value for w in at.warning)


def test_unknown_company_in_fixture_mode_is_recoverable():
    at = _ask("What was Costco's revenue in 2023?")
    assert not at.exception
    assert any("live mode" in e.value for e in at.error)


def test_live_mode_fails_gracefully_and_recovers():
    with mock.patch("src.snowflake_client.fetch_live_evidence", side_effect=LiveModeUnavailable("Live mode unavailable")):
        at = _ask("Apple revenue 2022 to 2023", mode="live")
        assert not at.exception
        assert any("fixture mode" in e.value for e in at.error)
        recover = next(b for b in at.button if "Switch to fixture mode" in b.label)
        recover.click().run()
        assert at.session_state["mode"] == "fixture" and not at.exception

