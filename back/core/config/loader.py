from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_ENV_PATH = ROOT_DIR / ".env"
DEFAULT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "intent_extraction.md"


@dataclass(frozen=True)
class AppConfig:
    prompt_path: Path = DEFAULT_PROMPT_PATH
    default_mode: str = "mock"
    api_host: str = "127.0.0.1"
    api_port: int = 8080
    gemini_model: str = "gemini-2.5-flash-lite"


def load_app_config() -> AppConfig:
    load_env_file()
    prompt_path = Path(os.getenv("TRIP_PLANNER_PROMPT_PATH", str(DEFAULT_PROMPT_PATH)))
    default_mode = os.getenv("TRIP_PLANNER_MODE", "mock").strip().lower() or "mock"
    api_host = os.getenv("TRIP_PLANNER_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    api_port = _parse_port(os.getenv("TRIP_PLANNER_API_PORT"), 8080)
    gemini_model = os.getenv("TRIP_PLANNER_GEMINI_MODEL", "gemini-2.5-flash-lite").strip()

    return AppConfig(
        prompt_path=prompt_path,
        default_mode=default_mode,
        api_host=api_host,
        api_port=api_port,
        gemini_model=gemini_model or "gemini-2.5-flash-lite",
    )


def load_markdown_prompt(prompt_path: Optional[Path] = None) -> str:
    return (prompt_path or DEFAULT_PROMPT_PATH).read_text(encoding="utf-8").strip()


def load_env_file(env_path: Optional[Path] = None) -> None:
    path = env_path or DEFAULT_ENV_PATH
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_quotes(value.strip())
        if key and key not in os.environ:
            os.environ[key] = value


def _parse_port(raw_value: Optional[str], default: int) -> int:
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
