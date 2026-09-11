from fastapi import APIRouter, Depends, HTTPException
from app.schemas.queue import CheckInRequest, QueueStatusUpdate
from app.models.queue import (
    check_in_booking,
    get_my_queue_status,
    get_live_queue,
    update_queue_status,
)
from app.auth_utils import require_role

router = APIRouter(prefix="/queue", tags=["queue"])


@router.post("/checkin", status_code=201)
def checkin(payload: CheckInRequest, current_user: dict = Depends(require_role("officer"))):
    result = check_in_booking(payload.booking_id, int(current_user["sub"]))
    if "error" in result:
        status_map = {"not_found": 404, "invalid_state": 400, "duplicate": 409}
        raise HTTPException(status_code=status_map.get(result["error"], 400), detail=result["detail"])
    return result["queue_status"]


@router.get("/mine")
def my_queue_status(current_user: dict = Depends(require_role("farmer"))):
    result = get_my_queue_status(int(current_user["sub"]))
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["detail"])
    return result


@router.get("/live")
def live_queue(counter_id: int, current_user: dict = Depends(require_role("officer"))):
    return get_live_queue(counter_id)


@router.patch("/{queue_id}/status")
def set_status(queue_id: int, payload: QueueStatusUpdate, current_user: dict = Depends(require_role("officer"))):
    result = update_queue_status(queue_id, payload.status)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return result["queue_status"]
