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

    async def get_indicative_roundtrip(
        self,
        *,
        origin_iata: str,
        destination_iata: str,
        departure_date: str,
        return_date: str,
        market: str = "UK",
        locale: str = "en-GB",
        currency: str = "EUR",
        limit: int = 10,
    ) -> tuple[dict[str, Any], ...]:
        outbound = await self.provider.search_indicative_anywhere(
            origin_iata=origin_iata,
            destination_iata=destination_iata,
            outbound_date=departure_date,
            market=market,
            locale=locale,
            currency=currency,
        )
        inbound = await self.provider.search_indicative_anywhere(
            origin_iata=destination_iata,
            destination_iata=origin_iata,
            outbound_date=return_date,
            market=market,
            locale=locale,
            currency=currency,
        )

        outbound_quotes = list(outbound.get("quotes") or [])
        inbound_quotes = list(inbound.get("quotes") or [])
        if not outbound_quotes or not inbound_quotes:
            return ()

        grouped: list[dict[str, Any]] = []
        for outbound_quote in outbound_quotes:
            for inbound_quote in inbound_quotes:
                grouped.append(_combine_indicative_quotes(outbound_quote, inbound_quote))

        ranked = sorted(grouped, key=lambda item: _extract_grouped_price(item))
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


def _combine_indicative_quotes(outbound_quote: dict[str, Any], inbound_quote: dict[str, Any]) -> dict[str, Any]:
    outbound_price = outbound_quote.get("price") if isinstance(outbound_quote.get("price"), dict) else {}
    inbound_price = inbound_quote.get("price") if isinstance(inbound_quote.get("price"), dict) else {}
    outbound_amount = _price_amount(outbound_price)
    inbound_amount = _price_amount(inbound_price)
    total_amount = None
    if outbound_amount is not None and inbound_amount is not None:
        total_amount = outbound_amount + inbound_amount
    elif outbound_amount is not None:
        total_amount = outbound_amount
    elif inbound_amount is not None:
        total_amount = inbound_amount

    return {
        "price": {
            "amount": total_amount,
            "unit": outbound_price.get("unit") or inbound_price.get("unit"),
        },
        "airports": outbound_quote.get("airports"),
        "outbound_datetime": outbound_quote.get("outbound_datetime"),
        "inbound_datetime": inbound_quote.get("outbound_datetime"),
        "is_direct": bool(outbound_quote.get("is_direct")) and bool(inbound_quote.get("is_direct")),
        "outbound": {
            "price": outbound_price,
            "airports": outbound_quote.get("airports"),
            "carrier": outbound_quote.get("carrier"),
            "datetime": outbound_quote.get("outbound_datetime"),
            "is_direct": outbound_quote.get("is_direct"),
        },
        "inbound": {
            "price": inbound_price,
            "airports": inbound_quote.get("airports"),
            "carrier": inbound_quote.get("carrier"),
            "datetime": inbound_quote.get("outbound_datetime"),
            "is_direct": inbound_quote.get("is_direct"),
        },
    }


def _price_amount(price: dict[str, Any]) -> float | None:
    value = price.get("amount")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_grouped_price(item: dict[str, Any]) -> float:
    price = item.get("price") if isinstance(item.get("price"), dict) else {}
    amount = _price_amount(price)
    return amount if amount is not None else float("inf")
