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
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-001"
    booking_base_url: str = "https://booking-com15.p.rapidapi.com"
    booking_api_key: str = ""
    booking_api_host: str = "booking-com15.p.rapidapi.com"
    booking_timeout_seconds: float = 30.0
    booking_max_retries: int = 3
    booking_retry_delay_seconds: float = 1.0
    hotel_currency: str = "USD"
    hotel_vibe_weight: float = 0.7
    hotel_price_weight: float = 0.2
    hotel_rating_weight: float = 0.1
    skyscanner_base_url: str = "https://partners.api.skyscanner.net"
    skyscanner_api_key: str = ""
    skyscanner_api_host: str = ""
    skyscanner_timeout_seconds: float = 30.0
    skyscanner_max_retries: int = 3
    skyscanner_retry_delay_seconds: float = 1.0


def load_app_config() -> AppConfig:
    load_env_file()
    prompt_path = Path(os.getenv("TRIP_PLANNER_PROMPT_PATH", str(DEFAULT_PROMPT_PATH)))
    default_mode = os.getenv("TRIP_PLANNER_MODE", "mock").strip().lower() or "mock"
    api_host = os.getenv("TRIP_PLANNER_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    api_port = _parse_port(os.getenv("TRIP_PLANNER_API_PORT"), 8080)
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("TRIP_PLANNER_GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
    gemini_embedding_model = os.getenv("TRIP_PLANNER_GEMINI_EMBEDDING_MODEL", "gemini-embedding-001").strip()
    booking_base_url = os.getenv("BOOKING_BASE_URL", "https://booking-com15.p.rapidapi.com").strip()
    booking_api_key = os.getenv("BOOKING_RAPIDAPI_KEY", "").strip()
    booking_api_host = os.getenv("BOOKING_API_HOST", "booking-com15.p.rapidapi.com").strip()
    booking_timeout_seconds = _parse_float(os.getenv("BOOKING_TIMEOUT_SECONDS"), 30.0)
    booking_max_retries = max(1, _parse_port(os.getenv("BOOKING_MAX_RETRIES"), 3))
    booking_retry_delay_seconds = _parse_float(os.getenv("BOOKING_RETRY_DELAY_SECONDS"), 1.0)
    hotel_currency = os.getenv("TRIP_PLANNER_HOTEL_CURRENCY", "USD").strip() or "USD"
    hotel_vibe_weight = _parse_float(os.getenv("TRIP_PLANNER_HOTEL_VIBE_WEIGHT"), 0.7)
    hotel_price_weight = _parse_float(os.getenv("TRIP_PLANNER_HOTEL_PRICE_WEIGHT"), 0.2)
    hotel_rating_weight = _parse_float(os.getenv("TRIP_PLANNER_HOTEL_RATING_WEIGHT"), 0.1)
    skyscanner_base_url = os.getenv("SKYSCANNER_BASE_URL", "https://partners.api.skyscanner.net").strip()
    skyscanner_api_key = os.getenv("SKYSCANNER_API_KEY", "").strip()
    skyscanner_api_host = os.getenv("SKYSCANNER_API_HOST", "").strip()
    skyscanner_timeout_seconds = _parse_float(os.getenv("SKYSCANNER_TIMEOUT_SECONDS"), 30.0)
    skyscanner_max_retries = max(1, _parse_port(os.getenv("SKYSCANNER_MAX_RETRIES"), 3))
    skyscanner_retry_delay_seconds = _parse_float(os.getenv("SKYSCANNER_RETRY_DELAY_SECONDS"), 1.0)

    return AppConfig(
        prompt_path=prompt_path,
        default_mode=default_mode,
        api_host=api_host,
        api_port=api_port,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model or "gemini-2.5-flash-lite",
        gemini_embedding_model=gemini_embedding_model or "gemini-embedding-001",
        booking_base_url=booking_base_url or "https://booking-com15.p.rapidapi.com",
        booking_api_key=booking_api_key,
        booking_api_host=booking_api_host or "booking-com15.p.rapidapi.com",
        booking_timeout_seconds=booking_timeout_seconds,
        booking_max_retries=booking_max_retries,
        booking_retry_delay_seconds=booking_retry_delay_seconds,
        hotel_currency=hotel_currency,
        hotel_vibe_weight=hotel_vibe_weight,
        hotel_price_weight=hotel_price_weight,
        hotel_rating_weight=hotel_rating_weight,
        skyscanner_base_url=skyscanner_base_url or "https://partners.api.skyscanner.net",
        skyscanner_api_key=skyscanner_api_key,
        skyscanner_api_host=skyscanner_api_host,
        skyscanner_timeout_seconds=skyscanner_timeout_seconds,
        skyscanner_max_retries=skyscanner_max_retries,
        skyscanner_retry_delay_seconds=skyscanner_retry_delay_seconds,
    )


def load_markdown_prompt(prompt_path: Optional[Path] = None) -> str:
    from datetime import date
    today = date.today()
    raw = (prompt_path or DEFAULT_PROMPT_PATH).read_text(encoding="utf-8").strip()
    return raw.replace("{{TODAY}}", today.isoformat()).replace("{{YEAR}}", str(today.year))


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


def _parse_float(raw_value: Optional[str], default: float) -> float:
    if not raw_value:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
