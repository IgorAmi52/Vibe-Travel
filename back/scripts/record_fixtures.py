"""Record Booking.com API responses as JSON fixtures.

Run once with a valid BOOKING_RAPIDAPI_KEY to capture responses for
each destination. Saved fixtures power FixtureHotelApiClient for
offline development.

Usage:
    cd back && python -m scripts.record_fixtures

Fixture layout:
    fixtures/{destination}/
        destinations.json
        hotels.json
        content/{hotel_id}.json
        reviews/{hotel_id}.json
"""

import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

from clients.api_connector import ApiConnector

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_KEY = os.environ["BOOKING_RAPIDAPI_KEY"]
BASE_URL = "https://booking-com15.p.rapidapi.com"
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "booking-com15.p.rapidapi.com",
}

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

DESTINATIONS = ["Paris", "Bali", "Tokyo"]
MAX_HOTELS_PER_DESTINATION = 10
REVIEWS_PER_HOTEL = 30


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"    Saved → {path.relative_to(FIXTURES_DIR.parent)}")


async def record_destination(connector: ApiConnector, dest_name: str) -> None:
    dest_dir = FIXTURES_DIR / dest_name.lower()
    print(f"\n{'=' * 60}")
    print(f"  Recording: {dest_name}")
    print("=" * 60)

    # ── 1. Destination search ───────────────────────────────────────
    print("\n  [1/4] Destination search...")
    try:
        resp = await connector.get(
            "/api/v1/hotels/searchDestination", params={"query": dest_name},
        )
        dest_data = resp.json()
    except Exception as exc:
        print(f"    FAILED: {exc}")
        return

    save_json(dest_dir / "destinations.json", dest_data)

    items = dest_data.get("data", [])
    if not items:
        print("    No destinations found. Skipping.")
        return

    dest_id = str(items[0].get("dest_id", ""))
    print(f"    dest_id: {dest_id}")

    # ── 2. Hotel search ─────────────────────────────────────────────
    print("\n  [2/4] Hotel search...")
    base_date = date.today() + timedelta(days=30)
    check_in = base_date
    check_out = check_in + timedelta(days=3)

    try:
        resp = await connector.get("/api/v1/hotels/searchHotels", params={
            "dest_id": dest_id,
            "search_type": "city",
            "arrival_date": check_in.isoformat(),
            "departure_date": check_out.isoformat(),
            "adults": 2,
            "room_qty": 1,
            "currency_code": "USD",
            "languagecode": "en-us",
        })
        hotels_data = resp.json()
    except Exception as exc:
        print(f"    FAILED: {exc}")
        return

    save_json(dest_dir / "hotels.json", hotels_data)

    hotels = hotels_data.get("data", {}).get("hotels", [])
    hotel_ids = [
        str(h["hotel_id"]) for h in hotels[:MAX_HOTELS_PER_DESTINATION]
        if isinstance(h, dict) and "hotel_id" in h
    ]
    print(f"    Found {len(hotels)} hotels, recording top {len(hotel_ids)}")

    # ── 3. Content per hotel ────────────────────────────────────────
    print(f"\n  [3/4] Hotel details ({len(hotel_ids)} hotels)...")
    default_arrival = base_date.isoformat()
    default_departure = (base_date + timedelta(days=1)).isoformat()

    for hid in hotel_ids:
        try:
            resp = await connector.get("/api/v1/hotels/getHotelDetails", params={
                "hotel_id": hid,
                "arrival_date": default_arrival,
                "departure_date": default_departure,
                "adults": 1,
                "room_qty": 1,
                "currency_code": "USD",
                "languagecode": "en-us",
            })
            save_json(dest_dir / "content" / f"{hid}.json", resp.json())
        except Exception as exc:
            print(f"    Hotel {hid} content FAILED: {exc}")

    # ── 4. Reviews per hotel ────────────────────────────────────────
    print(f"\n  [4/4] Reviews ({len(hotel_ids)} hotels, up to {REVIEWS_PER_HOTEL} each)...")
    for hid in hotel_ids:
        all_pages: list = []
        page = 0
        collected = 0

        while collected < REVIEWS_PER_HOTEL:
            try:
                resp = await connector.get("/api/v1/hotels/getHotelReviews", params={
                    "hotel_id": hid,
                    "languagecode": "en-us",
                    "sort_type": "SORT_MOST_RELEVANT",
                    "page": page,
                })
                page_data = resp.json()
            except Exception as exc:
                print(f"    Hotel {hid} reviews page {page} FAILED: {exc}")
                break

            results = page_data.get("data", {}).get("result", [])
            if not results:
                break

            all_pages.extend(results)
            collected += len(results)
            page += 1

        if all_pages:
            save_json(
                dest_dir / "reviews" / f"{hid}.json",
                {"data": {"result": all_pages[:REVIEWS_PER_HOTEL]}},
            )


async def main() -> None:
    connector = ApiConnector(
        base_url=BASE_URL, headers=HEADERS, timeout=30.0, max_retries=2,
    )
    try:
        for dest in DESTINATIONS:
            await record_destination(connector, dest)
    finally:
        await connector.close()

    print(f"\n{'=' * 60}")
    print(f"  Done. Fixtures saved to {FIXTURES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
