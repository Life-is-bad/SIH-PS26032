from pydantic import BaseModel, Field
from datetime import date, time


class SlotCreate(BaseModel):
    counter_id: int
    slot_date: date
    start_time: time
    end_time: time
    capacity: int = Field(gt=0)


class SlotOut(BaseModel):
    slot_id: int
    counter_id: int
    slot_date: date
    start_time: time
    end_time: time
    capacity: int
    booked_count: int
