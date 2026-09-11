from pydantic import BaseModel
from datetime import datetime


class BookingCreate(BaseModel):
    slot_id: int
    produce_type: str | None = None


class BookingOut(BaseModel):
    booking_id: int
    farmer_id: int
    slot_id: int
    status: str
    booking_time: datetime
    produce_type: str | None = None
