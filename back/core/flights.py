from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


@dataclass(slots=True, frozen=True)
class FlightSearchParams:
    origin_iata: str
    destination_iata: str
    departure_date: date
    return_date: date
    market: str = "UK"
    locale: str = "en-GB"
    currency: str = "EUR"
    adults: int = 1
    children_ages: tuple[int, ...] = ()
    cabin_class: str = "CABIN_CLASS_ECONOMY"
    direct_only: bool = False


@dataclass(slots=True, frozen=True)
class FlightSegment:
    segment_id: str | None
    origin_iata: str
    destination_iata: str
    departure_at: str
    arrival_at: str
    marketing_carrier: str | None = None
    operating_carrier: str | None = None
    flight_number: str | None = None
    duration_minutes: int | None = None
    aircraft_code: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class FlightLegChain:
    leg_id: str
    origin_iata: str
    destination_iata: str
    departure_at: str
    arrival_at: str
    duration_minutes: int | None
    stop_count: int
    segments: tuple[FlightSegment, ...]
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RoundTripChainResult:
    itinerary_id: str
    outbound_chain: FlightLegChain
    inbound_chain: FlightLegChain
    price_amount: float | None = None
    price_currency: str | None = None
    agent_name: str | None = None
    deep_link: str | None = None
    validating_carriers: tuple[str, ...] = ()
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LivePricesSession:
    session_token: str
    polling_url: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LivePricesPollResult:
    status: str
    completed: bool
    results: tuple[RoundTripChainResult, ...]
    raw_payload: dict[str, Any] = field(default_factory=dict)


class FlightProvider(Protocol):
    async def create_live_prices_session(self, params: FlightSearchParams) -> LivePricesSession:
        ...

    async def poll_live_prices_session(self, session: LivePricesSession) -> LivePricesPollResult:
        ...

    async def search_roundtrip_chains(self, params: FlightSearchParams) -> LivePricesPollResult:
        ...

    async def close(self) -> None:
        ...


@dataclass(slots=True)
class FlightChainService:
    provider: FlightProvider

    async def get_roundtrip_chains(
        self,
        params: FlightSearchParams,
        *,
        limit: int = 10,
    ) -> tuple[RoundTripChainResult, ...]:
        poll_result = await self.provider.search_roundtrip_chains(params)
        if not poll_result.results:
            return ()

        ranked = sorted(
            poll_result.results,
            key=lambda item: item.price_amount if item.price_amount is not None else float("inf"),
        )
        return tuple(ranked[:limit])
