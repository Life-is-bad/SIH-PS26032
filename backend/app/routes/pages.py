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
from app.models.queue import check_in_booking, get_farmer_queue_status
from app.models.slots import list_upcoming_slots, delete_slot
from app.models.bookings import (
    create_booking, get_farmer_bookings, cancel_booking,
    get_bookings_for_counter, get_booking_details, get_booking_by_token,
)
from app.models.models import get_user_by_id

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")
TRANSLATIONS = {
    "en": {
        "book_title": "Book your slot",
        "greeting": "Namaste, {name} — choose a center and time that works for you",
        "available_slots": "Available slots",
        "your_bookings": "Your bookings",
        "no_bookings": "No active bookings.",
        "book_a_slot": "Book a slot",
        "my_bookings": "My bookings",
        "select_slot": "Select a slot to book",
        "booking_details": "Booking details",
        "select_prompt": "Select a slot on the left to see details here.",
        "slot_label": "Slot",
        "center_label": "Center",
        "produce_label": "What are you bringing?",
        "produce_placeholder": "e.g. Wheat",
        "token_pending": "Token pending",
        "cancel": "Cancel",
        "view_qr": "View QR",
        "booked_on": "Booked",
        "no_smartphone": "No smartphone? No problem",
        "no_smartphone_body": "Visit the center directly — you'll still get SMS/voice updates on your queue position.",
        "km_away": "km away",
        "completed": "Completed",
        "cancelled": "Cancelled",
        "no_completed": "No completed bookings yet.",
        "no_cancelled": "No cancelled bookings.",
        "live_queue": "Live queue",
        "your_token": "Your token",
        "farmers_ahead": "farmers ahead of you",
        "minutes_wait": "minutes estimated wait",
        "booking_confirmed": "Booking confirmed",
        "checked_in_gate": "Checked in at gate",
        "qr_scanned": "QR scanned",
        "not_checked_in": "Not checked in yet",
        "waiting_in_queue": "Waiting in queue",
        "position_label": "Position",
        "of_label": "of",
        "in_service": "In service",
        "no_active_booking": "No active booking. Book a slot to see your queue status.",
    },
    "hi": {
        "book_title": "अपना स्लॉट बुक करें",
        "greeting": "नमस्ते, {name} — अपने लिए सही केंद्र और समय चुनें",
        "available_slots": "उपलब्ध स्लॉट",
        "your_bookings": "आपकी बुकिंग",
        "no_bookings": "कोई सक्रिय बुकिंग नहीं।",
        "book_a_slot": "स्लॉट बुक करें",
        "my_bookings": "मेरी बुकिंग",
        "select_slot": "बुक करने के लिए एक स्लॉट चुनें",
        "booking_details": "बुकिंग विवरण",
        "select_prompt": "विवरण देखने के लिए बाईं ओर एक स्लॉट चुनें।",
        "slot_label": "स्लॉट",
        "center_label": "केंद्र",
        "produce_label": "आप क्या ला रहे हैं?",
        "produce_placeholder": "उदा. गेहूं",
        "token_pending": "टोकन प्रतीक्षित",
        "view_qr": "क्यूआर कोड देखें",
        "cancel": "रद्द करें",
        "booked_on": "बुक किया गया",
        "no_smartphone": "स्मार्टफोन नहीं? कोई बात नहीं",
        "no_smartphone_body": "सीधे केंद्र पर जाएं — आपको अपनी कतार की स्थिति की SMS/वॉइस अपडेट फिर भी मिलेगी।",
        "km_away": "किमी दूर",
        "completed": "पूर्ण",
        "cancelled": "रद्द",
        "no_completed": "अभी तक कोई पूर्ण बुकिंग नहीं।",
        "no_cancelled": "कोई रद्द बुकिंग नहीं।",
        "live_queue": "लाइव कतार",
        "your_token": "आपका टोकन",
        "farmers_ahead": "किसान आपसे आगे",
        "minutes_wait": "मिनट अनुमानित प्रतीक्षा",
        "booking_confirmed": "बुकिंग की पुष्टि हुई",
        "checked_in_gate": "गेट पर चेक-इन हुआ",
        "qr_scanned": "क्यूआर स्कैन किया गया",
        "not_checked_in": "अभी तक चेक-इन नहीं हुआ",
        "waiting_in_queue": "कतार में प्रतीक्षारत",
        "position_label": "स्थान",
        "of_label": "में से",
        "in_service": "सेवा में",
        "no_active_booking": "कोई सक्रिय बुकिंग नहीं। अपनी कतार की स्थिति देखने के लिए एक स्लॉट बुक करें।",
    },
}


