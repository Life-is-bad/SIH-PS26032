from fastapi import APIRouter, Depends, HTTPException
from app.schemas.bookings import BookingCreate
from app.models.bookings import create_booking, get_farmer_bookings, cancel_booking
from app.auth_utils import require_role, get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", status_code=201)
def book_slot(payload: BookingCreate, current_user: dict = Depends(require_role("farmer"))):
    farmer_id = int(current_user["sub"])
    result = create_booking(farmer_id, payload.slot_id, payload.produce_type)

    if "error" in result:
        status_map = {"not_found": 404, "full": 409, "duplicate": 409}
        raise HTTPException(
            status_code=status_map.get(result["error"], 400),
            detail=result["detail"],
        )
    return result["booking"]


@router.get("/me")
def my_bookings(current_user: dict = Depends(require_role("farmer"))):
    return get_farmer_bookings(int(current_user["sub"]))


@router.delete("/{booking_id}")
def cancel(booking_id: int, current_user: dict = Depends(require_role("farmer"))):
    result = cancel_booking(booking_id, int(current_user["sub"]))

    if "error" in result:
        status_map = {"not_found": 404, "forbidden": 403, "invalid_state": 400}
        raise HTTPException(status_code=status_map.get(result["error"], 400), detail=result.get("detail", ""))
    return {"message": "Booking cancelled"}
