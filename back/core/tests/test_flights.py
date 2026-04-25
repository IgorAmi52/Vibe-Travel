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
    async def test_resolve_iata_code_uses_autosuggest(self) -> None:
        connector = _FakeConnector(
            [
                {
                    "places": [
                        {
                            "entityId": "114117388",
                            "iataCode": "VVO",
                            "name": "Vladivostok",
                        }
                    ]
                }
            ]
        )
        client = SkyscannerFlightClient(
            base_url="https://example.test",
            api_key="key",
            api_host="host",
            connector=connector,
        )

        iata_code = await client.resolve_iata_code("Vladivostok")
        path, kwargs = connector.post_calls[0]
        self.assertEqual(path, "/apiservices/v3/autosuggest/flights")
        self.assertEqual(kwargs["json"]["query"]["searchTerm"], "Vladivostok")
        self.assertEqual(kwargs["json"]["limit"], 1)
        self.assertEqual(iata_code, "VVO")

    async def test_resolve_iata_code_falls_back_to_airport_information(self) -> None:
        connector = _FakeConnector(
            [
                {
                    "places": [
                        {
                            "entityId": "32031637",
                            "name": "Chamonix-Mont-Blanc",
                            "type": "PLACE_TYPE_CITY",
                            "airportInformation": {
                                "iataCode": "GVA",
                                "name": "Geneva",
                                "entityId": "95674055",
                            },
                        }
                    ]
                }
            ]
        )
        client = SkyscannerFlightClient(
            base_url="https://example.test",
            api_key="key",
            api_host="host",
            connector=connector,
        )

        iata_code = await client.resolve_iata_code("Chamonix")
        self.assertEqual(iata_code, "GVA")

    async def test_create_session_resolves_city_names_before_payload(self) -> None:
        connector = _FakeConnector(
            [
                {"places": [{"iataCode": "BCN"}]},
                {"places": [{"iataCode": "CDG"}]},
                {"sessionToken": "abc"},
            ]
        )
        client = SkyscannerFlightClient(
            base_url="https://example.test",
            api_key="key",
            api_host="host",
            connector=connector,
        )
        params = FlightSearchParams(
            origin_iata="Barcelona",
            destination_iata="Paris",
            departure_date=date(2026, 6, 10),
            return_date=date(2026, 6, 15),
        )

        await client.create_live_prices_session(params)
        self.assertEqual(connector.post_calls[0][0], "/apiservices/v3/autosuggest/flights")
        self.assertEqual(connector.post_calls[1][0], "/apiservices/v3/autosuggest/flights")
        path, kwargs = connector.post_calls[2]
        self.assertEqual(path, "/apiservices/v3/flights/live/search/create")
        legs = kwargs["json"]["query"]["queryLegs"]
        self.assertEqual(legs[0]["originPlaceId"]["iata"], "BCN")
        self.assertEqual(legs[0]["destinationPlaceId"]["iata"], "CDG")

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
        self.assertEqual(path, "/apiservices/v3/flights/live/search/create")
        legs = kwargs["json"]["query"]["queryLegs"]
        self.assertEqual(len(legs), 2)
        self.assertEqual(legs[0]["originPlaceId"]["iata"], "VIE")
        self.assertEqual(legs[1]["originPlaceId"]["iata"], "LON")
        self.assertEqual(legs[0]["date"], {"year": 2026, "month": 6, "day": 10})
        self.assertEqual(legs[1]["date"], {"year": 2026, "month": 6, "day": 15})

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
        path, _ = connector.post_calls[0]
        self.assertEqual(path, "/apiservices/v3/flights/live/search/poll/abc")
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
        self.assertEqual(path, "/apiservices/v3/flights/indicative/search")
        leg = kwargs["json"]["query"]["queryLegs"][0]
        self.assertEqual(leg["originPlace"]["queryPlace"]["iata"], "VIE")
        self.assertTrue(leg["destinationPlace"]["anywhere"])
        self.assertEqual(result["status"], "RESULT_STATUS_COMPLETE")
        self.assertEqual(result["quotes"][0]["airports"]["destination"]["iata"], "AGP")
        self.assertEqual(result["quotes"][0]["airports"]["origin"]["name"], "Vienna")
        self.assertEqual(result["quotes"][0]["price"]["amount"], 89.0)
        self.assertEqual(result["quotes"][0]["outbound_datetime"], "2026-07-01T00:00:00")

    async def test_indicative_anywhere_supports_anytime_payload(self) -> None:
        connector = _FakeConnector(
            [
                {
                    "status": "RESULT_STATUS_COMPLETE",
                    "content": {"results": {"quotes": {}, "places": {}, "carriers": {}}},
                }
            ]
        )
        client = SkyscannerFlightClient(
            base_url="https://example.test",
            api_key="key",
            api_host="host",
            connector=connector,
        )

        await client.search_indicative_anywhere(origin_iata="VIE")
        path, kwargs = connector.post_calls[0]
        self.assertEqual(path, "/apiservices/v3/flights/indicative/search")
        query = kwargs["json"]["query"]
        leg = query["queryLegs"][0]
        self.assertEqual(leg["originPlace"]["queryPlace"]["iata"], "VIE")
        self.assertTrue(leg["destinationPlace"]["anywhere"])
        self.assertIs(leg["anytime"], True)
        self.assertEqual(query["dateTimeGroupingType"], "DATE_TIME_GROUPING_TYPE_BY_MONTH")

    async def test_indicative_supports_specific_destination_without_dates(self) -> None:
        connector = _FakeConnector(
            [
                {
                    "status": "RESULT_STATUS_COMPLETE",
                    "content": {"results": {"quotes": {}, "places": {}, "carriers": {}}},
                }
            ]
        )
        client = SkyscannerFlightClient(
            base_url="https://example.test",
            api_key="key",
            api_host="host",
            connector=connector,
        )

        await client.search_indicative_anywhere(origin_iata="BCN", destination_iata="CDG")
        path, kwargs = connector.post_calls[0]
        self.assertEqual(path, "/apiservices/v3/flights/indicative/search")
        leg = kwargs["json"]["query"]["queryLegs"][0]
        self.assertEqual(leg["originPlace"]["queryPlace"]["iata"], "BCN")
        self.assertEqual(leg["destinationPlace"]["queryPlace"]["iata"], "CDG")
        self.assertIs(leg["anytime"], True)

    async def test_indicative_supports_date_range_for_dated_destination_search(self) -> None:
        connector = _FakeConnector(
            [
                {
                    "status": "RESULT_STATUS_COMPLETE",
                    "content": {"results": {"quotes": {}, "places": {}, "carriers": {}}},
                }
            ]
        )
        client = SkyscannerFlightClient(
            base_url="https://example.test",
            api_key="key",
            api_host="host",
            connector=connector,
        )

        await client.search_indicative_anywhere(
            origin_iata="BCN",
            destination_iata="CDG",
            outbound_date="2026-07-01",
            return_date="2026-07-05",
        )
        path, kwargs = connector.post_calls[0]
        self.assertEqual(path, "/apiservices/v3/flights/indicative/search")
        query = kwargs["json"]["query"]
        leg = query["queryLegs"][0]
        self.assertEqual(leg["originPlace"]["queryPlace"]["iata"], "BCN")
        self.assertEqual(leg["destinationPlace"]["queryPlace"]["iata"], "CDG")
        self.assertEqual(
            leg["date_range"],
            {
                "startDate": {"year": 2026, "month": 7},
                "endDate": {"year": 2026, "month": 7},
            },
        )
        self.assertNotIn("dateTimeGroupingType", query)


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

    async def test_service_groups_indicative_outbound_and_inbound_quotes(self) -> None:
        class _Provider:
            async def search_roundtrip_chains(self, params: FlightSearchParams):
                raise NotImplementedError

            async def search_indicative_anywhere(
                self,
                *,
                origin_iata: str,
                destination_iata: str | None = None,
                outbound_date: str | None = None,
                return_date: str | None = None,
                market: str = "UK",
                locale: str = "en-GB",
                currency: str = "EUR",
            ):
                del return_date, market, locale, currency
                if origin_iata == "BCN" and destination_iata == "CDG":
                    return {
                        "quotes": [
                            {
                                "airports": {
                                    "origin": {"iata": "BCN", "name": "Barcelona"},
                                    "destination": {"iata": "CDG", "name": "Paris CDG"},
                                },
                                "outbound_datetime": f"{outbound_date}T09:00:00",
                                "price": {"amount": 70.0, "unit": "PRICE_UNIT_WHOLE"},
                                "carrier": {"name": "Outbound Air"},
                                "is_direct": True,
                            }
                        ]
                    }
                return {
                    "quotes": [
                        {
                            "airports": {
                                "origin": {"iata": "CDG", "name": "Paris CDG"},
                                "destination": {"iata": "BCN", "name": "Barcelona"},
                            },
                            "outbound_datetime": f"{outbound_date}T18:00:00",
                            "price": {"amount": 80.0, "unit": "PRICE_UNIT_WHOLE"},
                            "carrier": {"name": "Inbound Air"},
                            "is_direct": True,
                        }
                    ]
                }

            async def close(self) -> None:
                return None

        service = FlightChainService(provider=_Provider())
        results = await service.get_indicative_roundtrip(
            origin_iata="BCN",
            destination_iata="CDG",
            departure_date="2026-07-01",
            return_date="2026-07-05",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["outbound_datetime"], "2026-07-01T09:00:00")
        self.assertEqual(results[0]["inbound_datetime"], "2026-07-05T18:00:00")
        self.assertEqual(results[0]["price"]["amount"], 150.0)
        self.assertEqual(results[0]["airports"]["destination"]["iata"], "CDG")

    async def test_service_calls_indicative_anywhere(self) -> None:
        class _Provider:
            async def search_roundtrip_chains(self, params: FlightSearchParams):
                raise NotImplementedError

            async def search_indicative_anywhere(
                self,
                *,
                origin_iata: str,
                destination_iata: str | None = None,
                outbound_date: str | None = None,
                return_date: str | None = None,
                market: str = "UK",
                locale: str = "en-GB",
                currency: str = "EUR",
            ):
                del destination_iata, return_date
                return {
                    "status": "RESULT_STATUS_COMPLETE",
                    "quotes": [
                        {"origin": {"iata": origin_iata}, "outbound_date": outbound_date, "price_amount": 99.0}
                    ],
                    "market": market,
                    "locale": locale,
                    "currency": currency,
                }

            async def close(self) -> None:
                return None

        service = FlightChainService(provider=_Provider())
        result = await service.get_indicative_anywhere(origin_iata="VIE", outbound_date="2026-07-01")
        self.assertEqual(result["quotes"][0]["origin"]["iata"], "VIE")
        self.assertEqual(result["quotes"][0]["outbound_date"], "2026-07-01")


if __name__ == "__main__":
    unittest.main()
