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
    hierarchy: str
    location: GeoCoordinates | None = None
