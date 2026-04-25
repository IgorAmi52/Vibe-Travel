from __future__ import annotations

import asyncio
import json
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


def handle_flight_chain_request(app: TripPlannerApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    origin_iata = _required_non_empty_string(payload, "origin_iata")
    destination_iata = _required_non_empty_string(payload, "destination_iata")
    departure_date = _required_date(payload, "departure_date")
    return_date = _required_date(payload, "return_date")
    if return_date < departure_date:
        raise ValueError("return_date must be on or after departure_date")
    market = str(payload.get("market", "UK"))
    locale = str(payload.get("locale", "en-GB"))
    currency = str(payload.get("currency", "EUR"))
    adults = _int_field(payload, "adults", 1, min_value=1)
    children_ages = tuple(_int_item(age, "children_ages") for age in payload.get("children_ages", []))
    cabin_class = str(payload.get("cabin_class", "CABIN_CLASS_ECONOMY"))
    direct_only = _bool_field(payload, "direct_only", False)
    limit = _int_field(payload, "limit", 10, min_value=1, max_value=50)

    if not app.config.skyscanner_api_key:
        raise ValueError("SKYSCANNER_API_KEY is required for /flights/chains")

    params = FlightSearchParams(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        departure_date=departure_date,
        return_date=return_date,
        market=market,
        locale=locale,
        currency=currency,
        adults=adults,
        children_ages=children_ages,
        cabin_class=cabin_class,
        direct_only=direct_only,
    )

    async def _run() -> Dict[str, Any]:
        client = SkyscannerFlightClient(
            base_url=app.config.skyscanner_base_url,
            api_key=app.config.skyscanner_api_key,
            api_host=app.config.skyscanner_api_host,
            timeout=app.config.skyscanner_timeout_seconds,
            max_retries=app.config.skyscanner_max_retries,
            retry_delay=app.config.skyscanner_retry_delay_seconds,
        )
        try:
            service = FlightChainService(provider=client)
            results = await service.get_roundtrip_chains(params, limit=limit)
            return {"results": [_result_to_dict(item) for item in results]}
        finally:
            await client.close()

    return asyncio.run(_run())


def handle_flight_indicative_request(app: TripPlannerApp, payload: Dict[str, Any]) -> Dict[str, Any]:
    origin_iata = _required_non_empty_string(payload, "origin_iata").upper()
    outbound_date = _required_non_empty_string(payload, "outbound_date")
    _required_date(payload, "outbound_date")
    market = str(payload.get("market", "UK"))
    locale = str(payload.get("locale", "en-GB"))
    currency = str(payload.get("currency", "EUR"))

    if not app.config.skyscanner_api_key:
        raise ValueError("SKYSCANNER_API_KEY is required for /flights/indicative")

    async def _run() -> Dict[str, Any]:
        client = SkyscannerFlightClient(
            base_url=app.config.skyscanner_base_url,
            api_key=app.config.skyscanner_api_key,
            api_host=app.config.skyscanner_api_host,
            timeout=app.config.skyscanner_timeout_seconds,
            max_retries=app.config.skyscanner_max_retries,
            retry_delay=app.config.skyscanner_retry_delay_seconds,
        )
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

    return asyncio.run(_run())


def _result_to_dict(result: Any) -> Dict[str, Any]:
    return {
        "itinerary_id": result.itinerary_id,
        "price_amount": result.price_amount,
        "price_currency": result.price_currency,
        "agent_name": result.agent_name,
        "deep_link": result.deep_link,
        "validating_carriers": list(result.validating_carriers),
        "outbound_chain": _leg_to_dict(result.outbound_chain),
        "inbound_chain": _leg_to_dict(result.inbound_chain),
    }


def _leg_to_dict(leg: Any) -> Dict[str, Any]:
    return {
        "leg_id": leg.leg_id,
        "origin_iata": leg.origin_iata,
        "destination_iata": leg.destination_iata,
        "departure_at": leg.departure_at,
        "arrival_at": leg.arrival_at,
        "duration_minutes": leg.duration_minutes,
        "stop_count": leg.stop_count,
        "segments": [_segment_to_dict(segment) for segment in leg.segments],
    }


def _segment_to_dict(segment: Any) -> Dict[str, Any]:
    return {
        "segment_id": segment.segment_id,
        "origin_iata": segment.origin_iata,
        "destination_iata": segment.destination_iata,
        "departure_at": segment.departure_at,
        "arrival_at": segment.arrival_at,
        "marketing_carrier": segment.marketing_carrier,
        "operating_carrier": segment.operating_carrier,
        "flight_number": segment.flight_number,
        "duration_minutes": segment.duration_minutes,
        "aircraft_code": segment.aircraft_code,
    }


def _required_non_empty_string(payload: Dict[str, Any], key: str) -> str:
    value = str(payload[key]).strip()
    if not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_date(payload: Dict[str, Any], key: str):
    from datetime import date

    value = _required_non_empty_string(payload, key)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be ISO format YYYY-MM-DD") from exc


def _bool_field(payload: Dict[str, Any], key: str, default: bool) -> bool:
    raw = payload.get(key, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"true", "1", "yes"}:
            return True
        if value in {"false", "0", "no"}:
            return False
    raise ValueError(f"{key} must be a boolean")


def _int_item(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain integers") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} values must be >= 0")
    return parsed


def _int_field(
    payload: Dict[str, Any],
    key: str,
    default: int,
    *,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    raw = payload.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer") from exc
    if min_value is not None and value < min_value:
        raise ValueError(f"{key} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{key} must be <= {max_value}")
    return value
