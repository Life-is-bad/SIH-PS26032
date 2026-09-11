from app.database import get_connection
from mysql.connector import Error

AVG_MINUTES_PER_FARMER = 5  # simple heuristic — replace with a real average later


def check_in_booking(booking_id: int, officer_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM bookings WHERE booking_id = %s",
            (booking_id,),
        )
        booking = cursor.fetchone()

        if booking is None:
            return {"error": "not_found", "detail": "Booking does not exist"}
        if booking["status"] != "booked":
            return {"error": "invalid_state", "detail": f"Booking is {booking['status']}, not active"}

        try:
            cursor.execute(
                """
                INSERT INTO queue_status (booking_id, check_in_status, checked_in_at, checked_in_by)
                VALUES (%s, 'waiting', NOW(), %s)
                """,
                (booking_id, officer_id),
            )
            conn.commit()
        except Error as e:
            conn.rollback()
            if "uq_queue_booking" in str(e):
                return {"error": "duplicate", "detail": "This booking is already checked in"}
            raise

        cursor.execute("SELECT * FROM queue_status WHERE booking_id = %s", (booking_id,))
        return {"queue_status": cursor.fetchone()}
    finally:
        cursor.close()
        conn.close()


def get_my_queue_status(farmer_id: int):
    """
    Finds the farmer's active checked-in booking today, and computes
    live position + estimated wait among others waiting at the same counter.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT qs.*, b.slot_id, s.counter_id
            FROM queue_status qs
            JOIN bookings b ON b.booking_id = qs.booking_id
            JOIN slots s ON s.slot_id = b.slot_id
            WHERE b.farmer_id = %s AND qs.check_in_status = 'waiting'
            ORDER BY qs.checked_in_at DESC
            LIMIT 1
            """,
            (farmer_id,),
        )
        mine = cursor.fetchone()
        if mine is None:
            return {"error": "not_found", "detail": "No active checked-in booking found"}

        # count how many at the same counter checked in earlier and are still waiting
        cursor.execute(
            """
            SELECT COUNT(*) AS ahead
            FROM queue_status qs
            JOIN bookings b ON b.booking_id = qs.booking_id
            JOIN slots s ON s.slot_id = b.slot_id
            WHERE s.counter_id = %s
              AND qs.check_in_status = 'waiting'
              AND qs.checked_in_at < %s
            """,
            (mine["counter_id"], mine["checked_in_at"]),
        )
        ahead = cursor.fetchone()["ahead"]

        return {
            "queue_id": mine["queue_id"],
            "booking_id": mine["booking_id"],
            "check_in_status": mine["check_in_status"],
            "position": ahead + 1,
            "ahead_of_you": ahead,
            "estimated_wait_mins": ahead * AVG_MINUTES_PER_FARMER,
        }
    finally:
        cursor.close()
        conn.close()


def get_live_queue(counter_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT qs.queue_id, qs.check_in_status, qs.checked_in_at,
                   b.booking_id, b.produce_type,
                   u.full_name AS farmer_name, u.phone_number,
                   s.start_time, s.end_time
            FROM queue_status qs
            JOIN bookings b ON b.booking_id = qs.booking_id
            JOIN slots s ON s.slot_id = b.slot_id
            JOIN users u ON u.user_id = b.farmer_id
            WHERE s.counter_id = %s
              AND qs.check_in_status IN ('waiting', 'in_service')
            ORDER BY qs.checked_in_at ASC
            """,
            (counter_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def update_queue_status(queue_id: int, new_status: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM queue_status WHERE queue_id = %s", (queue_id,))
        row = cursor.fetchone()
        if row is None:
            return {"error": "not_found"}

        cursor.execute(
            "UPDATE queue_status SET check_in_status = %s WHERE queue_id = %s",
            (new_status, queue_id),
        )

        # if marking served/completed, also close out the booking
        if new_status == "served":
            cursor.execute(
                "UPDATE bookings SET status = 'completed' WHERE booking_id = %s",
                (row["booking_id"],),
            )

        conn.commit()
        cursor.execute("SELECT * FROM queue_status WHERE queue_id = %s", (queue_id,))
        return {"queue_status": cursor.fetchone()}
    finally:
        cursor.close()
        conn.close()
