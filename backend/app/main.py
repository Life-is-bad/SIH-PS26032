from fastapi import FastAPI
from app.database import test_connection

app = FastAPI(title="Farmer Slot Booking & Queue Management — PS 26032")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "API is running"}

@app.get("/db-check")
def db_check():
    connected, error = test_connection()
    if connected:
        return {"database": "connected"}
    return {"database": "error", "detail": error}
