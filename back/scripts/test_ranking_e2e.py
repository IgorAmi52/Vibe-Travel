"""End-to-end test of the hotel ranking pipeline with detailed logging.

Wires up all real implementations, runs the full pipeline for a given
destination + vibe query, and persists a detailed log to scripts/logs/.

Run from back/:
    python -m scripts.test_ranking_e2e
"""

import asyncio
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from clients.api_connector import ApiConnector
from clients.booking_client import BookingComClient
from clients.cosine_similarity_service import CosineSimilarityService
from clients.gemini_embed_provider import GeminiEmbedProvider
from core.models.hotel import Hotel
from core.services.hotel_embedding_service_impl import HotelEmbeddingServiceImpl
from core.services.hotel_ranking_service import HotelRankingService

# ── Config ──────────────────────────────────────────────────────────────

DESTINATION = "Lisbon"
VIBE_QUERY = "rooftop bars nightlife vibrant culture street food"
CHECK_IN_OFFSET_DAYS = 30
STAY_NIGHTS = 4
CURRENCY = "USD"
TOP_N = 10
MAX_REVIEWS = 20

VIBE_WEIGHT = 0.7
PRICE_WEIGHT = 0.2
RATING_WEIGHT = 0.1

BOOKING_BASE_URL = "https://booking-com15.p.rapidapi.com"

# ── Logging Setup ───────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"ranking_e2e_{timestamp}.log"

logger = logging.getLogger("ranking_e2e")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Also capture library logs to file
for lib_logger_name in ("clients", "core", "httpx"):
    lib_logger = logging.getLogger(lib_logger_name)
    lib_logger.setLevel(logging.DEBUG)
    lib_logger.addHandler(file_handler)


def section(title: str) -> None:
    border = "=" * 80
    logger.info("")
    logger.info(border)
    logger.info("  %s", title)
    logger.info(border)


def timed(label: str):
    """Context manager that logs elapsed time for a step."""

    class Timer:
        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, *_):
            elapsed = time.perf_counter() - self.start
            logger.info("  [%s] completed in %.2fs", label, elapsed)

    return Timer()


# ── Pipeline ────────────────────────────────────────────────────────────


