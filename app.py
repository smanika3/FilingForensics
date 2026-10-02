"""FilingForensics: evidence-first SEC filing review (fixture-first, local Ollama, optional live Snowflake)."""
import time
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

from src.calculations import EvidenceError, change_for_metric
from src.companies import CURATED, AmbiguousCompany, Company, CompanyNotFound, resolve
from src.config import get_config
from src.fixture_store import FixtureMissing, get_fixture_evidence, load as load_fixtures
from src.mdna import Table
from src.metrics import METRICS
from src.models import format_value
from src.ollama_client import build_prompt, synthesize
from src.query_parser import ParsedQuery, parse_question
from src.retrieval import EvidenceBundle, LiveModeUnavailable, get_evidence

st.set_page_config(page_title="FilingForensics", page_icon=":material/fact_check:", layout="centered")

cfg = get_config()
EXAMPLES = [
    "How did Apple's revenue change from FY2022 to FY2023?",
    "Microsoft net income 2023 vs 2024",
    "What was NVIDIA's diluted EPS in the latest year?",
    "Tesla gross margin 2022 to 2023",
    "Netflix total assets 2023",
]
LIMITATIONS = [
    "Values are XBRL facts as originally reported in each fiscal year's own 10-K; later restatements are not applied.",
    "Fiscal years follow each company's own calendar (e.g. Microsoft ends in June, NVIDIA in January).",
    "The narrative is a keyword-selected set of MD&A passages, not the full filing.",
    "Percent change is relative to the absolute value of the starting year.",
    "The language model only explains supplied evidence; all numbers are computed deterministically.",
]
DEFAULTS = {"mode": "fixture", "q": "", "result": None, "error": None, "choices": None, "override": None,
            "auto_run": False, "last_steps": None}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def md(text: str) -> str:
    """Escape '$' so model/filing text is not rendered as LaTeX."""
    return text.replace("$", "\\$")


def use_fixture_mode() -> None:
    st.session_state.mode = "fixture"
    st.session_state.error = None


def fill_from_company() -> None:
    name = st.session_state.get("company_pill")
    if name:
        st.session_state.q = f"How did {name.split(' (')[0]}'s revenue change in the latest fiscal year?"


def fill_from_example() -> None:
    if st.session_state.get("example_pill"):
        st.session_state.q = st.session_state.example_pill


def choose_company(company: Company) -> None:
    st.session_state.override = (company.cik, company.name)
    st.session_state.choices = None
    st.session_state.auto_run = True


def new_question() -> None:
    for key in ("result", "error", "choices", "override", "last_steps"):
        st.session_state[key] = None
    st.session_state.q = ""


@st.cache_data(ttl=3600, max_entries=64, show_spinner=False)
def live_evidence(cik: str, name: str, metric_key: str, years: Optional[Tuple[int, int]]) -> EvidenceBundle:
    from src.snowflake_client import fetch_live_evidence

    return fetch_live_evidence(cik, name, metric_key, years)


@st.cache_data(ttl=3600, max_entries=64, show_spinner=False)
def live_lookup(text: str) -> List[Company]:
    from src.snowflake_client import lookup_companies

    return lookup_companies(text)


def fixture_evidence(cik: str, metric_key: str, years: Optional[Tuple[int, int]]) -> EvidenceBundle:
    try:
        return get_fixture_evidence(cik, metric_key, years)
    except FixtureMissing:
        # Verified Apple revenue baseline works even without the snapshot file.
        if cik == "0000320193" and metric_key == "revenue" and years in (None, (2022, 2023)) and not load_fixtures()["companies"]:
            return get_evidence("fixture")
        raise


class Steps:
    """Timed progress lines inside an st.status container."""

    def __init__(self, status) -> None:
        self.status, self.started, self.log, self.lines = status, time.monotonic(), [], []

    def run(self, label: str, fn):
        self.status.update(label=f"{label}...")
        t0 = time.monotonic()
        result = fn()
        elapsed = time.monotonic() - t0
        self.log.append({"step": label, "seconds": round(elapsed, 2)})
        return result, elapsed

    def _line(self, text: str) -> None:
        self.lines.append(text)
        st.markdown(text)

    def done(self, message: str) -> None:
        self._line(f":green[:material/check_circle:] {message}")

    def warn(self, message: str) -> None:
        self._line(f":orange[:material/warning:] {message}")

    def fail(self, message: str, label: str = "Could not answer") -> None:
        self._line(f":red[:material/cancel:] {message}")
        self.status.update(label=label, state="error", expanded=True)
        st.session_state.last_steps = (label, "error", self.lines)


