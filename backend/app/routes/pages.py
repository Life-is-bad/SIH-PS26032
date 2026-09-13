import os
import io
import qrcode
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse

from app.auth_utils import (
    hash_password, verify_password, create_access_token,
    get_current_user_from_cookie,
)
from app.models.models import create_user, get_user_by_phone, get_user_by_id
from app.models.slots import list_upcoming_slots, create_slot, delete_slot
from app.models.bookings import (
    create_booking, get_farmer_bookings, cancel_booking,
    get_bookings_for_counter, get_booking_details, get_booking_by_token,
)
from app.models.queue import (
    get_live_queue, update_queue_status, check_in_booking, get_farmer_queue_status,
)
from app.models.counters import list_counters

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
        "booking_success": "Booking confirmed!",
        "live_queue": "Live queue",
        "slots_nav": "Slots",
        "add_slot": "Add a new slot",
        "awaiting_checkin": "Today's bookings — awaiting check-in",
        "live_queue_heading": "Live queue — Counter {counter}",
        "manage_slots": "Manage slots",
        "col_date": "Date",
        "col_time": "Time",
        "col_booked": "Booked",
        "no_upcoming_slots": "No upcoming slots for this counter.",
        "col_farmer": "Farmer",
        "col_produce": "Produce",
        "col_slot": "Slot",
        "col_status": "Status",
        "col_actions": "Actions",
        "no_one_waiting": "No one in queue right now.",
        "check_in_btn": "Check in",
        "counter_label": "Counter",
        "date_label": "Date",
        "start_time_label": "Start time",
        "end_time_label": "End time",
        "capacity_label": "Capacity",
        "add_slot_btn": "Add slot",
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
        "booking_success": "बुकिंग की पुष्टि हुई!",
        "live_queue": "लाइव कतार",
        "slots_nav": "स्लॉट",
        "add_slot": "नया स्लॉट जोड़ें",
        "awaiting_checkin": "आज की बुकिंग — चेक-इन की प्रतीक्षा में",
        "live_queue_heading": "लाइव कतार — काउंटर {counter}",
        "manage_slots": "स्लॉट प्रबंधित करें",
        "col_date": "तारीख",
        "col_time": "समय",
        "col_booked": "बुक किया गया",
        "no_upcoming_slots": "इस काउंटर के लिए कोई आगामी स्लॉट नहीं है।",
        "col_farmer": "किसान",
        "col_produce": "उपज",
        "col_slot": "स्लॉट",
        "col_status": "स्थिति",
        "col_actions": "कार्रवाई",
        "no_one_waiting": "अभी कतार में कोई नहीं है।",
        "check_in_btn": "चेक इन करें",
        "counter_label": "केंद्र",
        "date_label": "तारीख",
        "start_time_label": "प्रारंभ समय",
        "end_time_label": "समाप्ति समय",
        "capacity_label": "क्षमता",
        "add_slot_btn": "स्लॉट जोड़ें",
    },
}


def get_lang(request: Request) -> str:
    return request.cookies.get("lang", "en")


def require_page_user(request: Request, role: str, with_name: bool = False):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != role:
        return None, RedirectResponse("/login")
    if with_name:
        full_user = get_user_by_id(int(user["sub"]))
        user["full_name"] = full_user["full_name"] if full_user else None
    return user, None


def get_translations(request: Request, lang: str | None = None):
    current_lang = lang or get_lang(request)
    return current_lang, TRANSLATIONS[current_lang]


def apply_lang_cookie(response, lang: str | None):
    if lang:
        response.set_cookie("lang", lang, max_age=31536000)
    return response

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
    user, redirect = require_page_user(request, "farmer", with_name=True)
    if redirect:
        return redirect

    bookings = get_farmer_bookings(int(user["sub"]))
    completed = [b for b in bookings if b["status"] == "completed"]
    cancelled = [b for b in bookings if b["status"] == "cancelled"]
    current_lang, t = get_translations(request, lang)

    response = templates.TemplateResponse(
        request, "farmer_bookings.html",
        {
            "user": user, "completed": completed, "cancelled": cancelled,
            "active_page": "bookings", "lang": current_lang, "t": t,
        },
    )
    return apply_lang_cookie(response, lang)


@router.get("/farmer", response_class=HTMLResponse)
def farmer_page(request: Request, counter_id: int | None = None, lang: str | None = None):
    user, redirect = require_page_user(request, "farmer", with_name=True)
    if redirect:
        return redirect

    counters = list_counters()
    if counter_id is None and counters:
        counter_id = counters[0]["counter_id"]

    selected_counter = next((c for c in counters if c["counter_id"] == counter_id), None)
    slots = list_upcoming_slots(counter_id=counter_id) if counter_id else []
    bookings = get_farmer_bookings(int(user["sub"]))
    current_lang, t = get_translations(request, lang)

    response = templates.TemplateResponse(
        request, "farmer.html",
        {
            "user": user, "slots": slots, "bookings": bookings,
            "active_page": "book", "counters": counters,
            "selected_counter": selected_counter, "counter_id": counter_id,
            "lang": current_lang, "t": t,
        },
    )
    return apply_lang_cookie(response, lang)


