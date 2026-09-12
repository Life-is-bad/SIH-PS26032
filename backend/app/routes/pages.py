import os
import qrcode
import io
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from app.auth_utils import (
    hash_password, verify_password, create_access_token,
    get_current_user_from_cookie,
)
from app.models.models import create_user, get_user_by_phone
from app.models.slots import list_slots
from app.models.bookings import create_booking, get_farmer_bookings, cancel_booking
from app.models.queue import get_live_queue, update_queue_status
from datetime import date
from app.models.slots import list_upcoming_slots
from app.models.slots import create_slot
from app.models.counters import list_counters
from app.models.bookings import get_bookings_for_counter
from app.models.queue import check_in_booking
from app.models.slots import list_upcoming_slots, delete_slot
from app.models.bookings import (
    create_booking, get_farmer_bookings, cancel_booking,
    get_bookings_for_counter, get_booking_details, get_booking_by_token,
)

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = get_current_user_from_cookie(request)
    if user is None:
        return RedirectResponse("/login")
    if user["role"] == "farmer":
        return RedirectResponse("/farmer")
    return RedirectResponse("/officer?counter_id=1")


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse(request, "signup.html", {"user": None})


@router.post("/signup")
def signup_submit(
    request: Request,
    role: str = Form(...), full_name: str = Form(...),
    phone_number: str = Form(...), password: str = Form(...),
):
    if get_user_by_phone(phone_number):
        return templates.TemplateResponse(
            request, "signup.html",
            {"user": None, "error": "Phone number already registered"},
        )
    user_id = create_user(role, full_name, phone_number, hash_password(password))
    token = create_access_token(user_id, role)
    redirect_to = "/farmer" if role == "farmer" else "/officer?counter_id=1"
    response = RedirectResponse(redirect_to, status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=1800)
    return response


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"user": None})


@router.post("/login")
def login_submit(request: Request, phone_number: str = Form(...), password: str = Form(...)):
    user = get_user_by_phone(phone_number)
    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request, "login.html",
            {"user": None, "error": "Invalid phone number or password"},
        )
    token = create_access_token(user["user_id"], user["role"])
    redirect_to = "/farmer" if user["role"] == "farmer" else "/officer?counter_id=1"
    response = RedirectResponse(redirect_to, status_code=303)
    response.set_cookie("access_token", token, httponly=True, max_age=1800)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    return response


@router.get("/farmer", response_class=HTMLResponse)
def farmer_page(request: Request):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    farmer_id = int(user["sub"])
    slots = list_upcoming_slots()
    bookings = get_farmer_bookings(farmer_id)
    return templates.TemplateResponse(
        request, "farmer.html",
        {"user": user, "slots": slots, "bookings": bookings},
    )


@router.post("/farmer/book/{slot_id}")
def farmer_book(request: Request, slot_id: int, produce_type: str = Form(None)):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    result = create_booking(int(user["sub"]), slot_id, produce_type=produce_type or None)
    if "error" in result:
        slots = list_upcoming_slots()
        bookings = get_farmer_bookings(int(user["sub"]))
        return templates.TemplateResponse(
            request, "farmer.html",
            {"user": user, "slots": slots, "bookings": bookings, "error": result["detail"]},
        )
    booking_id = result["booking"]["booking_id"]
    return RedirectResponse(f"/farmer/booking/{booking_id}/confirmation", status_code=303)


@router.delete("/farmer/cancel/{booking_id}", response_class=HTMLResponse)
def farmer_cancel(request: Request, booking_id: int):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    cancel_booking(booking_id, int(user["sub"]))
    bookings = get_farmer_bookings(int(user["sub"]))
    return templates.TemplateResponse(
        request, "partials/booking_list.html", {"bookings": bookings}
    )


@router.get("/farmer/booking/{booking_id}/confirmation", response_class=HTMLResponse)
def farmer_confirmation(request: Request, booking_id: int):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    booking = get_booking_details(booking_id, int(user["sub"]))
    if booking is None:
        return RedirectResponse("/farmer")
    return templates.TemplateResponse(
        request, "farmer_confirmation.html", {"user": user, "booking": booking},
    )