async def main() -> None:
    logger.info("Log file: %s", log_file)
    logger.info("Destination: %s | Vibe: '%s'", DESTINATION, VIBE_QUERY)

    api_key = os.environ.get("BOOKING_RAPIDAPI_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not gemini_key:
        logger.error("Missing env vars: BOOKING_RAPIDAPI_KEY and GEMINI_API_KEY required")
        return

    connector = ApiConnector(
        base_url=BOOKING_BASE_URL,
        headers={
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "booking-com15.p.rapidapi.com",
        },
        timeout=30.0,
        max_retries=3,
    )
    hotel_api = BookingComClient(api_connector=connector)
    embed_provider = GeminiEmbedProvider(api_key=gemini_key)
    similarity_service = CosineSimilarityService()
    embedding_service = HotelEmbeddingServiceImpl(embed_provider=embed_provider)

    ranking_service = HotelRankingService(
        hotel_api=hotel_api,
        embedding_service=embedding_service,
        similarity_service=similarity_service,
        vibe_weight=VIBE_WEIGHT,
        price_weight=PRICE_WEIGHT,
        rating_weight=RATING_WEIGHT,
    )

    pipeline_start = time.perf_counter()

    try:
        # ── Step 1: Resolve Destination ─────────────────────────────
        section(f"Step 1: Resolve Destination — '{DESTINATION}'")
        with timed("resolve_destination_entity"):
            entity_id, search_type = await ranking_service._resolve_destination_entity(DESTINATION)
        logger.info("  Resolved: %s → entity=%s (type=%s)", DESTINATION, entity_id, search_type)

        # ── Step 2: Indicative Search ───────────────────────────────
        check_in = date.today() + timedelta(days=CHECK_IN_OFFSET_DAYS)
        check_out = check_in + timedelta(days=STAY_NIGHTS)

        section(f"Step 2: Hotel Search — {check_in} to {check_out}")
        with timed("indicative_search"):
            search_results = await hotel_api.indicative_search(
                entity_id=entity_id,
                check_in=check_in,
                check_out=check_out,
                currency=CURRENCY,
                search_type=search_type,
            )

        if not search_results:
            logger.error("No hotels found. Aborting.")
            return

        logger.info("  Found %d hotels", len(search_results))
        for sr in search_results[:TOP_N]:
            price_str = f"${sr.price.gross_amount:.0f}" if sr.price else "N/A"
            score_str = f"{sr.review_score:.1f}" if sr.review_score else "N/A"
            logger.info("  %-12s %-40s  %8s  score=%s", sr.hotel_id, sr.name[:40], price_str, score_str)
            logger.debug(
                "  [detail] hotel_id=%s class=%s country=%s checkin=%s",
                sr.hotel_id, sr.property_class, sr.country_code, sr.checkin_date,
            )

        if len(search_results) > TOP_N:
            logger.info("  ... and %d more", len(search_results) - TOP_N)

        # Limit to top N to avoid rate limits on content/reviews
        search_results = search_results[:TOP_N]
        hotel_ids = [h.hotel_id for h in search_results]
        logger.info("  Processing top %d hotels", len(hotel_ids))

        # ── Step 3: Content Fetch ───────────────────────────────────
        section("Step 3: Fetch Hotel Content")
        with timed("get_content"):
            contents = await hotel_api.get_content(hotel_ids)

        logger.info("  Content returned for %d / %d hotels", len(contents), len(hotel_ids))
        for c in contents:
            desc_preview = (c.description or "")[:120].replace("\n", " ")
            logger.info(
                "  %-12s %-30s  stars=%-4s  guest=%-4s  amenities=%d",
                c.hotel_id, c.name[:30], c.star_rating or "?", c.guest_rating or "?", len(c.amenities),
            )
            logger.debug("  [desc] %s...", desc_preview)
            logger.debug("  [amenities] %s", c.amenities[:15])

        # ── Step 4: Descriptions + Reviews Fetch (parallel) ─────────
        section("Step 4: Fetch Descriptions & Reviews")
        descriptions_by_hotel: dict[str, str | None] = {}
        reviews_by_hotel: dict[str, list] = {}
        with timed("get_descriptions_and_reviews"):
            desc_tasks = [hotel_api.get_description(hid) for hid in hotel_ids]
            review_tasks = [hotel_api.get_reviews(hid, limit=MAX_REVIEWS) for hid in hotel_ids]
            all_results = await asyncio.gather(
                *desc_tasks, *review_tasks, return_exceptions=True,
            )
            desc_results = all_results[:len(hotel_ids)]
            review_results = all_results[len(hotel_ids):]

            for hid, result in zip(hotel_ids, desc_results):
                if isinstance(result, BaseException):
                    logger.warning("  Description failed for %s: %s", hid, result)
                    descriptions_by_hotel[hid] = None
                else:
                    descriptions_by_hotel[hid] = result

            for hid, result in zip(hotel_ids, review_results):
                if isinstance(result, BaseException):
                    logger.warning("  Reviews failed for %s: %s", hid, result)
                    reviews_by_hotel[hid] = []
                else:
                    reviews_by_hotel[hid] = result

        logger.info("  Descriptions:")
        for hid, desc in descriptions_by_hotel.items():
            preview = (desc or "")[:120].replace("\n", " ")
            logger.info("  %-12s  %s", hid, f"{preview}..." if desc else "(none)")

        logger.info("  Reviews:")
        for hid, revs in reviews_by_hotel.items():
            logger.info("  %-12s  %d reviews", hid, len(revs))
            if revs:
                first = revs[0]
                preview = (first.content or "")[:100].replace("\n", " ")
                logger.debug("  [first review] rating=%.1f  %s...", first.rating or 0, preview)

        # ── Step 5: Assemble Hotels ─────────────────────────────────
        section("Step 5: Assemble Hotel Domain Models")
        hotels = ranking_service._build_hotels(search_results, contents, descriptions_by_hotel, reviews_by_hotel)
        logger.info("  Assembled %d Hotel objects", len(hotels))

        missing_desc = [h for h in hotels if not h.description]
        missing_reviews = [h for h in hotels if not h.reviews]
        if missing_desc:
            logger.warning("  %d hotels have no description: %s", len(missing_desc), [h.hotel_id for h in missing_desc])
        if missing_reviews:
            logger.warning("  %d hotels have no reviews: %s", len(missing_reviews), [h.hotel_id for h in missing_reviews])

        for h in hotels:
            logger.debug(
                "  [hotel] %s | price=%s | rating=%s | amenities=%d | reviews=%d",
                h.name[:40], h.price, h.guest_rating, len(h.amenities), len(h.reviews),
            )

        # ── Step 6: Build Text Blobs ────────────────────────────────
        section("Step 6: Build Text Blobs for Embedding")
        blobs = embedding_service.build_text_blobs(hotels)
        logger.info("  Built %d text blobs", len(blobs))

        for hotel, blob in zip(hotels, blobs):
            logger.info("  %-30s  blob_len=%d chars", hotel.name[:30], len(blob))
            logger.debug("  [blob preview] %s...", blob[:200].replace("\n", " "))

        # ── Step 7: Embed ───────────────────────────────────────────
        section(f"Step 7: Embed Vibe Query + {len(blobs)} Hotel Blobs")
        logger.info("  Vibe query: '%s'", VIBE_QUERY)

        with timed("embedding"):
            query_vec, hotel_vecs = await embedding_service.embed_query_and_hotels(VIBE_QUERY, blobs)

        logger.info("  Query vector: %d dimensions", len(query_vec))
        logger.info("  Hotel vectors: %d x %d dimensions", len(hotel_vecs), len(hotel_vecs[0]) if hotel_vecs else 0)
        logger.debug("  Query vector sample: %s", query_vec[:5])

        # ── Step 8: Cosine Similarity ───────────────────────────────
        section("Step 8: Compute Cosine Similarity")
        similarities = similarity_service.compute_similarity(query_vec, hotel_vecs)

        for hotel, sim in zip(hotels, similarities):
            logger.info("  %-40s  similarity=%.4f", hotel.name[:40], sim)

        # ── Step 9: Composite Scoring ───────────────────────────────
        section(f"Step 9: Composite Scoring (w_vibe={VIBE_WEIGHT}, w_price={PRICE_WEIGHT}, w_rating={RATING_WEIGHT})")
        scored = ranking_service._score_and_rank(hotels, similarities)

        for s in scored:
            logger.info(
                "  %-35s  vibe=%.4f  price=%.4f  rating=%.4f  COMPOSITE=%.4f",
                s.hotel.name[:35], s.vibe_similarity, s.price_score, s.guest_rating_score, s.composite_score,
            )

        # ── Step 10: Final Ranking ──────────────────────────────────
        section(f"Step 10: Final Ranking — Top {TOP_N}")
        for rank, s in enumerate(scored[:TOP_N], 1):
            price_str = f"${s.hotel.price:.0f}" if s.hotel.price else "N/A"
            logger.info(
                "  #%-2d  %-35s  %8s  composite=%.4f",
                rank, s.hotel.name[:35], price_str, s.composite_score,
            )
            logger.info(
                "       vibe=%.4f  price_score=%.4f  rating_score=%.4f  guest_rating=%s",
                s.vibe_similarity, s.price_score, s.guest_rating_score, s.hotel.guest_rating,
            )

        # ── Summary ─────────────────────────────────────────────────
        total_time = time.perf_counter() - pipeline_start
        section("Summary")
        logger.info("  Destination:     %s (entity=%s)", DESTINATION, entity_id)
        logger.info("  Vibe:            %s", VIBE_QUERY)
        logger.info("  Dates:           %s → %s", check_in, check_out)
        logger.info("  Hotels searched: %d", len(search_results))
        logger.info("  Hotels ranked:   %d", len(scored))
        logger.info("  Total time:      %.2fs", total_time)
        logger.info("  Log file:        %s", log_file)

    finally:
        await connector.close()


if __name__ == "__main__":
    asyncio.run(main())
