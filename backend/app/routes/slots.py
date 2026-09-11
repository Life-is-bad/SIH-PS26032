from fastapi import APIRouter, Depends
from app.schemas.slots import SlotCreate
from app.models.slots import create_slot, list_slots
from app.auth_utils import require_role, get_current_user
from datetime import date as date_type

router = APIRouter(prefix="/slots", tags=["slots"])


@router.post("/", status_code=201)
def add_slot(payload: SlotCreate, current_user: dict = Depends(require_role("officer"))):
    slot_id = create_slot(
        counter_id=payload.counter_id,
        slot_date=payload.slot_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        capacity=payload.capacity,
        created_by=int(current_user["sub"]),
    )
    return {"slot_id": slot_id}


@router.get("/")
def get_slots(
    slot_date: date_type | None = None,
    counter_id: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    return list_slots(slot_date=slot_date, counter_id=counter_id)
