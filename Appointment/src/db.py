import sqlite3
from pathlib import Path
import os

APP_NAME = "TerminSystem"

def get_app_data_dir():
    """
    返回用户可写的数据目录
    Windows: %APPDATA%\\TerminSystem
    """
    base = Path(os.environ.get("APPDATA", Path.home()))
    data_dir = base / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


DB_FILE = get_app_data_dir() / "termins.db"


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS termins (
            id TEXT PRIMARY KEY,
            date TEXT,
            planned_time TEXT,
            patient TEXT,
            status TEXT,
            arrival_time TEXT,
            leave_time TEXT,
            services TEXT,
            invoice_sent TEXT
        )
        """)
