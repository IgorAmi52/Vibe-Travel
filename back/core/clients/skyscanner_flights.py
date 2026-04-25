from __future__ import annotations

import asyncio
from typing import Any

from clients.api_connector import ApiConnector
from core.flights import (
    FlightLegChain,
    FlightSearchParams,
    FlightSegment,
    LivePricesPollResult,
    LivePricesSession,
    RoundTripChainResult,
)


class SkyscannerFlightClient:
    CREATE_SESSION_PATHS = (
        "/api/v1/flights/live/search/create",
        "/v1/flights/live/search/create",
        "/v3/flights/live/search/create",
    )
    POLL_SESSION_PATHS = (
        "/api/v1/flights/live/search/poll",
        "/v1/flights/live/search/poll",
        "/v3/flights/live/search/poll",
    )
    INDICATIVE_SEARCH_PATHS = (
        "/api/v1/flights/indicative/search",
        "/v1/flights/indicative/search",
        "/apiservices/v3/flights/indicative/search",
        "/v3/flights/indicative/search",
    )

    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_host: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        connector: ApiConnector | None = None,
    ) -> None:
        self._connector = connector or ApiConnector(
            base_url=base_url,
            headers={
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": api_host,
                "content-type": "application/json",
            },
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

    async def create_live_prices_session(self, params: FlightSearchParams) -> LivePricesSession:
        payload = await self._post_with_path_fallback(
            self.CREATE_SESSION_PATHS,
            json=self._build_live_prices_payload(params),
        )

        session_token = (
            payload.get("sessionToken")
            or payload.get("sessionId")
            or payload.get("data", {}).get("sessionToken")
            or payload.get("context", {}).get("sessionToken")
        )
        if not session_token:
            raise ValueError("Skyscanner Live Prices create response missing session token")

        polling_url = (
            payload.get("pollingUrl")
            or payload.get("context", {}).get("pollingUrl")
            or payload.get("data", {}).get("pollingUrl")
        )
        return LivePricesSession(
            session_token=str(session_token),
            polling_url=str(polling_url) if polling_url else None,
            raw_payload=payload,
        )

    async def poll_live_prices_session(self, session: LivePricesSession) -> LivePricesPollResult:
        payload = await self._post_with_path_fallback(
            self.POLL_SESSION_PATHS,
            json={"sessionToken": session.session_token},
        )
        return self._parse_poll_payload(payload)

    async def search_roundtrip_chains(
        self,
        params: FlightSearchParams,
        *,
        max_polls: int = 6,
        poll_interval_seconds: float = 1.0,
    ) -> LivePricesPollResult:
        session = await self.create_live_prices_session(params)
        latest_result: LivePricesPollResult | None = None

        for attempt in range(max_polls):
            latest_result = await self.poll_live_prices_session(session)
            if latest_result.completed:
                return latest_result
            if attempt < max_polls - 1:
                await asyncio.sleep(poll_interval_seconds)

        if latest_result is None:
            raise RuntimeError("Skyscanner Live Prices polling returned no response")
        return latest_result

    async def close(self) -> None:
        await self._connector.close()

    async def search_indicative_anywhere(
        self,
        *,
        origin_iata: str,
        outbound_date: str,
        market: str = "UK",
        locale: str = "en-GB",
        currency: str = "EUR",
    ) -> dict[str, Any]:
        payload = await self._post_with_path_fallback(
            self.INDICATIVE_SEARCH_PATHS,
            json=self._build_indicative_anywhere_payload(
                origin_iata=origin_iata,
                outbound_date=outbound_date,
                market=market,
                locale=locale,
                currency=currency,
            ),
        )
        return self._parse_indicative_payload(payload)

    async def _post_with_path_fallback(self, paths: tuple[str, ...], **kwargs: Any) -> dict[str, Any]:
        from httpx import HTTPStatusError

        last_error: Exception | None = None
        for path in paths:
            try:
                response = await self._connector.post(path, **kwargs)
                return response.json()
            except HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 404:
                    continue
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("Skyscanner request failed without response")

    @staticmethod
    def _build_live_prices_payload(params: FlightSearchParams) -> dict[str, Any]:
        return {
            "query": {
                "market": params.market,
                "locale": params.locale,
                "currency": params.currency,
                "adults": params.adults,
                "childrenAges": list(params.children_ages),
                "cabinClass": params.cabin_class,
                "queryLegs": [
                    {
                        "originPlaceId": {"iata": params.origin_iata},
                        "destinationPlaceId": {"iata": params.destination_iata},
                        "date": params.departure_date.isoformat(),
                    },
                    {
                        "originPlaceId": {"iata": params.destination_iata},
                        "destinationPlaceId": {"iata": params.origin_iata},
                        "date": params.return_date.isoformat(),
                    },
                ],
                "includeSustainabilityData": False,
                "nonStop": params.direct_only,
            }
        }

    @staticmethod
    def _build_indicative_anywhere_payload(
        *,
        origin_iata: str,
        outbound_date: str,
        market: str,
        locale: str,
        currency: str,
    ) -> dict[str, Any]:
        year, month, day = (int(part) for part in outbound_date.split("-", 2))
        return {
            "query": {
                "market": market,
                "locale": locale,
                "currency": currency,
                "queryLegs": [
                    {
                        "originPlace": {"queryPlace": {"iata": origin_iata}},
                        "destinationPlace": {"anywhere": True},
                        "fixedDate": {"year": year, "month": month, "day": day},
                    }
                ],
            }
        }

    @staticmethod
    def _parse_indicative_payload(payload: dict[str, Any]) -> dict[str, Any]:
        content = payload.get("content", {})
        results = content.get("results", {})
        quotes = results.get("quotes", {})
        places = results.get("places", {})
        carriers = results.get("carriers", {})

        mapped_quotes: list[dict[str, Any]] = []
        for quote_id, quote in quotes.items():
            if not isinstance(quote, dict):
                continue
            outbound_leg = quote.get("outboundLeg", {}) if isinstance(quote.get("outboundLeg"), dict) else {}
            inbound_leg = quote.get("inboundLeg", {}) if isinstance(quote.get("inboundLeg"), dict) else {}
            origin_place_id = outbound_leg.get("originPlaceId")
            destination_place_id = outbound_leg.get("destinationPlaceId")
            carrier_id = outbound_leg.get("marketingCarrierId")
            min_price = quote.get("minPrice", {}) if isinstance(quote.get("minPrice"), dict) else {}

            mapped_quotes.append(
                {
                    "quote_id": str(quote_id),
                    "price_amount": SkyscannerFlightClient._float_or_none(min_price.get("amount")),
                    "price_unit": SkyscannerFlightClient._string_or_none(min_price.get("unit")),
                    "is_direct": bool(quote.get("isDirect")),
                    "origin": SkyscannerFlightClient._place_from_index(origin_place_id, places),
                    "destination": SkyscannerFlightClient._place_from_index(destination_place_id, places),
                    "carrier": SkyscannerFlightClient._carrier_from_index(carrier_id, carriers),
                    "outbound_departure": SkyscannerFlightClient._datetime_to_iso(outbound_leg.get("departureDateTime")),
                    "inbound_departure": SkyscannerFlightClient._datetime_to_iso(inbound_leg.get("departureDateTime")),
                    "raw_payload": quote,
                }
            )

        return {
            "status": str(payload.get("status", "RESULT_STATUS_UNSPECIFIED")),
            "quotes": mapped_quotes,
            "raw_payload": payload,
        }

    def _parse_poll_payload(self, payload: dict[str, Any]) -> LivePricesPollResult:
        status = str(payload.get("status") or payload.get("action") or "UNKNOWN")
        completed = bool(
            payload.get("completed")
            or status.upper() in {"RESULT_STATUS_COMPLETE", "COMPLETED", "COMPLETE"}
            or payload.get("itineraries")
            or payload.get("data", {}).get("itineraries")
        )
        itinerary_nodes = payload.get("itineraries") or payload.get("data", {}).get("itineraries") or []
        legs_index = payload.get("legs") or payload.get("data", {}).get("legs") or {}
        segments_index = payload.get("segments") or payload.get("data", {}).get("segments") or {}
        pricing_index = payload.get("pricingOptions") or payload.get("data", {}).get("pricingOptions") or {}
        agents_index = payload.get("agents") or payload.get("data", {}).get("agents") or {}

        results: list[RoundTripChainResult] = []
        for itinerary in itinerary_nodes:
            mapped = self._map_itinerary(
                itinerary=itinerary,
                legs_index=legs_index,
                segments_index=segments_index,
                pricing_index=pricing_index,
                agents_index=agents_index,
            )
            if mapped is not None:
                results.append(mapped)

        return LivePricesPollResult(status=status, completed=completed, results=tuple(results), raw_payload=payload)

    def _map_itinerary(
        self,
        *,
        itinerary: dict[str, Any],
        legs_index: dict[str, Any],
        segments_index: dict[str, Any],
        pricing_index: dict[str, Any],
        agents_index: dict[str, Any],
    ) -> RoundTripChainResult | None:
        itinerary_id = self._string_or_none(itinerary.get("id") or itinerary.get("itineraryId"))
        if not itinerary_id:
            return None

        leg_ids = itinerary.get("legIds") or itinerary.get("legs") or []
        if len(leg_ids) < 2:
            return None

        outbound_leg = self._resolve_node(leg_ids[0], legs_index)
        inbound_leg = self._resolve_node(leg_ids[1], legs_index)
        if outbound_leg is None or inbound_leg is None:
            return None

        outbound_chain = self._build_leg_chain(outbound_leg, segments_index)
        inbound_chain = self._build_leg_chain(inbound_leg, segments_index)
        if outbound_chain is None or inbound_chain is None:
            return None

        price_amount, price_currency, agent_name, deep_link = self._extract_price(
            itinerary=itinerary,
            pricing_index=pricing_index,
            agents_index=agents_index,
        )
        validating_carriers = tuple(
            carrier
            for carrier in (
                self._string_or_none(item) for item in itinerary.get("validatingCarrierIds", [])
            )
            if carrier
        )

        return RoundTripChainResult(
            itinerary_id=itinerary_id,
            outbound_chain=outbound_chain,
            inbound_chain=inbound_chain,
            price_amount=price_amount,
            price_currency=price_currency,
            agent_name=agent_name,
            deep_link=deep_link,
            validating_carriers=validating_carriers,
            raw_payload=itinerary,
        )

    def _build_leg_chain(self, leg: dict[str, Any], segments_index: dict[str, Any]) -> FlightLegChain | None:
        leg_id = self._string_or_none(leg.get("id") or leg.get("legId"))
        origin = self._string_or_none(leg.get("originIata") or leg.get("origin"))
        destination = self._string_or_none(leg.get("destinationIata") or leg.get("destination"))
        departure = self._string_or_none(leg.get("departure") or leg.get("departureDateTime"))
        arrival = self._string_or_none(leg.get("arrival") or leg.get("arrivalDateTime"))
        if not all([leg_id, origin, destination, departure, arrival]):
            return None

        segment_ids = leg.get("segmentIds") or leg.get("segments") or []
        segments: list[FlightSegment] = []
        for segment_ref in segment_ids:
            segment_node = self._resolve_node(segment_ref, segments_index)
            if segment_node is None:
                continue
            segment = self._build_segment(segment_node)
            if segment is not None:
                segments.append(segment)
        if not segments:
            return None

        return FlightLegChain(
            leg_id=leg_id,
            origin_iata=origin,
            destination_iata=destination,
            departure_at=departure,
            arrival_at=arrival,
            duration_minutes=self._int_or_none(leg.get("durationInMinutes") or leg.get("duration")),
            stop_count=max(0, len(segments) - 1),
            segments=tuple(segments),
            raw_payload=leg,
        )

    def _build_segment(self, segment: dict[str, Any]) -> FlightSegment | None:
        origin = self._string_or_none(segment.get("originIata") or segment.get("origin"))
        destination = self._string_or_none(segment.get("destinationIata") or segment.get("destination"))
        departure = self._string_or_none(segment.get("departure") or segment.get("departureDateTime"))
        arrival = self._string_or_none(segment.get("arrival") or segment.get("arrivalDateTime"))
        if not all([origin, destination, departure, arrival]):
            return None

        return FlightSegment(
            segment_id=self._string_or_none(segment.get("id") or segment.get("segmentId")),
            origin_iata=origin,
            destination_iata=destination,
            departure_at=departure,
            arrival_at=arrival,
            marketing_carrier=self._string_or_none(segment.get("marketingCarrier") or segment.get("marketingCarrierId")),
            operating_carrier=self._string_or_none(segment.get("operatingCarrier") or segment.get("operatingCarrierId")),
            flight_number=self._string_or_none(segment.get("flightNumber")),
            duration_minutes=self._int_or_none(segment.get("durationInMinutes") or segment.get("duration")),
            aircraft_code=self._string_or_none(segment.get("aircraftCode") or segment.get("aircraft")),
            raw_payload=segment,
        )

    @staticmethod
    def _extract_price(
        *,
        itinerary: dict[str, Any],
        pricing_index: dict[str, Any],
        agents_index: dict[str, Any],
    ) -> tuple[float | None, str | None, str | None, str | None]:
        options = itinerary.get("pricingOptions") or itinerary.get("pricingOptionIds") or []
        if not options:
            return None, None, None, None

        option = options[0]
        if isinstance(option, str):
            option = pricing_index.get(option, {})
        if not isinstance(option, dict):
            return None, None, None, None

        if isinstance(option.get("price"), dict):
            amount = option.get("price", {}).get("amount")
            currency = option.get("price", {}).get("currency")
        else:
            amount = option.get("amount")
            currency = option.get("currency")
        deep_link = option.get("deepLink") or option.get("url")

        agent_name = None
        agent_ids = option.get("agentIds") or []
        if agent_ids:
            first_agent_id = agent_ids[0]
            if isinstance(first_agent_id, str):
                node = agents_index.get(first_agent_id)
                if isinstance(node, dict):
                    agent_name = node.get("name")

        return (
            SkyscannerFlightClient._float_or_none(amount),
            SkyscannerFlightClient._string_or_none(currency),
            SkyscannerFlightClient._string_or_none(agent_name),
            SkyscannerFlightClient._string_or_none(deep_link),
        )

    @staticmethod
    def _resolve_node(ref: Any, index: dict[str, Any]) -> dict[str, Any] | None:
        if isinstance(ref, dict):
            return ref
        if isinstance(ref, str):
            node = index.get(ref)
            return node if isinstance(node, dict) else None
        return None

    @staticmethod
    def _place_from_index(ref: Any, places: dict[str, Any]) -> dict[str, Any] | None:
        if ref is None:
            return None
        node = places.get(str(ref))
        if not isinstance(node, dict):
            return None
        return {
            "id": str(ref),
            "name": SkyscannerFlightClient._string_or_none(node.get("name")),
            "iata": SkyscannerFlightClient._string_or_none(node.get("iata")),
            "entity_id": SkyscannerFlightClient._string_or_none(node.get("entityId")),
        }

    @staticmethod
    def _carrier_from_index(ref: Any, carriers: dict[str, Any]) -> dict[str, Any] | None:
        if ref is None:
            return None
        node = carriers.get(str(ref))
        if not isinstance(node, dict):
            return None
        return {
            "id": str(ref),
            "name": SkyscannerFlightClient._string_or_none(node.get("name")),
            "iata": SkyscannerFlightClient._string_or_none(node.get("iata")),
            "display_code": SkyscannerFlightClient._string_or_none(node.get("displayCode")),
        }

    @staticmethod
    def _datetime_to_iso(value: Any) -> str | None:
        if not isinstance(value, dict):
            return None
        year = value.get("year")
        month = value.get("month")
        day = value.get("day")
        if year is None or month is None or day is None:
            return None
        hour = int(value.get("hour", 0))
        minute = int(value.get("minute", 0))
        second = int(value.get("second", 0))
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}T{hour:02d}:{minute:02d}:{second:02d}"

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
