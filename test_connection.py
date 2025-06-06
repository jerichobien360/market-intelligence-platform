# test_connection.py
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

try:
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    # Connect to database
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # Test query
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✅ Database connection successful!")
    print(f"PostgreSQL version: {version[0]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Database connection failed: {e}")
