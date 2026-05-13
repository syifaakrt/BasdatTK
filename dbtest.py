from db import get_connection

try:
    conn = get_connection()
    print("✅ Koneksi berhasil!")
    conn.close()
except Exception as e:
    print(f"❌ Gagal: {e}")