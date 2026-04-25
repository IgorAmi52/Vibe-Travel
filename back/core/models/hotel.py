from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Hotel:
    hotel_id: str
    name: str
    price: float | None = None
    currency: str | None = None
    description: str | None = None
    amenities: list[str] = field(default_factory=list)
    star_rating: float | None = None
    guest_rating: float | None = None
    accommodation_type: str | None = None
    reviews: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)


@dataclass
class HotelContent:
    hotel_id: str
    name: str
    description: str | None = None
    amenities: list[str] = field(default_factory=list)
    star_rating: float | None = None
    guest_rating: float | None = None
    accommodation_type: str | None = None
    images: list[str] = field(default_factory=list)


@dataclass
class HotelReview:
    title: str | None = None
    content: str | None = None
    rating: float | None = None
    guest_type: str | None = None
    review_date: str | None = None
    locale: str | None = None
    country_name: str | None = None


@dataclass
class ScoredHotel:
    hotel: Hotel
    vibe_similarity: float
    price_score: float
    guest_rating_score: float
    composite_score: float


@dataclass
class GeoCoordinates:
    latitude: float
    longitude: float


@dataclass
class Destination:
    entity_id: str
    name: str
    dest_type: str
    hierarchy: str
    location: GeoCoordinates | None = None


@dataclass
class PriceBreakdown:
    gross_amount: float
    currency: str
    strikethrough_amount: float | None = None
    tax_amount: float | None = None


@dataclass
class HotelSearchResult:
    hotel_id: str
    name: str
    price: PriceBreakdown | None = None
    review_score: float | None = None
    review_count: int | None = None
    review_word: str | None = None
    quality_class: int | None = None
    property_class: int | None = None
    country_code: str | None = None
    location: GeoCoordinates | None = None
    photo_urls: list[str] = field(default_factory=list)
    checkin_date: str | None = None
    checkout_date: str | None = None
