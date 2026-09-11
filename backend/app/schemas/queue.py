from pydantic import BaseModel
from typing import Literal

QueueStatusLiteral = Literal["waiting", "in_service", "served", "no_show"]


class CheckInRequest(BaseModel):
    booking_id: int


class QueueStatusUpdate(BaseModel):
    status: QueueStatusLiteral