def get_lang(request: Request) -> str:
    return request.cookies.get("lang", "en")

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


@router.get("/farmer/bookings", response_class=HTMLResponse)
def farmer_bookings_page(request: Request, lang: str | None = None):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    full_user = get_user_by_id(int(user["sub"]))
    user["full_name"] = full_user["full_name"] if full_user else None

    bookings = get_farmer_bookings(int(user["sub"]))
    completed = [b for b in bookings if b["status"] == "completed"]
    cancelled = [b for b in bookings if b["status"] == "cancelled"]

    current_lang = lang or get_lang(request)
    t = TRANSLATIONS[current_lang]

    response = templates.TemplateResponse(
        request, "farmer_bookings.html",
        {
            "user": user, "completed": completed, "cancelled": cancelled,
            "active_page": "bookings", "lang": current_lang, "t": t,
        },
    )
    if lang:
        response.set_cookie("lang", lang, max_age=31536000)
    return response


@router.get("/farmer", response_class=HTMLResponse)
def farmer_page(request: Request, counter_id: int | None = None, lang: str | None = None):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    full_user = get_user_by_id(int(user["sub"]))
    user["full_name"] = full_user["full_name"] if full_user else None

    counters = list_counters()
    if counter_id is None and counters:
        counter_id = counters[0]["counter_id"]

    selected_counter = next((c for c in counters if c["counter_id"] == counter_id), None)
    slots = list_upcoming_slots(counter_id=counter_id) if counter_id else []
    bookings = get_farmer_bookings(int(user["sub"]))

    current_lang = lang or get_lang(request)
    t = TRANSLATIONS[current_lang]

    response = templates.TemplateResponse(
        request, "farmer.html",
        {
            "user": user, "slots": slots, "bookings": bookings,
            "active_page": "book", "counters": counters,
            "selected_counter": selected_counter, "counter_id": counter_id,
            "lang": current_lang, "t": t,
        },
    )
    if lang:
        response.set_cookie("lang", lang, max_age=31536000)
    return response


@router.post("/farmer/book/{slot_id}")
def farmer_book(request: Request, slot_id: int, produce_type: str = Form(None)):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    result = create_booking(int(user["sub"]), slot_id, produce_type=produce_type or None)
    if "error" in result:
        counters = list_counters()
        slots = list_upcoming_slots()
        bookings = get_farmer_bookings(int(user["sub"]))
        t = TRANSLATIONS[get_lang(request)]
        return templates.TemplateResponse(
            request, "farmer.html",
            {"user": user, "slots": slots, "bookings": bookings, "error": result["detail"], "counters": counters, "t": t, "lang": get_lang(request)},
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
    t = TRANSLATIONS[get_lang(request)]
    return templates.TemplateResponse(
        request, "partials/booking_list.html", {"bookings": bookings, "t": t}
    )


@router.get("/farmer/bookings-partial", response_class=HTMLResponse)
def farmer_bookings_partial(request: Request):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    bookings = get_farmer_bookings(int(user["sub"]))
    return templates.TemplateResponse(
        request, "partials/booking_list.html", {"bookings": bookings, "t": TRANSLATIONS[get_lang(request)]}
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


@router.get("/farmer/queue", response_class=HTMLResponse)
def farmer_queue_page(request: Request, lang: str | None = None):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "farmer":
        return RedirectResponse("/login")
    full_user = get_user_by_id(int(user["sub"]))
    user["full_name"] = full_user["full_name"] if full_user else None

    status = get_farmer_queue_status(int(user["sub"]))

    current_lang = lang or get_lang(request)
    t = TRANSLATIONS[current_lang]

    response = templates.TemplateResponse(
        request, "farmer_queue.html",
        {"user": user, "status": status, "active_page": "queue", "lang": current_lang, "t": t},
    )
    if lang:
        response.set_cookie("lang", lang, max_age=31536000)
    return response


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
    full_user = get_user_by_id(int(user["sub"]))
    user["full_name"] = full_user["full_name"] if full_user else None
    queue = get_live_queue(counter_id)
    counters = list_counters()
    pending = get_bookings_for_counter(counter_id)
    return templates.TemplateResponse(
        request, "officer.html",
        {"user": user, "queue": queue, "counter_id": counter_id, "counters": counters, "pending": pending, "active_page": "queue"},
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
