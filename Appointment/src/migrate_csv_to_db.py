import csv
from db import get_conn, init_db
from pathlib import Path

CSV_FILE = Path(__file__).resolve().parent.parent / "data" / "termins.csv"

init_db()

with get_conn() as conn, open(CSV_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        conn.execute("""
        INSERT OR REPLACE INTO termins
        VALUES (:id, :date, :planned_time, :patient,
                :status, :arrival_time, :leave_time,
                :services, :invoice_sent)
        """, r)

print("✅ CSV → SQLite 迁移完成")
