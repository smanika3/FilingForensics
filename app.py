"""FilingForensics Streamlit entry point (placeholder until Stage 3)."""
import streamlit as st

from src.config import get_config

cfg = get_config()
st.title("FilingForensics")
st.caption(f"Mode: {cfg.mode} | Model: {cfg.ollama_model}")
st.info("Scaffold only. Evidence pipeline arrives in Stages 1-3.")
