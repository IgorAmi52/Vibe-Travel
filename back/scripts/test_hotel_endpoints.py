"""End-to-end smoke test for Booking.com hotel endpoints via RapidAPI.

Flow: searchDestination → searchHotels → getHotelDetails → getHotelReviews.
Uses BookingComClient through the HotelApiClient interface.
"""

import asyncio
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

from clients.api_connector import ApiConnector
from clients.booking_client import BookingComClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_KEY = os.environ["BOOKING_RAPIDAPI_KEY"]
BASE_URL = "https://booking-com15.p.rapidapi.com"
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "booking-com15.p.rapidapi.com",
}

DESTINATION = "Paris"


def section(title: str) -> None:
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print("=" * 80)


async def main() -> None:
    connector = ApiConnector(
        base_url=BASE_URL, headers=HEADERS, timeout=30.0, max_retries=2,
    )
    client = BookingComClient(api_connector=connector)

    try:
        # ── 1. Destination Search ───────────────────────────────────────
        section(f"1. Destination Search — '{DESTINATION}'")
        destinations = await client.autosuggest(DESTINATION)

        if not destinations:
            print("  No destinations found. Aborting.")
            return

        for d in destinations[:5]:
            loc = f"({d.location.latitude:.4f}, {d.location.longitude:.4f})" if d.location else ""
            print(f"  {d.entity_id:<12} {d.name:<40} {d.hierarchy:<10} {loc}")

        dest_id = destinations[0].entity_id
        print(f"\n  Using dest_id: {dest_id}")

        # ── 2. Hotel Search ─────────────────────────────────────────────
        section("2. Hotel Search")
        check_in = date.today() + timedelta(days=30)
        check_out = check_in + timedelta(days=3)
        print(f"  Dates: {check_in} → {check_out}")

        search_data = await client.indicative_search(
            entity_id=dest_id,
            check_in=check_in,
            check_out=check_out,
        )

        if not search_data:
            print("  Empty response.")
            return

        raw = json.dumps(search_data, indent=2)
        print(f"  Response keys: {list(search_data.keys())}")
        print(raw[:3000])
        if len(raw) > 3000:
            print(f"  ... ({len(raw)} total chars, truncated)")

        # Extract first hotel_id
        hotel_id = _extract_hotel_id(search_data)
        if not hotel_id:
            print("\n  Could not extract hotel_id from search response. Aborting.")
            return
        print(f"\n  Using hotel_id: {hotel_id}")

        # ── 3. Hotel Details ────────────────────────────────────────────
        section(f"3. Hotel Details — {hotel_id}")
        content_list = await client.get_content([hotel_id])

        if not content_list:
            print("  No content returned.")
        else:
            for c in content_list:
                print(f"  Name:       {c.name}")
                print(f"  Type:       {c.accommodation_type}")
                print(f"  Stars:      {c.star_rating}")
                print(f"  Guest:      {c.guest_rating}")
                print(f"  Amenities:  {c.amenities[:10]}")
                desc_preview = (c.description or "")[:200]
                print(f"  Desc:       {desc_preview}...")
                print(f"  Images:     {len(c.images)} total")

        # ── 4. Reviews ──────────────────────────────────────────────────
        section(f"4. Reviews — {hotel_id}")
        reviews = await client.get_reviews(hotel_id, limit=5)

        if not reviews:
            print("  No reviews returned.")
        else:
            for i, r in enumerate(reviews, 1):
                print(f"\n  [{i}] {r.title or '(no title)'} — rating: {r.rating}")
                print(f"      Guest: {r.guest_type or '?'} | Date: {r.review_date or '?'}")
                preview = (r.content or "")[:200]
                print(f"      {preview}")

        print(f"\n{'=' * 80}")
        print("  Done.")
        print("=" * 80)

    finally:
        await connector.close()


def _extract_hotel_id(data: dict) -> str | None:
    """Extract first hotel_id from Booking.com searchHotels response."""
    hotels = data.get("data", {}).get("hotels", [])
    if hotels and isinstance(hotels[0], dict):
        hid = hotels[0].get("hotel_id")
        if hid is not None:
            return str(hid)
    return None


if __name__ == "__main__":
    asyncio.run(main())
