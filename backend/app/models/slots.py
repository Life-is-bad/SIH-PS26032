from app.database import get_connection
from mysql.connector import Error

def create_slot(counter_id: int, slot_date, start_time, end_time, capacity: int, created_by: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO slots (counter_id, slot_date, start_time, end_time, capacity, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (counter_id, slot_date, start_time, end_time, capacity, created_by),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def list_slots(slot_date=None, counter_id: int | None = None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT * FROM slots WHERE 1=1"
        params = []
        if slot_date:
            query += " AND slot_date = %s"
            params.append(slot_date)
        if counter_id:
            query += " AND counter_id = %s"
            params.append(counter_id)
        query += " ORDER BY slot_date, start_time"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def get_slot(slot_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM slots WHERE slot_id = %s", (slot_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def list_upcoming_slots(counter_id: int | None = None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT * FROM slots WHERE slot_date >= CURDATE()"
        params = []
        if counter_id:
            query += " AND counter_id = %s"
            params.append(counter_id)
        query += " ORDER BY slot_date, start_time"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def delete_slot(slot_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM slots WHERE slot_id = %s", (slot_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": "not_found", "detail": "Slot does not exist"}
        return {"deleted": True}
    except Error as e:
        conn.rollback()
        if e.errno == 1451:
            return {"error": "has_bookings", "detail": "Cannot delete a slot that has existing bookings"}
        raise
    finally:
        cursor.close()
        conn.close()
