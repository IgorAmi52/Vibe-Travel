from __future__ import annotations

import asyncio
import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from core.app import TripPlannerApp, create_app
from core.clients import SkyscannerFlightClient
from core.flights import FlightChainService, FlightSearchParams
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
        if route == "/flights/indicative":
            try:
                payload = self._read_json_body()
                self._send_json(200, handle_flight_indicative_request(self.server.app, payload))
            except KeyError as exc:
                self._send_json(400, {"error": f"Missing required field: {exc.args[0]}"})
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if route == "/flights/chains":
            try:
                payload = self._read_json_body()
                self._send_json(200, handle_flight_chain_request(self.server.app, payload))
            except KeyError as exc:
                self._send_json(400, {"error": f"Missing required field: {exc.args[0]}"})
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

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


_VALID_REQUEST_TYPES = ("NEW", "CLARIFICATION")


def handle_flight_indicative_request(app: TripPlannerApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    origin_iata = str(payload["origin_iata"]).strip()
    outbound_date = payload.get("outbound_date")
    if outbound_date is not None:
        outbound_date = str(outbound_date).strip()
        try:
            date.fromisoformat(outbound_date)
        except ValueError as exc:
            raise ValueError("outbound_date must be ISO format YYYY-MM-DD") from exc

    client = SkyscannerFlightClient(
        base_url=app.config.skyscanner_base_url,
        api_key=app.config.skyscanner_api_key,
        api_host=app.config.skyscanner_api_host,
        timeout=app.config.skyscanner_timeout_seconds,
        max_retries=app.config.skyscanner_max_retries,
        retry_delay=app.config.skyscanner_retry_delay_seconds,
    )

    result = asyncio.run(
        _run_indicative_request(
            client=client,
            origin_iata=origin_iata,
            outbound_date=outbound_date,
            market=str(payload.get("market", "UK")),
            locale=str(payload.get("locale", "en-GB")),
            currency=str(payload.get("currency", "EUR")),
        )
    )

    return result


def handle_flight_chain_request(app: TripPlannerApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    origin_iata = str(payload["origin_iata"]).strip()
    destination_iata = str(payload["destination_iata"]).strip()

    try:
        departure_date = date.fromisoformat(str(payload["departure_date"]).strip())
        return_date = date.fromisoformat(str(payload["return_date"]).strip())
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid or missing date: {exc}") from exc

    if return_date < departure_date:
        raise ValueError("return_date must be on or after departure_date")

    limit = int(payload.get("limit", 10))
    if limit > 50:
        raise ValueError("limit must not exceed 50")

    params = FlightSearchParams(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        departure_date=departure_date,
        return_date=return_date,
        market=str(payload.get("market", "UK")),
        locale=str(payload.get("locale", "en-GB")),
        currency=str(payload.get("currency", "EUR")),
        adults=int(payload.get("adults", 1)),
        children_ages=tuple(payload.get("children_ages") or []),
        cabin_class=str(payload.get("cabin_class", "CABIN_CLASS_ECONOMY")),
        direct_only=bool(payload.get("direct_only", False)),
    )

    client = SkyscannerFlightClient(
        base_url=app.config.skyscanner_base_url,
        api_key=app.config.skyscanner_api_key,
        api_host=app.config.skyscanner_api_host,
        timeout=app.config.skyscanner_timeout_seconds,
        max_retries=app.config.skyscanner_max_retries,
        retry_delay=app.config.skyscanner_retry_delay_seconds,
    )
    service = FlightChainService(provider=client)

    results = asyncio.run(_run_flight_chain_request(service=service, client=client, params=params, limit=limit))

    return {
        "results": [
            {
                "itinerary_id": chain.itinerary_id,
                "price_amount": chain.price_amount,
                "price_currency": chain.price_currency,
                "agent_name": chain.agent_name,
                "deep_link": chain.deep_link,
            }
            for chain in results
        ],
        "count": len(results),
    }


def handle_invoke_request(app: TripPlannerApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    request_type = str(payload.get("type", "NEW")).upper()
    if request_type not in _VALID_REQUEST_TYPES:
        raise ValueError(f"type must be one of {_VALID_REQUEST_TYPES}")

    user_query = str(payload["user_query"]).strip()
    if not user_query:
        raise ValueError("user_query must be a non-empty string")

    runtime_state = dict(payload.get("state") or {}) if request_type == "CLARIFICATION" else {}
    _merge_request_state(runtime_state, payload)

    state = app.run(
        user_query=user_query,
        mode=payload.get("mode"),
        source=str(payload.get("source", "network")),
        state=runtime_state or None,
        mock_response=payload.get("mock_response"),
    )
    response: Dict[str, Any] = {"state": state}
    if state.get("needs_clarification"):
        response["needs_clarification"] = True
        response["clarification_prompt"] = state.get("clarification_prompt")
    return response


async def _run_indicative_request(
    *,
    client: SkyscannerFlightClient,
    origin_iata: str,
    outbound_date: Optional[str],
    market: str,
    locale: str,
    currency: str,
) -> Dict[str, Any]:
    try:
        return await client.search_indicative_anywhere(
            origin_iata=origin_iata,
            outbound_date=outbound_date,
            market=market,
            locale=locale,
            currency=currency,
        )
    finally:
        await client.close()


async def _run_flight_chain_request(
    *,
    service: FlightChainService,
    client: SkyscannerFlightClient,
    params: FlightSearchParams,
    limit: int,
):
    try:
        return await service.get_roundtrip_chains(params, limit=limit)
    finally:
        await client.close()


def _merge_request_state(state: Dict[str, Any], payload: Dict[str, Any]) -> None:
    for field_name in ("origin_iata", "destination_iata"):
        if payload.get(field_name):
            state[field_name] = str(payload[field_name]).strip()

    explicit_trip_intent = dict(state.get("trip_intent") or {})
    if isinstance(payload.get("trip_intent"), dict):
        explicit_trip_intent.update(payload["trip_intent"])

    for field_name in ("places", "countries", "start_date", "end_date", "budget", "vibe"):
        if payload.get(field_name) is not None:
            explicit_trip_intent[field_name] = payload[field_name]

    if explicit_trip_intent:
        state["trip_intent"] = explicit_trip_intent
