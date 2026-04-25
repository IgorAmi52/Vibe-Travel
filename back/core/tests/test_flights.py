from __future__ import annotations

import unittest
from datetime import date

from core.clients.skyscanner_flights import SkyscannerFlightClient
from core.flights import (
    FlightChainService,
    FlightLegChain,
    FlightSearchParams,
    FlightSegment,
    LivePricesPollResult,
    LivePricesSession,
    RoundTripChainResult,
)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _FakeConnector:
    def __init__(self, responses: list[dict]):
        self._responses = responses
        self.post_calls: list[tuple[str, dict]] = []

    async def post(self, url: str, **kwargs):
        self.post_calls.append((url, kwargs))
        if not self._responses:
            raise RuntimeError("No responses configured")
        return _FakeResponse(self._responses.pop(0))

    async def close(self) -> None:
        return None


def _params() -> FlightSearchParams:
    return FlightSearchParams(
        origin_iata="VIE",
        destination_iata="LON",
        departure_date=date(2026, 6, 10),
        return_date=date(2026, 6, 15),
        direct_only=True,
    )


class SkyscannerFlightClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_payload_contains_outbound_and_inbound_legs(self) -> None:
        connector = _FakeConnector([{"sessionToken": "abc"}])
        client = SkyscannerFlightClient(
            base_url="https://example.test",
            api_key="key",
            api_host="host",
            connector=connector,
        )

        await client.create_live_prices_session(_params())
        path, kwargs = connector.post_calls[0]
        self.assertEqual(path, "/api/v1/flights/live/search/create")
        legs = kwargs["json"]["query"]["queryLegs"]
        self.assertEqual(len(legs), 2)
        self.assertEqual(legs[0]["originPlaceId"]["iata"], "VIE")
        self.assertEqual(legs[1]["originPlaceId"]["iata"], "LON")

    async def test_poll_maps_roundtrip_chains(self) -> None:
        connector = _FakeConnector(
            [
                {
                    "status": "RESULT_STATUS_COMPLETE",
                    "itineraries": [{"id": "it-1", "legIds": ["leg-out", "leg-in"], "pricingOptions": ["po-1"]}],
                    "legs": {
                        "leg-out": {
                            "id": "leg-out",
                            "originIata": "VIE",
                            "destinationIata": "LON",
                            "departure": "2026-06-10T08:00:00",
                            "arrival": "2026-06-10T10:00:00",
                            "segmentIds": ["seg-out"],
                        },
                        "leg-in": {
                            "id": "leg-in",
                            "originIata": "LON",
                            "destinationIata": "VIE",
                            "departure": "2026-06-15T18:00:00",
                            "arrival": "2026-06-15T20:00:00",
                            "segmentIds": ["seg-in"],
                        },
                    },
                    "segments": {
                        "seg-out": {
                            "id": "seg-out",
                            "originIata": "VIE",
                            "destinationIata": "LON",
                            "departure": "2026-06-10T08:00:00",
                            "arrival": "2026-06-10T10:00:00",
                        },
                        "seg-in": {
                            "id": "seg-in",
                            "originIata": "LON",
                            "destinationIata": "VIE",
                            "departure": "2026-06-15T18:00:00",
                            "arrival": "2026-06-15T20:00:00",
                        },
                    },
                    "pricingOptions": {"po-1": {"price": {"amount": 190, "currency": "EUR"}}},
                }
            ]
        )
        client = SkyscannerFlightClient(
            base_url="https://example.test",
            api_key="key",
            api_host="host",
            connector=connector,
        )

        result = await client.poll_live_prices_session(LivePricesSession(session_token="abc"))
        self.assertTrue(result.completed)
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].outbound_chain.origin_iata, "VIE")
        self.assertEqual(result.results[0].inbound_chain.origin_iata, "LON")

    async def test_indicative_anywhere_payload_and_mapping(self) -> None:
        connector = _FakeConnector(
            [
                {
                    "status": "RESULT_STATUS_COMPLETE",
                    "content": {
                        "results": {
                            "quotes": {
                                "q-1": {
                                    "minPrice": {"amount": "89", "unit": "EUR"},
                                    "isDirect": True,
                                    "outboundLeg": {
                                        "originPlaceId": "p-vie",
                                        "destinationPlaceId": "p-agp",
                                        "departureDateTime": {"year": 2026, "month": 7, "day": 1},
                                        "marketingCarrierId": "c-1",
                                    },
                                }
                            },
                            "places": {
                                "p-vie": {"name": "Vienna", "iata": "VIE", "entityId": "27544008"},
                                "p-agp": {"name": "Malaga", "iata": "AGP", "entityId": "95673381"},
                            },
                            "carriers": {"c-1": {"name": "Ryanair", "iata": "FR", "displayCode": "FR"}},
                        }
                    },
                }
            ]
        )
        client = SkyscannerFlightClient(
            base_url="https://example.test",
            api_key="key",
            api_host="host",
            connector=connector,
        )

        result = await client.search_indicative_anywhere(origin_iata="VIE", outbound_date="2026-07-01")
        path, kwargs = connector.post_calls[0]
        self.assertEqual(path, "/api/v1/flights/indicative/search")
        leg = kwargs["json"]["query"]["queryLegs"][0]
        self.assertEqual(leg["originPlace"]["queryPlace"]["iata"], "VIE")
        self.assertTrue(leg["destinationPlace"]["anywhere"])
        self.assertEqual(result["status"], "RESULT_STATUS_COMPLETE")
        self.assertEqual(result["quotes"][0]["destination"]["iata"], "AGP")


class FlightChainServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_limits_and_sorts(self) -> None:
        class _Provider:
            async def search_roundtrip_chains(self, params: FlightSearchParams):
                del params
                leg_out = FlightLegChain(
                    leg_id="o1",
                    origin_iata="VIE",
                    destination_iata="LON",
                    departure_at="2026-06-10T08:00:00",
                    arrival_at="2026-06-10T10:00:00",
                    duration_minutes=120,
                    stop_count=0,
                    segments=(
                        FlightSegment(
                            segment_id="s1",
                            origin_iata="VIE",
                            destination_iata="LON",
                            departure_at="2026-06-10T08:00:00",
                            arrival_at="2026-06-10T10:00:00",
                        ),
                    ),
                )
                leg_in = FlightLegChain(
                    leg_id="i1",
                    origin_iata="LON",
                    destination_iata="VIE",
                    departure_at="2026-06-15T18:00:00",
                    arrival_at="2026-06-15T20:00:00",
                    duration_minutes=120,
                    stop_count=0,
                    segments=(
                        FlightSegment(
                            segment_id="s2",
                            origin_iata="LON",
                            destination_iata="VIE",
                            departure_at="2026-06-15T18:00:00",
                            arrival_at="2026-06-15T20:00:00",
                        ),
                    ),
                )
                return LivePricesPollResult(
                    status="COMPLETE",
                    completed=True,
                    results=(
                        RoundTripChainResult(
                            itinerary_id="expensive",
                            outbound_chain=leg_out,
                            inbound_chain=leg_in,
                            price_amount=400.0,
                            price_currency="EUR",
                        ),
                        RoundTripChainResult(
                            itinerary_id="cheap",
                            outbound_chain=leg_out,
                            inbound_chain=leg_in,
                            price_amount=100.0,
                            price_currency="EUR",
                        ),
                    ),
                )

            async def close(self) -> None:
                return None

        service = FlightChainService(provider=_Provider())
        results = await service.get_roundtrip_chains(_params(), limit=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].itinerary_id, "cheap")


if __name__ == "__main__":
    unittest.main()
