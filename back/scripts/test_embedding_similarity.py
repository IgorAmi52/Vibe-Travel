"""
Smoke test: embed vibe queries and hotel descriptions, then rank by cosine similarity.

Usage: GEMINI_API_KEY=... python -m scripts.test_embedding_similarity
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from clients.cosine_similarity_service import CosineSimilarityService
from clients.gemini_embed_provider import GeminiEmbedProvider

VIBE_QUERY = "quiet romantic beachfront with amazing sunsets"

HOTEL_DESCRIPTIONS = [
    {
        "name": "Sunset Cove Boutique Resort",
        "text": (
            "An intimate beachfront retreat nestled along a secluded coastline. "
            "Watch breathtaking sunsets from your private terrace. Couples love "
            "the candlelit dinners on the sand and the tranquil spa treatments. "
            "Amenities: private beach, spa, pool, fine dining, sunset lounge."
        ),
    },
    {
        "name": "Downtown Metro Hotel",
        "text": (
            "Modern business hotel in the heart of the financial district. "
            "Walking distance to convention centers and corporate offices. "
            "Features high-speed wifi, conference rooms, and a rooftop bar. "
            "Amenities: business center, gym, restaurant, concierge service."
        ),
    },
    {
        "name": "Paradise Beach Resort & Spa",
        "text": (
            "All-inclusive family resort on a white sand beach. Lively pool parties, "
            "kids club, water sports, and nightly entertainment shows. Great for "
            "families looking for fun in the sun. "
            "Amenities: waterpark, kids club, buffet, beach volleyball, nightclub."
        ),
    },
    {
        "name": "Cliffside Ocean Retreat",
        "text": (
            "Perched on dramatic sea cliffs with panoramic ocean views. "
            "A serene adults-only escape with infinity pools overlooking the water. "
            "Known for spectacular sunset views and peaceful atmosphere. "
            "Amenities: infinity pool, yoga deck, fine dining, couples spa, wine cellar."
        ),
    },
    {
        "name": "Alpine Mountain Lodge",
        "text": (
            "Cozy mountain lodge surrounded by pine forests and hiking trails. "
            "Perfect for adventurers seeking fresh air and nature escapes. "
            "Features a fireplace lounge, local cuisine, and guided treks. "
            "Amenities: ski-in/ski-out, sauna, hiking guides, mountain bikes."
        ),
    },
]


async def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY in .env or environment")
        sys.exit(1)

    embed_provider = GeminiEmbedProvider(api_key=api_key)
    similarity_service = CosineSimilarityService()

    all_texts = [VIBE_QUERY] + [h["text"] for h in HOTEL_DESCRIPTIONS]
    print(f"Embedding {len(all_texts)} texts via Gemini...\n")
    embeddings = await embed_provider.embed(all_texts)

    query_embedding = embeddings[0]
    hotel_embeddings = embeddings[1:]

    print(f"Embedding dimensions: {len(query_embedding)}")
    print(f"Vibe query: \"{VIBE_QUERY}\"\n")

    scores = similarity_service.compute_similarity(query_embedding, hotel_embeddings)

    ranked = sorted(
        zip(HOTEL_DESCRIPTIONS, scores), key=lambda x: x[1], reverse=True
    )

    print("=" * 60)
    print("RANKING RESULTS")
    print("=" * 60)
    for rank, (hotel, score) in enumerate(ranked, 1):
        print(f"\n#{rank}  {hotel['name']}")
        print(f"     Cosine similarity: {score:.4f}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
