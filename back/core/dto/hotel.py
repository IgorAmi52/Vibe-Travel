from pydantic import BaseModel

from back.core.models.hotel import ScoredHotel


class HotelRankingRequest(BaseModel):
    vibe_query: str
    destination: str
    check_in: str
    check_out: str
    guests: int = 2
    rooms: int = 1


class HotelRankingResponse(BaseModel):
    destination: str
    entity_id: str
    hotels: list[ScoredHotel]
