import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")  # Neon connection string from .env

def get_connection():
    try:
        conn = psycopg2.connect(DB_URL)
        print("✅ Connected successfully to Neon PostgreSQL!")
        return conn
    except Exception as e:
        print("❌ Database connection failed:", e)
        return None
