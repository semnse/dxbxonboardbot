"""Simple DB check"""
import psycopg2

print("Connecting to DB...")

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="onboarding_bot"
    )
    print("[OK] Connected!")
    
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM chat_bindings")
    count = cur.fetchone()[0]
    print(f"chat_bindings: {count} records")
    
    cur.close()
    conn.close()
    print("[OK] Done!")
    
except Exception as e:
    print(f"[ERROR] {e}")
