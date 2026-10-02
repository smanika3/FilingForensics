"""Environment configuration with safe defaults. Fixture mode needs no variables."""
import os
from dataclasses import dataclass


from pathlib import Path


def _load_env() -> None:
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val


_load_env()


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

