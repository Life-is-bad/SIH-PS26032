import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DATABASE_URL_HOST"),
    "port": int(os.getenv("DATABASE_URL_PORT", 3306)),
    "user": os.getenv("DATABASE_URL_USER"),
    "password": os.getenv("DATABASE_URL_PASSWORD"),
    "database": os.getenv("DATABASE_URL_NAME"),
}


def get_connection():
    """Returns a fresh MySQL connection. Caller is responsible for closing it."""
    return mysql.connector.connect(**DB_CONFIG)


def test_connection():
    try:
        conn = get_connection()
        conn.close()
        return True, None
    except Error as e:
        return False, str(e)
