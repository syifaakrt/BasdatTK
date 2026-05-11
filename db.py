import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    
    cur = conn.cursor()
    cur.execute("SET search_path TO aeromiles, public;")
    conn.commit()
    cur.close()
    
    return conn