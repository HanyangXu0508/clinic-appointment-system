import uuid
from datetime import datetime
from db import get_conn, init_db
import csv
from pathlib import Path

# 确保数据库和表存在
init_db()


# ----------------- 工具 -----------------
def _now_id():
    return uuid.uuid4().hex

def parse_services(s: str):
    """
    数据库存的是用 ; 分隔的字符串
    UI 需要的是 list[str]
    """
    if not s:
        return []
    return [x.strip() for x in s.split(";") if x.strip()]

def _normalize_services(services):
    """
    UI 里传进来的是 list[str]
    数据库存成用 ; 连接的字符串
    """
    if not services:
        return ""
    if isinstance(services, list):
        return ";".join(x.strip() for x in services if x.strip())
    return str(services)


# ----------------- 核心接口（保持不变） -----------------

def get_termins(date_from=None, date_to=None, status=None):
    sql = "SELECT * FROM termins WHERE 1=1"
    params = []

    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)
    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY date, planned_time"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [dict(r) for r in rows]


def add_termin(patient, date_ddmmyyyy, planned_time):
    try:
        date_iso = datetime.strptime(date_ddmmyyyy, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return False, "日期格式错误，应为 DD-MM-YYYY"

    tid = _now_id()

    with get_conn() as conn:
        conn.execute("""
        INSERT INTO termins (
            id, date, planned_time, patient,
            status, arrival_time, leave_time,
            services, invoice_sent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tid,
            date_iso,
            planned_time,
            patient,
            "scheduled",
            "",
            "",
            "",
            "no"
        ))

    return True, "创建成功"


def update_termin(
    tid,
    patient=None,
    date=None,
    planned_time=None,
    arrival_time=None,
    leave_time=None,
    services=None,
    invoice_sent=None
):
    fields = []
    params = []

    if patient is not None:
        fields.append("patient = ?")
        params.append(patient)

    if date is not None:
        fields.append("date = ?")
        params.append(date)

    if planned_time is not None:
        fields.append("planned_time = ?")
        params.append(planned_time)

    if arrival_time is not None:
        fields.append("arrival_time = ?")
        params.append(arrival_time)
        fields.append("status = ?")
        params.append("arrived" if arrival_time else "scheduled")

    if leave_time is not None:
        fields.append("leave_time = ?")
        params.append(leave_time)

    if services is not None:
        fields.append("services = ?")
        params.append(_normalize_services(services))

    if invoice_sent is not None:
        fields.append("invoice_sent = ?")
        params.append(invoice_sent)

    if not fields:
        return True, "无修改"

    sql = "UPDATE termins SET " + ", ".join(fields) + " WHERE id = ?"
    params.append(tid)

    with get_conn() as conn:
        conn.execute(sql, params)

    return True, "更新成功"


def delete_termin(tid):
    with get_conn() as conn:
        conn.execute("DELETE FROM termins WHERE id = ?", (tid,))

def export_termins_to_csv(csv_path: str):
    """
    将当前 SQLite 中的 termins 表导出为 CSV
    """
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM termins ORDER BY date, planned_time").fetchall()

    if not rows:
        raise RuntimeError("当前没有任何数据可导出")

    csv_path = Path(csv_path)

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        # 表头
        writer.writerow(rows[0].keys())

        # 数据行
        for r in rows:
            writer.writerow(list(r))
