from unittest import mock

import requests
from streamlit.testing.v1 import AppTest


def _app():
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    return at


def test_fixture_mode_without_model():
    at = _app()
    at.sidebar.toggle[0].set_value(False)
    at.sidebar.button[0].click().run()
    assert not at.exception
    page = " ".join(m.value for m in at.markdown)
    assert "Revenue decreased by $11.04B, or 2.8%, from FY2022 to FY2023." in page
    assert "0000320193-23-000106" in page and "0000320193-25-000079" in page
    assert any("Fixture mode" in i.value for i in at.info)


def test_model_failure_does_not_crash():
    with mock.patch("src.ollama_client.requests.post", side_effect=requests.ConnectionError()):
        at = _app()
        at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("Model explanation unavailable" in w.value for w in at.warning)


def test_live_mode_fails_gracefully():
    at = _app()
    at.session_state["mode"] = "live"
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("fixture mode" in e.value for e in at.error)
