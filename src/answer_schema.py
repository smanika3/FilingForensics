"""Tolerant parsing of model output into the required answer fields."""
import json
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

REQUIRED_FIELDS = ("answer", "calculation", "narrative_evidence", "citations", "limitations")


@dataclass
class ModelAnswer:
    answer: str = ""
    calculation: str = ""
    narrative_evidence: str = ""
    citations: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    ok: bool = False
    error: Optional[str] = None
    raw: str = ""
    latency_s: Optional[float] = None
    model: str = ""


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [str(value)] if str(value).strip() else []


def _extract_json(raw: str) -> Optional[dict]:
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    candidates = [fenced.group(1)] if fenced else []
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None


def parse_model_answer(raw: str) -> ModelAnswer:
    if not raw or not raw.strip():
        return ModelAnswer(error="Empty model output", raw=raw or "")
    data = _extract_json(raw)
    if data is None:
        return ModelAnswer(error="Model output was not valid JSON", raw=raw)
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    return ModelAnswer(
        answer=str(data.get("answer", "") or ""),
        calculation=str(data.get("calculation", "") or ""),
        narrative_evidence=str(data.get("narrative_evidence", "") or ""),
        citations=_as_list(data.get("citations")),
        limitations=_as_list(data.get("limitations")),
        ok=not missing,
        error=f"Missing fields: {', '.join(missing)}" if missing else None,
        raw=raw,
    )
