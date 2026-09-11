from fastapi import APIRouter, Depends
from app.schemas.slots import SlotCreate
from app.models.slots import create_slot, list_slots
from app.auth_utils import require_role, get_current_user
from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException
from app.models.slots import create_slot, list_slots, delete_slot

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

@router.delete("/{slot_id}")
def remove_slot(slot_id: int, current_user: dict = Depends(require_role("officer"))):
    result = delete_slot(slot_id)
    if "error" in result:
        status_map = {"has_bookings": 409, "not_found": 404}
        raise HTTPException(status_code=status_map[result["error"]], detail=result["detail"])
    return {"deleted": True}
