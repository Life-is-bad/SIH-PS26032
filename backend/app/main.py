from fastapi import FastAPI, Depends
from app.database import test_connection
from app.routes import auth
from app.auth_utils import get_current_user, require_role
from app.routes import slots, bookings
from app.routes import slots, bookings, queue
from fastapi.staticfiles import StaticFiles
from app.routes import pages

app = FastAPI(title="Farmer Slot Booking & Queue Management — PS 26032")

app.include_router(auth.router)
app.include_router(slots.router)
app.include_router(bookings.router)
app.include_router(queue.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages.router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "API is running"}

@app.get("/db-check")
def db_check():
    connected, error = test_connection()
    if connected:
        return {"database": "connected"}
    return {"database": "error", "detail": error}

@app.get("/whoami")
def whoami(current_user: dict = Depends(get_current_user)):
    return current_user

@app.get("/officer-only-test")
def officer_only(current_user: dict = Depends(require_role("officer"))):
    return {"message": "You're an officer, access granted"}
