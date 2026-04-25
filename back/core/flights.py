from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class LivePricesSession:
    session_token: str
    polling_url: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LivePricesPollResult:
    status: str
    completed: bool
    results: tuple[RoundTripChainResult, ...]
    raw_payload: dict[str, Any] = field(default_factory=dict)


class FlightProvider(Protocol):
    async def resolve_iata_code(
        self,
        search_term: str,
        *,
        market: str = "UK",
        locale: str = "en-GB",
    ) -> str | None:
        ...

    async def create_live_prices_session(self, params: FlightSearchParams) -> LivePricesSession:
        ...

    async def poll_live_prices_session(self, session: LivePricesSession) -> LivePricesPollResult:
        ...

    async def search_roundtrip_chains(self, params: FlightSearchParams) -> LivePricesPollResult:
        ...

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
    ) -> dict[str, Any]:
        ...

    async def close(self) -> None:
        ...


@dataclass
class FlightChainService:
    provider: FlightProvider

    async def resolve_iata_code(
        self,
        search_term: str,
        *,
        market: str = "UK",
        locale: str = "en-GB",
    ) -> str | None:
        return await self.provider.resolve_iata_code(search_term, market=market, locale=locale)

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

    async def get_indicative_anywhere(
        self,
        *,
        origin_iata: str,
        destination_iata: str | None = None,
        outbound_date: str | None = None,
        return_date: str | None = None,
        market: str = "UK",
        locale: str = "en-GB",
        currency: str = "EUR",
    ) -> dict[str, Any]:
        return await self.provider.search_indicative_anywhere(
            origin_iata=origin_iata,
            destination_iata=destination_iata,
            outbound_date=outbound_date,
            return_date=return_date,
            market=market,
            locale=locale,
            currency=currency,
        )
