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
