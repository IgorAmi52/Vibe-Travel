from __future__ import annotations

import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from core.api import serve_http
from core.app import create_app
from core.config import load_app_config


def main() -> None:
    _configure_logging()

    parser = argparse.ArgumentParser(description="Trip planner runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    invoke_parser = subparsers.add_parser("invoke", help="Run one graph invocation")
    invoke_parser.add_argument("--query", required=True, help="User travel query")
    invoke_parser.add_argument("--mode", choices=["mock", "gemini"], help="Inference backend")
    invoke_parser.add_argument("--source", default="cli", help="Source label for the request")
    invoke_parser.add_argument("--mock-file", help="Path to JSON file with an IntentStruct payload")

    serve_parser = subparsers.add_parser("serve", help="Start the HTTP API")
    serve_parser.add_argument("--host", help="Bind host")
    serve_parser.add_argument("--port", type=int, help="Bind port")

    args = parser.parse_args()
    config = load_app_config()
    app = create_app(config)

    if args.command == "invoke":
        result = app.run(
            user_query=args.query,
            mode=args.mode,
            source=args.source,
            mock_response=_load_mock_file(args.mock_file),
        )
        print(json.dumps(result, indent=2))
        return

    host = args.host or config.api_host
    port = args.port or config.api_port
    serve_http(app=app, host=host, port=port)


def _load_mock_file(mock_file: Optional[str]) -> Optional[Dict[str, Any]]:
    if not mock_file:
        return None
    return json.loads(Path(mock_file).read_text(encoding="utf-8"))


def _configure_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "trip_planner.log"

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[console_handler, file_handler],
        force=True,
    )


if __name__ == "__main__":
    main()
