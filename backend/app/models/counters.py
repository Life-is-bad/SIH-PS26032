import math
from app.database import get_connection

def list_counters():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT counter_id, counter_name, location_desc FROM counters WHERE is_active = TRUE")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

from app.database import get_connection

def list_counters():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT counter_id, counter_name, location_desc FROM counters WHERE is_active = TRUE")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def list_counters_with_distance(user_lat: float | None = None, user_lng: float | None = None):
    counters = list_counters()
    if user_lat is None or user_lng is None:
        return counters

    for c in counters:
        if c["latitude"] is not None and c["longitude"] is not None:
            c["distance_km"] = _haversine(user_lat, user_lng, float(c["latitude"]), float(c["longitude"]))
        else:
            c["distance_km"] = None

    return sorted(counters, key=lambda c: (c["distance_km"] is None, c["distance_km"]))


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)