def run_pipeline(question: str, mode: str, use_model: bool) -> None:
    st.session_state.error, st.session_state.result, st.session_state.choices = None, None, None
    with st.status("Understanding your question...", expanded=True) as status:
        steps = Steps(status)
        parsed: ParsedQuery
        parsed, t = steps.run("Understanding your question", lambda: parse_question(question, cfg, use_llm=True))
        if st.session_state.override:
            parsed.cik, parsed.company_text = st.session_state.override
        if not parsed.company_text:
            steps.fail("I couldn't find a company in that question. Try one of the suggestions, e.g. *Apple revenue 2023*.")
            st.session_state.error = "no_company"
            return
        metric = METRICS[parsed.metric_key]
        span = f"FY{parsed.years[0]} → FY{parsed.years[1]}" if parsed.years else "latest two fiscal years"
        steps.done(f"Question understood ({t:.1f}s, {parsed.source}): **{md(parsed.company_text)}** · {metric.label} · {span}")

        def _resolve() -> Company:
            if parsed.cik:
                return Company(parsed.cik, parsed.company_text, "")
            return resolve(parsed.company_text, lookup=live_lookup if mode == "live" else None)

        try:
            company, t = steps.run("Resolving company", _resolve)
        except AmbiguousCompany as exc:
            steps.fail(f"'{md(exc.query)}' matches several SEC filers. Pick one below.", label="Which company did you mean?")
            st.session_state.choices = exc.matches
            return
        except (CompanyNotFound, LiveModeUnavailable) as exc:
            steps.fail(md(str(exc)))
            st.session_state.error = "live" if isinstance(exc, LiveModeUnavailable) else "company"
            return
        steps.done(f"Company resolved ({t:.1f}s): **{md(company.name)}** · CIK `{company.cik}`")

        source = "Snowflake (read-only)" if mode == "live" else "offline fixtures"

        def _fetch() -> EvidenceBundle:
            if mode == "live":
                return live_evidence(company.cik, company.name, metric.key, parsed.years)
            return fixture_evidence(company.cik, metric.key, parsed.years)

        try:
            bundle, t = steps.run(f"Querying financial facts and MD&A from {source}", _fetch)
        except (LiveModeUnavailable, FixtureMissing) as exc:
            steps.fail(md(str(exc)))
            st.session_state.error = "live" if mode == "live" else "fixture"
            return
        steps.done(
            f"Evidence retrieved ({t:.1f}s): {len(bundle.metrics)} fact rows, "
            f"{'MD&A excerpt' if bundle.text else 'no MD&A narrative'}"
        )

        try:
            change, t = steps.run(
                "Calculating change deterministically",
                lambda: change_for_metric(bundle.metrics, metric, *bundle.years, company=company.name),
            )
        except EvidenceError as exc:
            steps.fail(f"Evidence validation failed: {md(str(exc))}")
            st.session_state.error = "evidence"
            return
        steps.done(f"Change calculated ({t:.2f}s): {format_value(change.absolute_change, change.unit)} ({change.percent_change:+.2f}%)")

        model_answer = None
        if use_model:
            model_answer, t = steps.run(
                f"Asking {cfg.ollama_model} to explain the evidence (usually 10–25s)",
                lambda: synthesize(build_prompt(question, change, bundle.metrics, bundle.text), cfg),
            )
            if model_answer.ok:
                # Programmatically enforce verified citation list (MD&A + metric filings)
                verified = []
                if bundle.text and bundle.text.adsh:
                    verified.append(bundle.text.adsh)
                for m in bundle.metrics:
                    if m.adsh not in verified:
                        verified.append(m.adsh)
                model_answer.citations = verified
                steps.done(f"Explanation ready ({t:.1f}s, {cfg.ollama_model} on localhost)")
            else:
                steps.warn(f"Model explanation unavailable ({md(model_answer.error or '')}); using the deterministic answer.")
        total = time.monotonic() - steps.started
        status.update(label=f"Answered in {total:.1f}s", state="complete", expanded=False)
        st.session_state.last_steps = (f"Answered in {total:.1f}s", "complete", steps.lines)
    st.session_state.result = {
        "question": question, "parsed": parsed, "bundle": bundle, "change": change,
        "model": model_answer, "steps": steps.log,
    }


# ---------- sidebar settings ----------
with st.sidebar:
    st.header("Settings")
    mode = st.radio("Data mode", ["fixture", "live"], horizontal=True, key="mode",
                    help="Fixture: offline verified snapshot. Live: read-only Snowflake queries.")
    use_model = st.toggle("Explain with local model", value=True, help=f"Ollama {cfg.ollama_model} on localhost")
    st.caption("Not investment, legal, or compliance advice.")

