from __future__ import annotations

import re
from datetime import datetime

from core.flights import (
    FlightLegChain,
    FlightSearchParams,
    FlightProvider,
    FlightSegment,
    LivePricesPollResult,
    LivePricesSession,
    RoundTripChainResult,
)


class SyntheticFlightClient(FlightProvider):
    _PLACE_TO_IATA = {
        "barcelona": "BCN",
        "paris": "CDG",
        "mallorca": "PMI",
        "san sebastian": "EAS",
        "val d'isere": "LYS",
        "val d isere": "LYS",
        "chamonix": "CMF",
        "zermatt": "ZRH",
        "ljubljana": "LJU",
        "lake bled": "LJU",
        "vladivostok": "VVO",
    }

    async def resolve_iata_code(
        self,
        search_term: str,
        *,
        market: str = "UK",
        locale: str = "en-GB",
    ) -> str | None:
        del market, locale
        normalized = search_term.strip()
        if _looks_like_iata(normalized):
            return normalized.upper()
        return self._PLACE_TO_IATA.get(normalized.lower())

    async def create_live_prices_session(self, params: FlightSearchParams) -> LivePricesSession:
        return LivePricesSession(
            session_token=f"synthetic-{params.origin_iata}-{params.destination_iata}",
            polling_url=None,
            raw_payload={},
        )

    async def poll_live_prices_session(self, session: LivePricesSession) -> LivePricesPollResult:
        raise NotImplementedError("SyntheticFlightClient polls through search_roundtrip_chains directly.")

    async def search_roundtrip_chains(self, params: FlightSearchParams) -> LivePricesPollResult:
        outbound_departure = _at(params.departure_date.isoformat(), "08:30")
        outbound_arrival = _at(params.departure_date.isoformat(), "11:10")
        inbound_departure = _at(params.return_date.isoformat(), "18:15")
        inbound_arrival = _at(params.return_date.isoformat(), "20:55")

        outbound_segment = FlightSegment(
            segment_id="synthetic-out-1",
            origin_iata=params.origin_iata,
            destination_iata=params.destination_iata,
            departure_at=outbound_departure,
            arrival_at=outbound_arrival,
            marketing_carrier="MOCK AIR",
            operating_carrier="MOCK AIR",
            flight_number="MK101",
            duration_minutes=160,
        )
        inbound_segment = FlightSegment(
            segment_id="synthetic-in-1",
            origin_iata=params.destination_iata,
            destination_iata=params.origin_iata,
            departure_at=inbound_departure,
            arrival_at=inbound_arrival,
            marketing_carrier="MOCK AIR",
            operating_carrier="MOCK AIR",
            flight_number="MK102",
            duration_minutes=160,
        )
        outbound_chain = FlightLegChain(
            leg_id="synthetic-leg-out",
            origin_iata=params.origin_iata,
            destination_iata=params.destination_iata,
            departure_at=outbound_departure,
            arrival_at=outbound_arrival,
            duration_minutes=160,
            stop_count=0,
            segments=(outbound_segment,),
        )
        inbound_chain = FlightLegChain(
            leg_id="synthetic-leg-in",
            origin_iata=params.destination_iata,
            destination_iata=params.origin_iata,
            departure_at=inbound_departure,
            arrival_at=inbound_arrival,
            duration_minutes=160,
            stop_count=0,
            segments=(inbound_segment,),
        )
        result = RoundTripChainResult(
            itinerary_id=f"{params.origin_iata}-{params.destination_iata}-synthetic",
            outbound_chain=outbound_chain,
            inbound_chain=inbound_chain,
            price_amount=249.0,
            price_currency=params.currency,
            agent_name="Synthetic Flights",
            deep_link="https://example.test/flights/mock",
            validating_carriers=("MOCK AIR",),
        )
        return LivePricesPollResult(
            status="COMPLETED",
            completed=True,
            results=(result,),
            raw_payload={},
        )

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
    ) -> dict[str, object]:
        del market, locale
        primary_destination = destination_iata or "PMI"
        quotes = [
            {
                "airports": {
                    "origin": {"iata": origin_iata, "name": origin_iata},
                    "destination": {"iata": primary_destination, "name": primary_destination},
                },
                "outbound_datetime": f"{outbound_date}T00:00:00" if outbound_date else None,
                "inbound_datetime": f"{return_date}T00:00:00" if return_date else None,
                "price": {"amount": 120.0, "unit": currency},
                "is_direct": True,
            },
            {
                "airports": {
                    "origin": {"iata": origin_iata, "name": origin_iata},
                    "destination": {"iata": "AGP", "name": "Malaga"},
                },
                "outbound_datetime": f"{outbound_date}T00:00:00" if outbound_date else None,
                "inbound_datetime": f"{return_date}T00:00:00" if return_date else None,
                "price": {"amount": 135.0, "unit": currency},
                "is_direct": True,
            },
        ]
        return {
            "status": "RESULT_STATUS_COMPLETE",
            "quotes": quotes,
        }

    async def close(self) -> None:
        return None


def _at(day: str, time_value: str) -> str:
    return datetime.fromisoformat(f"{day}T{time_value}:00").isoformat()


def _looks_like_iata(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]{3}", value.strip()))
