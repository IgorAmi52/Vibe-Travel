from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from core.app import TripPlannerApp, create_app
from core.state import IntentStruct


class TripPlannerHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, app: TripPlannerApp) -> None:
        self.app = app
        super().__init__(server_address, handler_class)


class TripPlannerApiHandler(BaseHTTPRequestHandler):
    server: TripPlannerHTTPServer

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "default_mode": self.server.app.config.default_mode,
                },
            )
            return
        if route == "/schema":
            self._send_json(200, IntentStruct.json_schema())
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route != "/invoke":
            self._send_json(404, {"error": "Not found"})
            return

        try:
            payload = self._read_json_body()
            self._send_json(200, handle_invoke_request(self.server.app, payload))
        except KeyError:
            self._send_json(400, {"error": "Missing required field: user_query"})
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        del format, args

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Body must be valid JSON") from exc

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def create_http_server(
    app: Optional[TripPlannerApp] = None,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> TripPlannerHTTPServer:
    return TripPlannerHTTPServer((host, port), TripPlannerApiHandler, app or create_app())


def serve_http(
    app: Optional[TripPlannerApp] = None,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> None:
    server = create_http_server(app=app, host=host, port=port)
    server.serve_forever()


def handle_invoke_request(app: TripPlannerApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    user_query = str(payload["user_query"]).strip()
    if not user_query:
        raise ValueError("user_query must be a non-empty string")

    state = app.run(
        user_query=user_query,
        mode=payload.get("mode"),
        source=str(payload.get("source", "network")),
        state=payload.get("state"),
        mock_response=payload.get("mock_response"),
    )
    return {"state": state}