@router.get("/farmer/booking/{booking_id}/qr.png")
def farmer_booking_qr(request: Request, booking_id: int):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    booking = get_booking_details(booking_id, int(user["sub"]))
    if booking is None or not booking["qr_token"]:
        return RedirectResponse("/farmer")
    base_url = os.getenv("PUBLIC_BASE_URL") or str(request.base_url).rstrip("/")
    scan_url = f"{base_url}/officer/scan/{booking['qr_token']}"
    img = qrcode.make(scan_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.get("/officer/scan/{token}", response_class=HTMLResponse)
def officer_scan(request: Request, token: str):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "officer":
        return RedirectResponse("/login")
    booking = get_booking_by_token(token)
    if booking is None:
        return templates.TemplateResponse(
            request, "officer_scan_result.html",
            {"user": user, "result": "invalid", "booking": None},
        )
    if booking["status"] != "booked":
        return templates.TemplateResponse(
            request, "officer_scan_result.html",
            {"user": user, "result": "invalid_state", "booking": booking},
        )
    outcome = check_in_booking(booking["booking_id"], int(user["sub"]))
    result = "duplicate" if "error" in outcome and outcome["error"] == "duplicate" else "checked_in"
    return templates.TemplateResponse(
        request, "officer_scan_result.html",
        {"user": user, "result": result, "booking": booking},
    )


@router.get("/officer", response_class=HTMLResponse)
def officer_page(request: Request, counter_id: int = 1):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "officer":
        return RedirectResponse("/login")
    queue = get_live_queue(counter_id)
    counters = list_counters()
    pending = get_bookings_for_counter(counter_id,)
    slots = list_upcoming_slots(counter_id)
    return templates.TemplateResponse(
        request, "officer.html",
        {"user": user, "queue": queue, "counter_id": counter_id, "counters": counters, "pending": pending, "slots": slots},
    )


@router.get("/officer/queue-partial", response_class=HTMLResponse)
def officer_queue_partial(request: Request, counter_id: int = 1):
    queue = get_live_queue(counter_id)
    return templates.TemplateResponse(
        request, "partials/queue_table.html", {"queue": queue}
    )


@router.patch("/officer/status/{queue_id}/{new_status}", response_class=HTMLResponse)
def officer_update_status(request: Request, queue_id: int, new_status: str, counter_id: int = 1):
    update_queue_status(queue_id, new_status)
    queue = get_live_queue(counter_id)
    return templates.TemplateResponse(
        request, "partials/queue_table.html", {"queue": queue}
    )

@router.post("/officer/slots/new")
def officer_add_slot(
    request: Request,
    counter_id: int = Form(...), slot_date: str = Form(...),
    start_time: str = Form(...), end_time: str = Form(...),
    capacity: int = Form(...),
):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "officer":
        return RedirectResponse("/login")
    create_slot(counter_id, slot_date, start_time, end_time, capacity, int(user["sub"]))
    return RedirectResponse(f"/officer?counter_id={counter_id}", status_code=303)

@router.post("/officer/checkin/{booking_id}", response_class=HTMLResponse)
def officer_checkin(request: Request, booking_id: int, counter_id: int = 1):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "officer":
        return RedirectResponse("/login")
    check_in_booking(booking_id, int(user["sub"]))
    queue = get_live_queue(counter_id)
    pending = get_bookings_for_counter(counter_id)
    return templates.TemplateResponse(
        request, "partials/officer_panels.html",
        {"pending": pending, "queue": queue, "counter_id": counter_id},
    )

@router.delete("/officer/slots/{slot_id}", response_class=HTMLResponse)
def officer_delete_slot(request: Request, slot_id: int, counter_id: int = 1):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "officer":
        return RedirectResponse("/login")
    result = delete_slot(slot_id)
    error = result["detail"] if "error" in result else None
    slots = list_upcoming_slots(counter_id)
    return templates.TemplateResponse(
        request, "partials/slot_manage_list.html",
        {"slots": slots, "counter_id": counter_id, "error": error},
    )
