from app.database import get_connection


def create_user(role: str, full_name: str, phone_number: str, password_hash: str, email: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (role, full_name, phone_number, email, password_hash)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (role, full_name, phone_number, email, password_hash),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def get_user_by_phone(phone_number: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)  # dictionary=True gives {column: value} instead of tuples
    try:
        cursor.execute(
            "SELECT * FROM users WHERE phone_number = %s",
            (phone_number,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def get_user_by_id(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM users WHERE user_id = %s",
            (user_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
