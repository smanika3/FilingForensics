"""FilingForensics: evidence-first SEC filing review (fixture-first, local Ollama)."""
import pandas as pd
import streamlit as st

from src.calculations import EvidenceError, revenue_change
from src.config import get_config
from src.models import format_usd_billions
from src.ollama_client import build_prompt, synthesize
from src.retrieval import LiveModeUnavailable, get_evidence

st.set_page_config(page_title="FilingForensics", page_icon=":material/fact_check:", layout="wide")

cfg = get_config()
QUESTIONS = {
    "How did Apple's total revenue change from FY2022 to FY2023, and what does the MD&A say about it?": (2022, 2023),
}
LIMITATIONS = [
    "Preset scope: Apple (CIK 0000320193), total net sales, FY2022 vs FY2023 only.",
    "Metric rows come from later 10-K filings (comparative periods), so their accessions differ from the MD&A filing.",
    "FY2023 spanned 53 weeks versus 52 weeks for FY2022, which affects year-over-year comparability.",
    "The narrative excerpt is a short MD&A passage, not the full filing.",
    "The language model only explains supplied evidence; the calculation is computed deterministically.",
]



def md(text: str) -> str:
    """Escape '$' so model text is not rendered as LaTeX."""
    return text.replace("$", "\\$")


st.title(":material/fact_check: FilingForensics")
st.caption("Evidence-first SEC filing review. Not investment, legal, or compliance advice.")

def use_fixture_mode() -> None:
    st.session_state.mode = "fixture"


@st.cache_data(ttl=3600, max_entries=8, show_spinner=False)
def load_live_evidence(old_year: int, new_year: int):
    """Cache live results so reruns don't reconnect (or re-prompt OAuth). Failures are not cached."""
    return get_evidence("live", old_year, new_year)


with st.sidebar:
    st.header("Controls")
    company = st.selectbox("Company", ["Apple Inc. (CIK 0000320193)"])
    question = st.selectbox("Question", list(QUESTIONS))
    mode = st.radio("Data mode", ["fixture", "live"], horizontal=True, key="mode")
    use_model = st.toggle("Explain with local model", value=True, help=f"Ollama {cfg.ollama_model} on localhost")
    run = st.button("Analyze", type="primary", icon=":material/play_arrow:", width="stretch")

if mode == "fixture":
    st.info("Fixture mode — using verified sample evidence", icon=":material/inventory_2:")
else:
    st.warning(
        "Live mode — read-only queries against SNOWFLAKE_PUBLIC_DATA_FREE (credentials from environment)",
        icon=":material/cloud:",
    )

if not run and "result" not in st.session_state:
    st.markdown("Choose a question in the sidebar and click **Analyze**.")
    st.stop()

if run:
    old_year, new_year = QUESTIONS[question]
    try:
        if mode == "live":
            with st.spinner("Querying Snowflake (text and metrics separately)..."):
                bundle = load_live_evidence(old_year, new_year)
        else:
            bundle = get_evidence("fixture")
    except LiveModeUnavailable as exc:
        st.error(str(exc), icon=":material/error:")
        st.button("Switch to fixture mode", icon=":material/inventory_2:", on_click=use_fixture_mode)
        st.stop()
    try:
        change = revenue_change(bundle.metrics, old_year, new_year)
    except EvidenceError as exc:
        st.error(f"Evidence validation failed: {exc}", icon=":material/error:")
        st.stop()
    model_answer = None
    if use_model:
        with st.spinner(f"Asking {cfg.ollama_model} to explain the evidence..."):
            model_answer = synthesize(build_prompt(question, change, bundle.metrics, bundle.text), cfg)
    st.session_state.result = (question, bundle, change, model_answer)

question, bundle, change, model_answer = st.session_state.result

