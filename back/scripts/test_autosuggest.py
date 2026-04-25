"""Exploratory script — hit Skyscanner autosuggest with various inputs and compare responses."""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from clients.api_connector import ApiConnector

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_KEY = os.environ["SKY_SCANNER_KEY"]

SEARCH_TERMS = [
    "Paris",
    "London",
    "Tokyo",
    "Bali",
    "New York",
    "Santorini",
    "Dubai Mall",
    "Hilton",
    "CDG",
]

# Try both possible API hosts
CANDIDATES = [
    {
        "name": "Skyscanner Partners API",
        "base_url": "https://partners.api.skyscanner.net",
        "path": "/apiservices/v3/autosuggest/hotels",
        "headers": {"x-api-key": API_KEY, "Content-Type": "application/json"},
    },
    {
        "name": "RapidAPI sky-scanner3",
        "base_url": "https://sky-scanner3.p.rapidapi.com",
        "path": "/v1/hotels/autosuggest",
        "headers": {
            "x-rapidapi-key": API_KEY,
            "x-rapidapi-host": "sky-scanner3.p.rapidapi.com",
            "Content-Type": "application/json",
        },
    },
    {
        "name": "RapidAPI sky-scrapper",
        "base_url": "https://sky-scrapper.p.rapidapi.com",
        "path": "/api/v1/hotels/searchDestination",
        "headers": {
            "x-rapidapi-key": API_KEY,
            "x-rapidapi-host": "sky-scrapper.p.rapidapi.com",
            "Content-Type": "application/json",
        },
    },
]

PAYLOAD = {"query": {"market": "UK", "locale": "en-GB", "searchTerm": "Paris"}}


async def probe_host(candidate: dict) -> None:
    print(f"\n--- {candidate['name']} ({candidate['base_url']}{candidate['path']}) ---")
    connector = ApiConnector(
        base_url=candidate["base_url"],
        headers=candidate["headers"],
        timeout=15.0,
        max_retries=1,
    )
    try:
        response = await connector.post(candidate["path"], json=PAYLOAD)
        data = response.json()
        print(f"STATUS: {response.status_code}")
        print(json.dumps(data, indent=2)[:2000])
    except Exception as exc:
        print(f"FAILED: {exc}")
    finally:
        await connector.close()


async def run_full_test(base_url: str, path: str, headers: dict) -> None:
    """Once we know the working host, run all search terms."""
    connector = ApiConnector(base_url=base_url, headers=headers, timeout=15.0, max_retries=1)

    print("\n\n" + "=" * 120)
    print(f"{'Term':<20} {'Name':<30} {'Type':<35} {'Score':<10} {'Entity ID':<18} {'Hierarchy'}")
    print("=" * 120)

    for term in SEARCH_TERMS:
        try:
            response = await connector.post(path, json={
                "query": {"market": "UK", "locale": "en-GB", "searchTerm": term}
            })
            data = response.json()
            places = data.get("places", data.get("results", []))
            if not places:
                print(f"{term:<20} (no results — keys: {list(data.keys())})")
                continue
            for i, item in enumerate(places[:5]):
                prefix = term if i == 0 else ""
                name = item.get("name", "?")
                ptype = item.get("type", "?")
                score = item.get("score", "?")
                eid = item.get("entityId", item.get("entity_id", "?"))
                hier = item.get("hierarchy", "?")
                print(f"{prefix:<20} {name:<30} {ptype:<35} {str(score):<10} {str(eid):<18} {hier}")
            print("-" * 120)
        except Exception as exc:
            print(f"{term:<20} ERROR: {exc}")

    await connector.close()


async def main() -> None:
    # Phase 1: find working host
    print("PHASE 1: Probing API hosts with 'Paris' query...\n")
    for c in CANDIDATES:
        await probe_host(c)

    # Phase 2: run full comparison with Partners API
    winner = CANDIDATES[0]
    await run_full_test(winner["base_url"], winner["path"], winner["headers"])


if __name__ == "__main__":
    asyncio.run(main())
