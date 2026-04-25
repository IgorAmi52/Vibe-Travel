"""Shared parsers for Booking.com API response format.

Used by both BookingComClient (live API) and FixtureHotelApiClient (recorded fixtures).
"""

from typing import Any

from core.models.hotel import (
    Destination,
    GeoCoordinates,
    HotelContent,
    HotelReview,
    HotelSearchResult,
    PriceBreakdown,
)


def parse_destinations(data: Any) -> list[Destination]:
    items = data.get("data", []) if isinstance(data, dict) else []
    results: list[Destination] = []

    for item in items:
        location = None
        lat = item.get("latitude")
        lon = item.get("longitude")
        if lat is not None and lon is not None:
            location = GeoCoordinates(latitude=float(lat), longitude=float(lon))

        results.append(Destination(
            entity_id=str(item.get("dest_id", "")),
            name=item.get("name", ""),
            dest_type=item.get("dest_type", ""),
            hierarchy=item.get("country", ""),
            location=location,
        ))
    return results


def parse_hotel_search(data: Any) -> list[HotelSearchResult]:
    hotels_raw = data.get("data", {}).get("hotels", []) if isinstance(data, dict) else []
    results: list[HotelSearchResult] = []

    for entry in hotels_raw:
        if not isinstance(entry, dict):
            continue

        prop = entry.get("property", {}) or {}
        hotel_id = str(entry.get("hotel_id", ""))

        price_info = prop.get("priceBreakdown", {}) or {}
        price: PriceBreakdown | None = None
        gross = price_info.get("grossPrice", {})
        if gross and gross.get("value") is not None:
            price = PriceBreakdown(
                gross_amount=float(gross["value"]),
                currency=gross.get("currency", "USD"),
                strikethrough_amount=_safe_float(price_info.get("strikethroughPrice", {}).get("value")),
                tax_amount=_safe_float(price_info.get("excludedPrice", {}).get("value")),
            )

        location = None
        lat = prop.get("latitude")
        lon = prop.get("longitude")
        if lat is not None and lon is not None:
            location = GeoCoordinates(latitude=float(lat), longitude=float(lon))

        results.append(HotelSearchResult(
            hotel_id=hotel_id,
            name=prop.get("name", ""),
            price=price,
            review_score=_safe_float(prop.get("reviewScore")),
            review_count=prop.get("reviewCount"),
            review_word=prop.get("reviewScoreWord"),
            quality_class=prop.get("qualityClass"),
            property_class=prop.get("propertyClass"),
            country_code=prop.get("countryCode"),
            location=location,
            photo_urls=prop.get("photoUrls", []),
            checkin_date=prop.get("checkinDate"),
            checkout_date=prop.get("checkoutDate"),
        ))

    return results


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_hotel_detail(data: Any) -> HotelContent | None:
    info = data.get("data", {}) if isinstance(data, dict) else {}
    if not info:
        return None

    raw_data = info.get("rawData", {}) or {}

    # Amenities: facilities_block.facilities + property_highlight_strip
    amenities: list[str] = []
    facilities_block = info.get("facilities_block", {}) or {}
    for facility in facilities_block.get("facilities", []):
        if isinstance(facility, dict):
            amenities.append(facility.get("name", str(facility)))
        else:
            amenities.append(str(facility))
    for highlight in info.get("property_highlight_strip", []):
        if isinstance(highlight, dict):
            name = highlight.get("name", "")
            if name and name not in amenities:
                amenities.append(name)

    # Photos from rawData.photoUrls
    images: list[str] = []
    for url in raw_data.get("photoUrls", []):
        if isinstance(url, str):
            images.append(url)

    return HotelContent(
        hotel_id=str(info.get("hotel_id", "")),
        name=info.get("hotel_name", ""),
        description=info.get("description") or None,
        amenities=amenities,
        star_rating=raw_data.get("propertyClass"),
        guest_rating=raw_data.get("reviewScore"),
        accommodation_type=info.get("accommodation_type_name"),
        images=images,
    )


def parse_description(data: Any) -> str | None:
    """Extract the narrative property description from getDescriptionAndInfo."""
    items = data.get("data", []) if isinstance(data, dict) else []
    # descriptiontype_id 6 = property overview narrative; skip type 7 (policies/check-in info)
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("descriptiontype_id") == 6:
            desc = item.get("description", "").strip()
            if desc:
                return desc
    # Fallback: return the longest description that isn't policies
    best = ""
    for item in items:
        if not isinstance(item, dict):
            continue
        desc = item.get("description", "").strip()
        if len(desc) > len(best) and item.get("descriptiontype_id") != 7:
            best = desc
    return best or None


def parse_reviews(data: Any) -> list[HotelReview]:
    raw = data.get("data", {}) if isinstance(data, dict) else {}
    review_list = raw.get("result", []) if isinstance(raw, dict) else []
    results: list[HotelReview] = []

    for item in review_list:
        if not isinstance(item, dict):
            continue

        pros = item.get("pros", "")
        cons = item.get("cons", "")
        parts = []
        if pros:
            parts.append(f"Pros: {pros}")
        if cons:
            parts.append(f"Cons: {cons}")
        content = " | ".join(parts) if parts else None

        results.append(HotelReview(
            title=item.get("title"),
            content=content,
            rating=item.get("average_score"),
            guest_type=item.get("travel_purpose"),
            review_date=item.get("date"),
            locale=item.get("languagecode"),
            country_name=item.get("countrycode"),
        ))
    return results