with st.container(border=True):
    st.subheader("Answer")
    st.markdown(f"**{change.summary}**")
    st.badge(
        "Live Snowflake evidence" if bundle.mode == "live" else "Fixture evidence",
        icon=":material/cloud:" if bundle.mode == "live" else ":material/inventory_2:",
        color="green" if bundle.mode == "live" else "blue",
    )
    with st.container(horizontal=True):
        st.metric(f"FY{change.old.fiscal_year} revenue", format_usd_billions(change.old.value))
        st.metric(
            f"FY{change.new.fiscal_year} revenue",
            format_usd_billions(change.new.value),
            delta=f"{format_usd_billions(change.absolute_change)} ({change.percent_change:.2f}%)",
        )
    st.caption(
        f"Deterministic calculation: {change.new.value:,} − {change.old.value:,} = {change.absolute_change:,} USD; "
        f"{change.absolute_change:,} / {change.old.value:,} × 100 = {change.percent_change:.4f}%"
    )

with st.container(border=True):
    st.subheader(":material/smart_toy: Model explanation")
    if model_answer is None:
        st.caption("Local model disabled. The deterministic answer above stands on its own.")
    elif model_answer.ok:
        st.markdown(md(model_answer.answer))
        st.markdown(f"**Calculation:** {md(model_answer.calculation)}")
        st.markdown(f"**Narrative evidence:** {md(model_answer.narrative_evidence)}")
        if model_answer.citations:
            st.markdown("**Cited:** " + ", ".join(f"`{c}`" for c in model_answer.citations))
        st.caption(f"{model_answer.model} · {model_answer.latency_s}s · explanation only, not the source of truth")
    else:
        st.warning(
            f"Model explanation unavailable ({model_answer.error}). Showing the deterministic result only.",
            icon=":material/warning:",
        )

st.subheader("Metric evidence")
df = pd.DataFrame(
    [
        {
            "Fiscal year": f"FY{m.fiscal_year}",
            "Revenue (USD)": m.value,
            "Revenue": format_usd_billions(m.value),
            "Period": f"{m.period_start} → {m.period_end}",
            "Source accession": m.adsh,
            "Filed": m.filed_date,
            "Variable": m.variable_name,
        }
        for m in bundle.metrics
    ]
)
st.dataframe(df, hide_index=True, column_config={"Revenue (USD)": st.column_config.NumberColumn(format="%d")})
st.bar_chart(df, x="Fiscal year", y="Revenue (USD)", height=250)

text = bundle.text
with st.expander(":material/description: Narrative evidence (MD&A excerpt)", expanded=True):
    st.markdown(f"**{text.form_type}** · accession `{text.adsh}` · filed {text.filed_date} · {text.item_number} — {text.item_title}")
    st.text(text.text)

with st.expander(":material/verified: Provenance and limitations"):
    st.markdown(
        f"- Narrative: `{text.adsh}` ({text.form_type}, filed {text.filed_date}, {text.item_number})\n"
        + "\n".join(
            f"- FY{m.fiscal_year} metric: `{m.adsh}` (filed {m.filed_date}), period {m.period_start} → {m.period_end}"
            for m in bundle.metrics
        )
    )
    st.markdown("**Limitations**\n" + "\n".join(f"- {l}" for l in LIMITATIONS))
    if model_answer is not None and model_answer.ok and model_answer.limitations:
        st.markdown("**Model-noted limitations**\n" + "\n".join(f"- {md(l)}" for l in model_answer.limitations))
    st.caption("FilingForensics does not provide investment, legal, or compliance advice.")

with st.expander(":material/bug_report: Debug"):
    st.json(
        {
            "mode": bundle.mode,
            "row_counts": bundle.row_counts,
            "sql": bundle.sql or "none (fixture mode)",
            "model": cfg.ollama_model,
            "ollama_host": cfg.ollama_host,
            "model_latency_s": getattr(model_answer, "latency_s", None),
            "model_ok": getattr(model_answer, "ok", None),
            "model_error": getattr(model_answer, "error", None),
        }
    )
    if model_answer is not None and model_answer.raw:
        st.code(model_answer.raw, language="json")
