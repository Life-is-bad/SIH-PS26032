import secrets
from app.database import get_connection
from mysql.connector import Error


def create_booking(farmer_id: int, slot_id: int, produce_type: str | None):
    conn = get_connection()
    try:
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM slots WHERE slot_id = %s FOR UPDATE",
            (slot_id,),
        )
        slot = cursor.fetchone()

        if slot is None:
            conn.rollback()
            return {"error": "not_found", "detail": "Slot does not exist"}

        if slot["booked_count"] >= slot["capacity"]:
            conn.rollback()
            return {"error": "full", "detail": "This slot is fully booked"}

        token = secrets.token_urlsafe(24)

        try:
            cursor.execute(
                """
                INSERT INTO bookings (farmer_id, slot_id, produce_type, qr_token)
                VALUES (%s, %s, %s, %s)
                """,
                (farmer_id, slot_id, produce_type, token),
            )
        except Error as e:
            conn.rollback()
            if "uq_bookings_active" in str(e):
                return {"error": "duplicate", "detail": "You already have an active booking for this slot"}
            raise

        booking_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,))
        return {"booking": cursor.fetchone()}
    finally:
        cursor.close()
        conn.close()


def get_farmer_bookings(farmer_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT b.*, qs.check_in_status AS queue_status
            FROM bookings b
            LEFT JOIN queue_status qs ON qs.booking_id = b.booking_id
            WHERE b.farmer_id = %s
            ORDER BY b.booking_time DESC
            """,
            (farmer_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def cancel_booking(booking_id: int, farmer_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM bookings WHERE booking_id = %s",
            (booking_id,),
        )
        booking = cursor.fetchone()

        if booking is None:
            return {"error": "not_found"}
        if booking["farmer_id"] != farmer_id:
            return {"error": "forbidden"}
        if booking["status"] != "booked":
            return {"error": "invalid_state", "detail": f"Booking is already {booking['status']}"}

        cursor.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE booking_id = %s",
            (booking_id,),
        )
        conn.commit()
        return {"success": True}
    finally:
        cursor.close()
        conn.close()


def get_bookings_for_counter(counter_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT b.booking_id, b.produce_type, b.status,
                   u.full_name AS farmer_name,
                   s.start_time, s.end_time
            FROM bookings b
            JOIN slots s ON s.slot_id = b.slot_id
            JOIN users u ON u.user_id = b.farmer_id
            LEFT JOIN queue_status qs ON qs.booking_id = b.booking_id
            WHERE s.counter_id = %s
              AND b.status = 'booked'
              AND qs.queue_id IS NULL
            ORDER BY s.start_time
            """,
            (counter_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def get_booking_details(booking_id: int, farmer_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT b.booking_id, b.produce_type, b.status, b.qr_token,
                   s.slot_date, s.start_time, s.end_time,
                   c.counter_id, c.counter_name, c.location_desc
            FROM bookings b
            JOIN slots s ON s.slot_id = b.slot_id
            JOIN counters c ON c.counter_id = s.counter_id
            WHERE b.booking_id = %s AND b.farmer_id = %s
            """,
            (booking_id, farmer_id),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def get_booking_by_token(token: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT b.booking_id, b.produce_type, b.status,
                   u.full_name AS farmer_name,
                   s.start_time, s.end_time, s.counter_id
            FROM bookings b
            JOIN users u ON u.user_id = b.farmer_id
            JOIN slots s ON s.slot_id = b.slot_id
            WHERE b.qr_token = %s
            """,
            (token,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
