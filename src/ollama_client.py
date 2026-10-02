"""Local Ollama evidence synthesizer. The model explains evidence; it never computes the authoritative numbers."""
import json
import time
from typing import Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests

from src.answer_schema import ModelAnswer, parse_model_answer
from src.config import Config, get_config
from src.models import MetricChange, MetricEvidence, TextEvidence, format_value

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


def build_prompt(
    question: str, change: MetricChange, metrics: Sequence[MetricEvidence], text: Optional[TextEvidence]
) -> str:
    calculation = (
        f"{change.summary} Absolute change: {change.absolute_change} {change.unit} "
        f"({format_value(change.absolute_change, change.unit)}); percent change: {change.percent_change:.4f}%."
    )
    metric_json = json.dumps(
        [
            {
                "fiscal_year": m.fiscal_year,
                "metric": change.label,
                "value": m.value,
                "unit": change.unit,
                "period": f"{m.period_start or 'as of'} to {m.period_end}",
                "adsh": m.adsh,
                "filed_date": m.filed_date,
            }
            for m in metrics
        ],
        indent=1,
    )
    if text is None:
        text_block = "No MD&A narrative is available for this filing. Say that the narrative cause is not established."
    else:
        text_block = (
            f"[{text.adsh}] {text.form_type} filed {text.filed_date}, {text.item_number} "
            f"({text.item_title}):\n{text.text}"
        )
    return PROMPT_TEMPLATE.format(
        question=question, calculation=calculation, metric_evidence=metric_json, text_evidence=text_block
    )


def generate_json(prompt: str, config: Optional[Config] = None, num_predict: int = 700) -> Tuple[str, Optional[str], float]:
    """Call local Ollama in JSON mode. Returns (raw_text, error, latency_s); never raises."""
    cfg = config or get_config()
    host = urlparse(cfg.ollama_host).hostname
    if host not in LOCAL_HOSTS:
        return "", f"Refusing non-localhost Ollama host: {host}", 0.0
    payload = {
        "model": cfg.ollama_model,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": num_predict},
        "prompt": prompt,
    }
    started = time.monotonic()
    raw, error = "", None
    try:
        resp = requests.post(f"{cfg.ollama_host.rstrip('/')}/api/generate", json=payload, timeout=cfg.ollama_timeout)
        resp.raise_for_status()
        raw = resp.json().get("response", "")
    except requests.Timeout:
        error = f"Ollama timed out after {cfg.ollama_timeout}s"
    except requests.ConnectionError:
        error = f"Ollama unavailable at {cfg.ollama_host}"
    except (requests.RequestException, ValueError) as exc:
        error = f"Ollama request failed: {exc}"
    return raw, error, round(time.monotonic() - started, 2)


def synthesize(prompt: str, config: Optional[Config] = None) -> ModelAnswer:
    """Call local Ollama. Always returns a ModelAnswer; never raises."""
    cfg = config or get_config()
    raw, error, latency = generate_json(prompt, cfg)
    result = ModelAnswer(error=error) if error else parse_model_answer(raw)
    result.latency_s = latency
    result.model = cfg.ollama_model
    return result