submitting = (bool(st.session_state.get("send")) and bool(st.session_state.q.strip())) or st.session_state.auto_run
has_output = submitting or any(st.session_state[k] for k in ("result", "error", "choices"))

# ---------- query bar (centered on landing, top after a query) ----------
if not has_output:
    for _ in range(4):
        st.write("")
    st.title(":material/fact_check: FilingForensics", anchor=False)
    st.caption("Ask about a public company's 10-K. Every number is computed from SEC filings and cited.")
    st.pills("Companies", [f"{c.name} ({c.ticker})" for c in CURATED], key="company_pill", on_change=fill_from_company,
             help="Pick one to prefill the box, or type any other company.")
else:
    st.markdown("#### :material/fact_check: FilingForensics")

with st.form("ask", border=not has_output):
    cols = st.columns([8, 1], vertical_alignment="bottom")
    cols[0].text_input("Question", key="q", label_visibility="collapsed",
                       placeholder="e.g. How did Microsoft's net income change from 2023 to 2024?")
    submitted = cols[1].form_submit_button(":material/send:", type="primary", width="stretch", key="send")

if mode == "fixture":
    st.caption(":material/inventory_2: Fixture mode — using verified sample evidence (offline)")
else:
    st.caption(":material/cloud: Live mode — read-only queries against SNOWFLAKE_PUBLIC_DATA_FREE")

if not has_output:
    st.pills("Try asking", EXAMPLES, key="example_pill", on_change=fill_from_example)

if st.session_state.auto_run:
    st.session_state.auto_run, submitted = False, True
elif submitted:
    st.session_state.override = None

if submitted and st.session_state.q.strip():
    st.session_state.last_steps = None
    run_pipeline(st.session_state.q.strip(), mode, use_model)
elif st.session_state.last_steps:
    label, state, lines = st.session_state.last_steps
    with st.status(label, state=state, expanded=state == "error"):
        for line in lines:
            st.markdown(line)

# ---------- error / choice states ----------
if st.session_state.choices:
    st.warning("Several SEC filers match. Which one did you mean?", icon=":material/help:")
    for c in st.session_state.choices:
        st.button(f"{c.name}" + (f" ({c.ticker})" if c.ticker else "") + f" · CIK {c.cik}", key=f"pick_{c.cik}",
                  on_click=choose_company, args=(c,))
if st.session_state.error:
    hints = {
        "no_company": "Try: *Apple revenue 2022 to 2023* or pick a company above.",
        "company": "Check the spelling, use a ticker (e.g. COST), or switch to live mode to search all SEC filers.",
        "live": "Live mode failed. You can switch to fixture mode and keep going.",
        "fixture": "That scenario isn't in the offline fixtures. Switch to live mode to query it.",
        "evidence": "The filing data didn't pass validation for that request; try another year or metric.",
    }
    st.error(hints.get(st.session_state.error, "Something went wrong."), icon=":material/error:")
    if st.session_state.error == "live":
        st.button("Switch to fixture mode", icon=":material/inventory_2:", on_click=use_fixture_mode)
if has_output:
    st.button("New question", icon=":material/add:", on_click=new_question)

result = st.session_state.result
if not result:
    st.stop()

# ---------- results ----------
bundle: EvidenceBundle = result["bundle"]
change = result["change"]
model_answer = result["model"]
parsed: ParsedQuery = result["parsed"]
metric = METRICS[bundle.metric_key]
unit = change.unit

with st.container(border=True):
    st.subheader("Answer", anchor=False)
    st.markdown(f"**{md(change.summary)}**")
    st.badge(
        "Live Snowflake evidence" if bundle.mode == "live" else "Fixture evidence",
        icon=":material/cloud:" if bundle.mode == "live" else ":material/inventory_2:",
        color="green" if bundle.mode == "live" else "blue",
    )
    with st.container(horizontal=True):
        st.metric(f"FY{change.old.fiscal_year} {metric.label.lower()}", format_value(change.old.value, unit))
        st.metric(
            f"FY{change.new.fiscal_year} {metric.label.lower()}",
            format_value(change.new.value, unit),
            delta=f"{format_value(change.absolute_change, unit)} ({change.percent_change:.2f}%)",
        )
    st.caption(
        f"Deterministic calculation: {change.new.value:,} − {change.old.value:,} = {change.absolute_change:,} {unit}; "
        f"{change.absolute_change:,} / |{change.old.value:,}| × 100 = {change.percent_change:.4f}%"
    )
for note in bundle.notes + parsed.notes:
    st.info(md(note), icon=":material/info:")

