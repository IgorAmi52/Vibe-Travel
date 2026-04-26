import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from clients.booking_parsers import parse_description, parse_destinations, parse_hotel_detail, parse_hotel_search, parse_reviews
from core.api.hotel_api_client import HotelApiClient
from core.models.hotel import Destination, HotelContent, HotelReview, HotelSearchResult

logger = logging.getLogger(__name__)


class FixtureHotelApiClient(HotelApiClient):
    """Reads pre-recorded JSON fixtures instead of calling a live API.

    Fixture layout (created by scripts/record_fixtures.py):
        fixtures/{destination}/
            destinations.json
            hotels.json
            content/{hotel_id}.json
            reviews/{hotel_id}.json
    """

    def __init__(self, fixtures_dir: str | Path) -> None:
        self._root = Path(fixtures_dir)
        self._entity_index: dict[str, Path] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Map entity_id → destination directory for O(1) lookups."""
        for dest_dir in self._root.iterdir():
            if not dest_dir.is_dir():
                continue
            dest_file = dest_dir / "destinations.json"
            if not dest_file.exists():
                continue
            data = json.loads(dest_file.read_text())
            for item in data.get("data", []):
                eid = str(item.get("dest_id", ""))
                if eid:
                    self._entity_index[eid] = dest_dir

    def _load(self, path: Path) -> Any:
        if not path.exists():
            logger.warning("Fixture not found: %s", path)
            return None
        return json.loads(path.read_text())

    async def autosuggest(self, search_term: str) -> list[Destination]:
        dest_dir = self._root / search_term.lower()
        data = self._load(dest_dir / "destinations.json")
        if not data:
            return []
        return parse_destinations(data)

    async def indicative_search(
        self,
        entity_id: str,
        check_in: date,
        check_out: date,
        search_type: str = "city",
        currency: str = "USD",
        search_type: str = "city",
    ) -> list[HotelSearchResult]:
        dest_dir = self._entity_index.get(entity_id)
        if not dest_dir:
            return []
        data = self._load(dest_dir / "hotels.json")
        return parse_hotel_search(data) if data else []

    async def get_content(self, hotel_ids: list[str]) -> list[HotelContent]:
        results: list[HotelContent] = []
        for hotel_id in hotel_ids:
            path = self._find_file("content", f"{hotel_id}.json")
            if not path:
                continue
            parsed = parse_hotel_detail(self._load(path))
            if parsed:
                results.append(parsed)
        return results

    async def get_description(self, hotel_id: str) -> str | None:
        path = self._find_file("descriptions", f"{hotel_id}.json")
        if not path:
            return None
        data = self._load(path)
        return parse_description(data) if data else None

    async def get_reviews(self, hotel_id: str, limit: int = 30) -> list[HotelReview]:
        path = self._find_file("reviews", f"{hotel_id}.json")
        if not path:
            return []
        data = self._load(path)
        return parse_reviews(data)[:limit] if data else []

    async def close(self) -> None:
        return None

    def _find_file(self, subfolder: str, filename: str) -> Path | None:
        for dest_dir in self._entity_index.values():
            candidate = dest_dir / subfolder / filename
            if candidate.exists():
                return candidate
        return None