@router.post("/farmer/book/{slot_id}")
def farmer_book(request: Request, slot_id: int, produce_type: str = Form(None)):
    user, redirect = require_page_user(request, "farmer", with_name=True)
    if redirect:
        return redirect

    result = create_booking(int(user["sub"]), slot_id, produce_type=produce_type or None)
    if "error" in result:
        counters = list_counters()
        counter_id = request.query_params.get("counter_id")
        counter_id = int(counter_id) if counter_id else (counters[0]["counter_id"] if counters else None)
        selected_counter = next((c for c in counters if c["counter_id"] == counter_id), None)
        slots = list_upcoming_slots(counter_id=counter_id) if counter_id else []
        bookings = get_farmer_bookings(int(user["sub"]))
        current_lang, t = get_translations(request)
        return templates.TemplateResponse(
            request, "farmer.html",
            {
                "user": user, "slots": slots, "bookings": bookings, "error": result["detail"],
                "counters": counters, "selected_counter": selected_counter, "counter_id": counter_id,
                "active_page": "book", "t": t, "lang": current_lang,
            },
        )
    booking_id = result["booking"]["booking_id"]
    return RedirectResponse(f"/farmer/booking/{booking_id}/confirmation", status_code=303)


@router.delete("/farmer/cancel/{booking_id}", response_class=HTMLResponse)
def farmer_cancel(request: Request, booking_id: int):
    user, redirect = require_page_user(request, "farmer")
    if redirect:
        return redirect
    cancel_booking(booking_id, int(user["sub"]))
    bookings = get_farmer_bookings(int(user["sub"]))
    _, t = get_translations(request)
    return templates.TemplateResponse(
        request, "partials/booking_list.html", {"bookings": bookings, "t": t}
    )


@router.get("/farmer/bookings-partial", response_class=HTMLResponse)
def farmer_bookings_partial(request: Request):
    user, redirect = require_page_user(request, "farmer")
    if redirect:
        return redirect
    bookings = get_farmer_bookings(int(user["sub"]))
    _, t = get_translations(request)
    return templates.TemplateResponse(
        request, "partials/booking_list.html", {"bookings": bookings, "t": t}
    )


@router.get("/farmer/booking/{booking_id}/confirmation", response_class=HTMLResponse)
def farmer_confirmation(request: Request, booking_id: int):
    user, redirect = require_page_user(request, "farmer")
    if redirect:
        return redirect
    booking = get_booking_details(booking_id, int(user["sub"]))
    if booking is None:
        return RedirectResponse("/farmer")
    return templates.TemplateResponse(
        request, "farmer_confirmation.html", {"user": user, "booking": booking},
    )


@router.get("/farmer/booking/{booking_id}/qr.png")
def farmer_booking_qr(request: Request, booking_id: int):
    user, redirect = require_page_user(request, "farmer")
    if redirect:
        return redirect
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
    user, redirect = require_page_user(request, "farmer", with_name=True)
    if redirect:
        return redirect
    status = get_farmer_queue_status(int(user["sub"]))
    current_lang, t = get_translations(request, lang)
    response = templates.TemplateResponse(
        request, "farmer_queue.html",
        {"user": user, "status": status, "active_page": "queue", "lang": current_lang, "t": t},
    )
    return apply_lang_cookie(response, lang)


@router.get("/officer/scan/{token}", response_class=HTMLResponse)
def officer_scan(request: Request, token: str):
    user, redirect = require_page_user(request, "officer")
    if redirect:
        return redirect
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
def officer_page(request: Request, counter_id: int = 1, lang: str | None = None):
    user = get_current_user_from_cookie(request)
    if user is None or user["role"] != "officer":
        return RedirectResponse("/login")
    full_user = get_user_by_id(int(user["sub"]))
    user["full_name"] = full_user["full_name"] if full_user else None
    queue = get_live_queue(counter_id)
    counters = list_counters()
    pending = get_bookings_for_counter(counter_id)
    slots = list_upcoming_slots(counter_id=counter_id)

    current_lang = lang or get_lang(request)
    t = TRANSLATIONS[current_lang]

    response = templates.TemplateResponse(
        request, "officer.html",
        {
            "user": user, "queue": queue, "counter_id": counter_id,
            "counters": counters, "pending": pending, "slots": slots,
            "active_page": "queue", "lang": current_lang, "t": t,
        },
    )
    if lang:
        response.set_cookie("lang", lang, max_age=31536000)
    return response


@router.get("/officer/queue-partial", response_class=HTMLResponse)
def officer_queue_partial(request: Request, counter_id: int = 1):
    queue = get_live_queue(counter_id)
    t = TRANSLATIONS[get_lang(request)]
    return templates.TemplateResponse(
        request, "partials/queue_table.html", {"queue": queue, "t": t}
    )


@router.patch("/officer/status/{queue_id}/{new_status}", response_class=HTMLResponse)
def officer_update_status(request: Request, queue_id: int, new_status: str, counter_id: int = 1):
    user, redirect = require_page_user(request, "officer")
    if redirect:
        return redirect
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
    user, redirect = require_page_user(request, "officer")
    if redirect:
        return redirect
    create_slot(counter_id, slot_date, start_time, end_time, capacity, int(user["sub"]))
    return RedirectResponse(f"/officer?counter_id={counter_id}", status_code=303)


@router.post("/officer/checkin/{booking_id}", response_class=HTMLResponse)
def officer_checkin(request: Request, booking_id: int, counter_id: int = 1):
    user, redirect = require_page_user(request, "officer")
    if redirect:
        return redirect
    check_in_booking(booking_id, int(user["sub"]))
    queue = get_live_queue(counter_id)
    pending = get_bookings_for_counter(counter_id)
    return templates.TemplateResponse(
        request, "partials/officer_panels.html",
        {"pending": pending, "queue": queue, "counter_id": counter_id},
    )


@router.delete("/officer/slots/{slot_id}", response_class=HTMLResponse)
def officer_delete_slot(request: Request, slot_id: int, counter_id: int = 1):
    user, redirect = require_page_user(request, "officer")
    if redirect:
        return redirect
    result = delete_slot(slot_id)
    error = result["detail"] if "error" in result else None
    slots = list_upcoming_slots(counter_id)
    return templates.TemplateResponse(
        request, "partials/slot_manage_list.html",
        {"slots": slots, "counter_id": counter_id, "error": error},
    )
