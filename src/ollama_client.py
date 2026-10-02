"""Local Ollama evidence synthesizer. The model explains evidence; it never computes the authoritative numbers."""
import json
import time
from typing import Optional, Sequence
from urllib.parse import urlparse

import requests

from src.answer_schema import ModelAnswer, parse_model_answer
from src.config import Config, get_config
from src.models import MetricEvidence, RevenueChange, TextEvidence, format_usd_billions

PROMPT_TEMPLATE = """You are FilingForensics, an evidence-constrained SEC filing assistant.

Use only the supplied evidence. Do not invent facts, quotes, causes, or citations.
If the evidence does not support a claim, say that it is not established.
Do not provide investment, legal, or compliance advice.
The deterministic calculation below is authoritative; do not recompute or alter it.

Return only a compact JSON object (each text field at most two sentences, at most 3 limitations) with these fields:
- answer: concise answer
- calculation: explain the numeric change
- narrative_evidence: explain which supplied passage is relevant
- citations: array of source identifiers (use only the ADSH accession IDs supplied)
- limitations: array of limitations

Question:
{question}

Deterministic calculation (authoritative):
{calculation}

Numeric evidence:
{metric_evidence}

Narrative evidence:
{text_evidence}
"""

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def build_prompt(question: str, change: RevenueChange, metrics: Sequence[MetricEvidence], text: TextEvidence) -> str:
    calculation = (
        f"{change.summary} Absolute change: {change.absolute_change} USD "
        f"({format_usd_billions(change.absolute_change)}); percent change: {change.percent_change:.4f}%."
    )
    metric_json = json.dumps(
        [
            {
                "fiscal_year": m.fiscal_year,
                "value": m.value,
                "unit": m.unit,
                "period": f"{m.period_start} to {m.period_end}",
                "adsh": m.adsh,
                "filed_date": m.filed_date,
            }
            for m in metrics
        ],
        indent=1,
    )
    text_block = (
        f"[{text.adsh}] {text.form_type} filed {text.filed_date}, {text.item_number} "
        f"({text.item_title}):\n{text.text}"
    )
    return PROMPT_TEMPLATE.format(
        question=question, calculation=calculation, metric_evidence=metric_json, text_evidence=text_block
    )


def synthesize(prompt: str, config: Optional[Config] = None) -> ModelAnswer:
    """Call local Ollama. Always returns a ModelAnswer; never raises."""
    cfg = config or get_config()
    host = urlparse(cfg.ollama_host).hostname
    if host not in LOCAL_HOSTS:
        return ModelAnswer(error=f"Refusing non-localhost Ollama host: {host}", model=cfg.ollama_model)
    payload = {
        "model": cfg.ollama_model,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 700},
        "prompt": prompt,
    }
    started = time.monotonic()
    try:
        resp = requests.post(f"{cfg.ollama_host.rstrip('/')}/api/generate", json=payload, timeout=cfg.ollama_timeout)
        resp.raise_for_status()
        raw = resp.json().get("response", "")
    except requests.Timeout:
        result = ModelAnswer(error=f"Ollama timed out after {cfg.ollama_timeout}s")
    except requests.ConnectionError:
        result = ModelAnswer(error=f"Ollama unavailable at {cfg.ollama_host}")
    except (requests.RequestException, ValueError) as exc:
        result = ModelAnswer(error=f"Ollama request failed: {exc}")
    else:
        result = parse_model_answer(raw)
    result.latency_s = round(time.monotonic() - started, 2)
    result.model = cfg.ollama_model
    return result