with st.container(border=True):
    st.subheader(":material/smart_toy: Model explanation", anchor=False)
    if model_answer is None:
        st.caption("Local model disabled. The deterministic answer above stands on its own.")
    elif model_answer.ok:
        st.markdown(md(model_answer.answer))
        st.markdown(f"**Calculation:** {md(model_answer.calculation)}")
        st.markdown(f"**Narrative evidence:** {md(model_answer.narrative_evidence)}")
        citations = []
        if bundle.text and bundle.text.adsh:
            citations.append(f"Narrative MD&A: `{bundle.text.adsh}`")
        for m in bundle.metrics:
            citations.append(f"FY{m.fiscal_year} metric: `{m.adsh}`")
        if citations:
            st.markdown("**Cited accessions:** " + " · ".join(citations))
        st.caption(f"{model_answer.model} · {model_answer.latency_s}s · explanation only, not the source of truth")
    else:
        st.warning(
            f"Model explanation unavailable ({md(model_answer.error or '')}). Showing the deterministic result only.",
            icon=":material/warning:",
        )

st.subheader("Metric evidence", anchor=False)
df = pd.DataFrame(
    [
        {
            "Fiscal year": f"FY{m.fiscal_year}",
            f"{metric.label} ({unit})": m.value,
            "Display": format_value(m.value, unit),
            "Period": f"{m.period_start} → {m.period_end}" if m.period_start else f"as of {m.period_end}",
            "Source accession": m.adsh,
            "Filed": m.filed_date,
            "Variable": m.variable_name,
        }
        for m in bundle.metrics
    ]
)
st.dataframe(df, hide_index=True)
if len(df) > 1:
    st.bar_chart(df, x="Fiscal year", y=f"{metric.label} ({unit})", height=220)


def unique_header(row: List[str]) -> List[str]:
    seen: dict = {}
    out = []
    for i, cell in enumerate(row):
        name = cell or ("Line item" if i == 0 else f"Col {i}")
        seen[name] = seen.get(name, 0) + 1
        out.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return out


text = bundle.text
with st.expander(":material/description: Narrative evidence (MD&A excerpt)", expanded=True):
    if text is None:
        st.caption("No MD&A narrative available for this filing.")
    else:
        st.markdown(
            f"**{text.form_type}** · accession `{text.adsh}` · filed {text.filed_date} · {text.item_number} — {md(text.item_title)}"
        )
        blocks = bundle.text_blocks or [p for p in text.text.split("\n\n") if p.strip()]
        for block in blocks:
            if isinstance(block, Table):
                if len(block.rows) > 1:
                    st.dataframe(pd.DataFrame(block.rows[1:], columns=unique_header(block.rows[0])), hide_index=True)
            else:
                st.markdown(md(block))

with st.expander(":material/verified: Provenance and limitations"):
    lines = []
    if text is not None:
        lines.append(f"- Narrative: `{text.adsh}` ({text.form_type}, filed {text.filed_date}, {text.item_number})")
    lines += [
        f"- FY{m.fiscal_year} {metric.label.lower()}: `{m.adsh}` (filed {m.filed_date}), "
        + (f"period {m.period_start} → {m.period_end}" if m.period_start else f"as of {m.period_end}")
        for m in bundle.metrics
    ]
    st.markdown("\n".join(lines))
    st.markdown("**Limitations**\n" + "\n".join(f"- {l}" for l in LIMITATIONS))
    if model_answer is not None and model_answer.ok and model_answer.limitations:
        st.markdown("**Model-noted limitations**\n" + "\n".join(f"- {md(l)}" for l in model_answer.limitations))
    st.caption("FilingForensics does not provide investment, legal, or compliance advice.")

with st.expander(":material/bug_report: Debug"):
    st.json(
        {
            "mode": bundle.mode,
            "parsed": {"company": parsed.company_text, "cik": bundle.cik, "metric": bundle.metric_key,
                       "years": list(bundle.years), "source": parsed.source},
            "steps": result["steps"],
            "row_counts": bundle.row_counts,
            "sql": bundle.sql or "none (fixture mode)",
            "model": cfg.ollama_model,
            "ollama_host": cfg.ollama_host,
            "model_latency_s": getattr(model_answer, "latency_s", None),
            "model_ok": getattr(model_answer, "ok", None),
            "model_error": getattr(model_answer, "error", None),
        }
    )
    if parsed.llm_raw:
        st.caption("LLM parser output")
        st.code(parsed.llm_raw, language="json")
    if model_answer is not None and model_answer.raw:
        st.caption("Model explanation output")
        st.code(model_answer.raw, language="json")
