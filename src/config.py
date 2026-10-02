"""Environment configuration with safe defaults. Fixture mode needs no variables."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    mode: str = os.getenv("FF_MODE", "fixture")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3.5:2b")
    ollama_timeout: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30"))
    snowflake_database: str = os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_PUBLIC_DATA_FREE")
    snowflake_schema: str = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC_DATA_FREE")


def get_config() -> Config:
    return Config()
