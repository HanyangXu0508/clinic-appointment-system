import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta


from termin import (
    get_termins,
    add_termin,
    update_termin,
    delete_termin,
    parse_services,
    export_termins_to_csv
)

# ----------------- 常量 -----------------
HOURS = [f"{i:02d}" for i in range(24)]
MINS = [f"{i:02d}" for i in range(60)]
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


# ----------------- 工具 -----------------
def valid_date_ddmmyyyy(s: str) -> bool:
    try:
        datetime.strptime(s, "%d-%m-%Y")
        return True
    except ValueError:
        return False


def valid_date_yyyymmdd(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def weekday_cn_from_iso(iso_date: str) -> str:
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
        return WEEKDAY_CN[d.weekday()]
    except Exception:
        return ""


def date_de_from_iso(iso_date: str) -> str:
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return ""


def normalize_services_text(s: str) -> str:
    s = (s or "").replace("，", ";").replace(",", ";")
    parts = [x.strip() for x in s.split(";") if x.strip()]
    return ";".join(parts)


def services_str_to_display(s: str) -> str:
    return ", ".join(parse_services(s or ""))


# ----------------- 时间选择控件 -----------------
class TimePicker(ttk.Frame):
    def __init__(self, master, initial="00:00"):
        super().__init__(master)
        self.h = tk.StringVar()
        self.m = tk.StringVar()

        self.cb_h = ttk.Combobox(self, values=HOURS, width=3, state="readonly", textvariable=self.h)
        self.cb_m = ttk.Combobox(self, values=MINS, width=3, state="readonly", textvariable=self.m)

        self.cb_h.grid(row=0, column=0, padx=(0, 6))
        ttk.Label(self, text=":").grid(row=0, column=1)
        self.cb_m.grid(row=0, column=2, padx=(6, 0))

        self.set_time(initial)

    def set_enabled(self, enabled: bool):
        state = "readonly" if enabled else "disabled"
        self.cb_h.configure(state=state)
        self.cb_m.configure(state=state)

    def set_time(self, t: str):
        try:
            hh, mm = (t or "00:00").split(":")
        except Exception:
            hh, mm = "00", "00"
        self.h.set(hh if hh in HOURS else "00")
        self.m.set(mm if mm in MINS else "00")

    def get_time(self) -> str:
        return f"{self.h.get()}:{self.m.get()}"


# ================= 主窗口 =================
class TerminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Termin System")
        self.geometry("1200x650")
        self.minsize(1050, 580)

        self.range_var = tk.StringVar(value="today")
        self.status_var = tk.StringVar(value="all")
        self.invoice_var = tk.StringVar(value="all")
        self.name_search_var = tk.StringVar()   # ← 明确：姓名搜索

        self._style()
        self._build_ui()
        self.refresh()

    def _style(self):
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def export_csv(self):
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            title="导出为 CSV",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")]
        )

        if not path:
            return

        try:
            export_termins_to_csv(path)
            messagebox.showinfo("导出成功", f"已成功导出到：\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="范围").pack(side="left")
        for t, v in [("今天", "today"), ("本月", "month"), ("全部", "all")]:
            ttk.Radiobutton(top, text=t, value=v, variable=self.range_var,
                            command=self.refresh).pack(side="left", padx=6)

        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Label(top, text="状态").pack(side="left")
        for t, v in [("全部", "all"), ("到达", "arrived"), ("未到", "scheduled")]:
            ttk.Radiobutton(top, text=t, value=v, variable=self.status_var,
                            command=self.refresh).pack(side="left", padx=6)

        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Label(top, text="账单").pack(side="left")
        for t, v in [("全部", "all"), ("已发送", "yes"), ("未发送", "no")]:
            ttk.Radiobutton(top, text=t, value=v, variable=self.invoice_var,
                            command=self.refresh).pack(side="left", padx=6)

        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=12)

        ttk.Label(top, text="搜索（姓名）").pack(side="left")
        ttk.Entry(top, textvariable=self.name_search_var, width=22).pack(side="left", padx=8)
        ttk.Button(top, text="应用", command=self.refresh).pack(side="left")


        # 表格
        self.columns = (
            "planned", "weekday", "date_de", "patient", "arrived",
            "range", "services", "invoice", "edit", "delete"
        )
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=8)

        headers = {
            "planned": "预约时间",
            "weekday": "星期",
            "date_de": "日期",
            "patient": "姓名",
            "arrived": "到达",
            "range": "到达-离开",
            "services": "项目",
            "invoice": "账单",
            "edit": "",
            "delete": ""
        }
        widths = {
            "planned": 90, "weekday": 80, "date_de": 110, "patient": 140,
            "arrived": 70, "range": 160, "services": 320,
            "invoice": 70, "edit": 45, "delete": 45
        }
        for c in self.columns:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor="center")

        self.tree.bind("<Button-1>", self.on_click)

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="➕ 新建预约",
                   command=lambda: NewTerminDialog(self)).pack(side="left")
        ttk.Button(bottom, text="🗓 今日时间表",
                   command=lambda: TodayTimelineDialog(self)).pack(side="left", padx=10)
        ttk.Button(bottom, text="🗓 本周时间表",
                   command=lambda: WeekTimelineDialog(self)).pack(side="left", padx=10)
        ttk.Button(
            bottom,
            text="📤 导出 CSV",
            command=self.export_csv
        ).pack(side="right")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())

        today = date.today().strftime("%Y-%m-%d")
        df = dt = None
        if self.range_var.get() == "today":
            df = dt = today
        elif self.range_var.get() == "month":
            df = today[:7] + "-01"
            dt = today[:7] + "-31"

        status = None if self.status_var.get() == "all" else self.status_var.get()
        invoice = None if self.invoice_var.get() == "all" else self.invoice_var.get()

        rows = get_termins(date_from=df, date_to=dt, status=status)
        rows.sort(key=lambda r: (r["date"], r["planned_time"]))

        name_kw = self.name_search_var.get().strip()

        for r in rows:
            if name_kw and name_kw not in r["patient"]:
                continue
            if invoice and r.get("invoice_sent", "no") != invoice:
                continue

            self.tree.insert(
                "", "end", iid=r["id"],
                values=(
                    r["planned_time"],
                    weekday_cn_from_iso(r["date"]),
                    date_de_from_iso(r["date"]),
                    r["patient"],
                    "☑" if r["status"] == "arrived" else "☐",
                    f"{r['arrival_time']}–{r['leave_time']}" if r["arrival_time"] else "",
                    services_str_to_display(r.get("services", "")),
                    "☑" if r.get("invoice_sent") == "yes" else "☐",
                    "修改🖊",
                    "删除🗑"
                )
            )

    def on_click(self, event):
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row_id:
            return

        idx = int(col[1:]) - 1
        if idx == self.columns.index("arrived"):
            ArrivalDialog(self, row_id)
        elif idx == self.columns.index("edit"):
            EditDialog(self, row_id)
        elif idx == self.columns.index("delete"):
            if messagebox.askyesno("确认删除", "确定删除这条 Termin 吗？"):
                delete_termin(row_id)
                self.refresh()

# ================= 本周时间表窗口 =================
class WeekTimelineDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("本周时间表")
        self.geometry("1000x800")

        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", self.redraw)

    def redraw(self, event=None):
        c = self.canvas
        c.delete("all")

        width = c.winfo_width()
        height = c.winfo_height()
        if width < 100:
            return

        # ---------- 本周范围 ----------
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        week_days = [monday + timedelta(days=i) for i in range(7)]

        rows = get_termins(
            date_from=monday.strftime("%Y-%m-%d"),
            date_to=(monday + timedelta(days=6)).strftime("%Y-%m-%d")
        )

        # ---------- 布局参数 ----------
        hour_height = 34
        top_pad = 40
        axis_w = 80
        col_gap = 6

        left = axis_w + 10
        right = width - 20
        usable_w = right - left
        col_w = (usable_w - col_gap * 6) / 7

        # ---------- 星期标题 ----------
        for i, d in enumerate(week_days):
            x = left + i * (col_w + col_gap) + col_w / 2
            label = f"{WEEKDAY_CN[d.weekday()]}\n{d.strftime('%m-%d')}"
            c.create_text(
                x, 16,
                text=label,
                font=("Segoe UI", 10, "bold"),
                fill="#333",
                justify="center"
            )

        # ---------- 每日列背景 + 竖线 ----------
        for i in range(7):
            x1 = left + i * (col_w + col_gap)
            x2 = x1 + col_w

            # 淡背景（可选，增强列感）
            c.create_rectangle(
                x1, top_pad,
                x2, top_pad + 24 * hour_height,
                fill="#fafafa",
                outline=""
            )

            # 竖分隔线
            c.create_line(
                x1, top_pad,
                x1, top_pad + 24 * hour_height,
                fill="#ddd"
            )

        # 最右侧边界线
        c.create_line(
            right, top_pad,
            right, top_pad + 24 * hour_height,
            fill="#ddd"
        )

        # ---------- 时间轴 ----------
        for h in range(24):
            y = top_pad + h * hour_height

            c.create_text(
                axis_w - 6, y,
                text=f"{h:02d}:00",
                anchor="e",
                font=("Segoe UI", 9),
                fill="#555"
            )

            c.create_line(left, y, right, y, fill="#eee")



        # ---------- 预约块 ----------
        for r in rows:
            d = datetime.strptime(r["date"], "%Y-%m-%d").date()
            day_idx = (d - monday).days
            if not (0 <= day_idx <= 6):
                continue

            if r["arrival_time"] and r["leave_time"]:
                start = r["arrival_time"]
                end = r["leave_time"]
            else:
                start = r["planned_time"]
                t = datetime.strptime(start, "%H:%M") + timedelta(minutes=90)
                end = t.strftime("%H:%M")

            sh, sm = map(int, start.split(":"))
            eh, em = map(int, end.split(":"))

            y1 = top_pad + sh * hour_height + (sm / 60) * hour_height
            y2 = top_pad + eh * hour_height + (em / 60) * hour_height

            x1 = left + day_idx * (col_w + col_gap)
            x2 = x1 + col_w

            c.create_rectangle(
                x1, y1, x2, y2,
                fill="#cce5ff",
                outline="#4a90e2"
            )

            pad_x = 6
            pad_y = 6
            line_h = 16

            # 姓名（主信息）
            c.create_text(
                x1 + pad_x,
                y1 + pad_y,
                text=r["patient"],
                anchor="nw",
                font=("Segoe UI", 9, "bold"),
                fill="#000"
            )

            # 时间（次信息）
            c.create_text(
                x1 + pad_x,
                y1 + pad_y + line_h,
                text=f"{start}–{end}",
                anchor="nw",
                font=("Segoe UI", 9),
                fill="#333"
            )

            # ---------- 今日红线（仅当在本周） ----------
            now = datetime.now()
            if monday <= now.date() <= monday + timedelta(days=6):
                day_idx = (now.date() - monday).days
                x1 = left + day_idx * (col_w + col_gap)
                x2 = x1 + col_w
                y = top_pad + now.hour * hour_height + (now.minute / 60) * hour_height

                c.create_line(x1, y, x2, y, fill="#d9534f", width=2)




# ================= 今日时间表窗口 =================
import tkinter as tk
from datetime import datetime, date, timedelta

class TodayTimelineDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("今日时间表")
        self.geometry("700x800")

        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # 绑定 resize / 首次显示
        self.canvas.bind("<Configure>", self.redraw)

    def redraw(self, event=None):
        canvas = self.canvas
        canvas.delete("all")  # 关键：重画

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 50:  # 防止初始化时 width=1
            return

        today = date.today().strftime("%Y-%m-%d")
        rows = [r for r in get_termins(date_from=today, date_to=today)]

        hour_height = 34
        axis_w = 90
        top_pad = 20

        left = axis_w + 20
        right = width - 20

        # ===== 时间轴 =====
        for h in range(24):
            y = top_pad + h * hour_height

            canvas.create_text(
                axis_w, y,
                text=f"{h:02d}:00",
                anchor="e",
                fill="#333",
                font=("Segoe UI", 10, "bold")
            )

            canvas.create_line(left, y, right, y, fill="#eee")



        # ===== 预约块 =====
        for r in rows:
            if r["arrival_time"] and r["leave_time"]:
                start = r["arrival_time"]
                end = r["leave_time"]
            else:
                start = r["planned_time"]
                t = datetime.strptime(start, "%H:%M") + timedelta(minutes=90)
                end = t.strftime("%H:%M")

            sh, sm = map(int, start.split(":"))
            eh, em = map(int, end.split(":"))

            y1 = top_pad + sh * hour_height + (sm / 60) * hour_height
            y2 = top_pad + eh * hour_height + (em / 60) * hour_height

            canvas.create_rectangle(
                left, y1, right - 20, y2,
                fill="#cce5ff",
                outline="#4a90e2"
            )

            canvas.create_text(
                left + 8,
                (y1 + y2) / 2,
                text=f"{r['patient']}  {start}-{end}",
                anchor="w",
                font=("Segoe UI", 10)
            )

            # ===== 当前时间红线 =====
            now = datetime.now()
            now_y = (
                    top_pad
                    + now.hour * hour_height
                    + (now.minute / 60) * hour_height
            )

            canvas.create_line(
                left, now_y, right - 20, now_y,
                fill="#d9534f", width=2
            )


# ----------------- 新建预约 -----------------
class NewTerminDialog(tk.Toplevel):
    def __init__(self, parent: TerminApp):
        super().__init__(parent)
        self.parent = parent
        self.title("新建预约")
        self.geometry("420x260")
        self.resizable(False, False)

        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="姓名").grid(row=0, column=0, sticky="w", pady=8)
        self.patient = ttk.Entry(frm, width=30)
        self.patient.grid(row=0, column=1, sticky="ew", pady=8)

        ttk.Label(frm, text="日期（DD-MM-YYYY）").grid(row=1, column=0, sticky="w", pady=8)
        self.date = ttk.Entry(frm, width=30)
        self.date.grid(row=1, column=1, sticky="ew", pady=8)

        ttk.Label(frm, text="预约时间").grid(row=2, column=0, sticky="w", pady=8)
        self.time_picker = TimePicker(frm, initial="00:00")
        self.time_picker.grid(row=2, column=1, sticky="w", pady=8)

        frm.columnconfigure(1, weight=1)

        btns = ttk.Frame(self, padding=10)
        btns.pack(fill="x")
        ttk.Button(btns, text="取消", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="创建", command=self.save).pack(side="right", padx=10)

    def save(self):
        name = self.patient.get().strip()
        d = self.date.get().strip()

        if not name:
            messagebox.showerror("错误", "姓名不能为空")
            return

        if not valid_date_ddmmyyyy(d):
            messagebox.showerror("错误", "日期格式错误，应为 DD-MM-YYYY（例如 25-12-2025）")
            return

        planned = self.time_picker.get_time()
        ok, msg = add_termin(name, d, planned)
        if not ok:
            messagebox.showerror("错误", msg)
            return

        self.parent.refresh()
        self.destroy()


# ----------------- 到达登记（复选框驱动） -----------------
class ArrivalDialog(tk.Toplevel):
    def __init__(self, parent: TerminApp, tid: str):
        super().__init__(parent)
        self.parent = parent
        self.tid = tid
        self.title("到达登记")
        self.geometry("460x300")
        self.resizable(False, False)

        self.original = next(r for r in get_termins() if r["id"] == tid)

        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="both", expand=True)

        self.arrived_var = tk.BooleanVar(value=(self.original["status"] == "arrived"))

        ttk.Checkbutton(
            frm, text="是否到达",
            variable=self.arrived_var,
            command=self._toggle
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=10)

        ttk.Label(frm, text="到达时间").grid(row=1, column=0, sticky="w", pady=8)
        self.arrival_picker = TimePicker(frm, initial=self.original.get("arrival_time") or "00:00")
        self.arrival_picker.grid(row=1, column=1, sticky="w", pady=8)

        ttk.Label(frm, text="离开时间").grid(row=2, column=0, sticky="w", pady=8)
        self.leave_picker = TimePicker(frm, initial=self.original.get("leave_time") or "00:00")
        self.leave_picker.grid(row=2, column=1, sticky="w", pady=8)

        ttk.Label(frm, text="项目（; 分隔）").grid(row=3, column=0, sticky="w", pady=8)
        self.services = ttk.Entry(frm, width=40)
        self.services.insert(0, self.original.get("services", ""))
        self.services.grid(row=3, column=1, sticky="ew", pady=8)

        frm.columnconfigure(1, weight=1)

        btns = ttk.Frame(self, padding=10)
        btns.pack(fill="x")
        ttk.Button(btns, text="取消", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="保存", command=self.save).pack(side="right", padx=10)

        self._toggle()

    def _toggle(self):
        on = self.arrived_var.get()
        self.arrival_picker.set_enabled(on)
        self.leave_picker.set_enabled(on)
        self.services.configure(state="normal" if on else "disabled")

    def save(self):
        if self.arrived_var.get():
            services_norm = normalize_services_text(self.services.get())
            update_termin(
                self.tid,
                arrival_time=self.arrival_picker.get_time(),
                leave_time=self.leave_picker.get_time(),
                services=[x for x in services_norm.split(";") if x]
            )
        else:
            update_termin(self.tid, arrival_time="", leave_time="", services=[])

        self.parent.refresh()
        self.destroy()


# ----------------- 编辑 Termin（全字段 + 默认不改） -----------------
class EditDialog(tk.Toplevel):
    def __init__(self, parent: TerminApp, tid: str):
        super().__init__(parent)
        self.parent = parent
        self.tid = tid
        self.title("编辑 Termin")
        self.geometry("520x440")
        self.resizable(False, False)

        self.original = next(r for r in get_termins() if r["id"] == tid)

        frm = ttk.Frame(self, padding=14)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="姓名").grid(row=0, column=0, sticky="w", pady=8)
        self.patient = ttk.Entry(frm, width=40)
        self.patient.insert(0, self.original.get("patient", ""))
        self.patient.grid(row=0, column=1, sticky="ew", pady=8)

        ttk.Label(frm, text="日期（YYYY-MM-DD）").grid(row=1, column=0, sticky="w", pady=8)
        self.date = ttk.Entry(frm, width=40)
        self.date.insert(0, self.original.get("date", ""))
        self.date.grid(row=1, column=1, sticky="ew", pady=8)

        ttk.Label(frm, text="预约时间").grid(row=2, column=0, sticky="w", pady=8)
        self.planned_picker = TimePicker(frm, initial=self.original.get("planned_time") or "00:00")
        self.planned_picker.grid(row=2, column=1, sticky="w", pady=8)

        ttk.Label(frm, text="到达时间").grid(row=3, column=0, sticky="w", pady=8)
        self.arrival_picker = TimePicker(frm, initial=self.original.get("arrival_time") or "00:00")
        self.arrival_picker.grid(row=3, column=1, sticky="w", pady=8)

        ttk.Label(frm, text="离开时间").grid(row=4, column=0, sticky="w", pady=8)
        self.leave_picker = TimePicker(frm, initial=self.original.get("leave_time") or "00:00")
        self.leave_picker.grid(row=4, column=1, sticky="w", pady=8)

        ttk.Label(frm, text="项目（; 分隔）").grid(row=5, column=0, sticky="w", pady=8)
        self.services = ttk.Entry(frm, width=40)
        self.services.insert(0, self.original.get("services", ""))
        self.services.grid(row=5, column=1, sticky="ew", pady=8)

        self.invoice_var = tk.BooleanVar(value=(self.original.get("invoice_sent", "no") == "yes"))
        ttk.Checkbutton(frm, text="已发送账单", variable=self.invoice_var)\
            .grid(row=6, column=1, sticky="w", pady=10)

        frm.columnconfigure(1, weight=1)

        btns = ttk.Frame(self, padding=10)
        btns.pack(fill="x")
        ttk.Button(btns, text="取消", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="保存修改", command=self.save).pack(side="right", padx=10)

    def save(self):
        updates = {}

        new_patient = self.patient.get().strip()
        if new_patient and new_patient != self.original.get("patient", ""):
            updates["patient"] = new_patient

        new_date = self.date.get().strip()
        if new_date != self.original.get("date", ""):
            if not valid_date_yyyymmdd(new_date):
                messagebox.showerror("错误", "日期必须是 YYYY-MM-DD（例如 2025-12-25）")
                return
            updates["date"] = new_date

        new_planned = self.planned_picker.get_time()
        if new_planned != self.original.get("planned_time", ""):
            updates["planned_time"] = new_planned

        # 到达/离开：允许单独修改；若原来为空，只有当你不是 00:00 才写入
        new_arrival = self.arrival_picker.get_time()
        old_arrival = self.original.get("arrival_time", "")
        if old_arrival:
            if new_arrival != old_arrival:
                updates["arrival_time"] = new_arrival
        else:
            if new_arrival != "00:00":
                updates["arrival_time"] = new_arrival

        new_leave = self.leave_picker.get_time()
        old_leave = self.original.get("leave_time", "")
        if old_leave:
            if new_leave != old_leave:
                updates["leave_time"] = new_leave
        else:
            if new_leave != "00:00":
                updates["leave_time"] = new_leave

        new_services_norm = normalize_services_text(self.services.get())
        if new_services_norm != self.original.get("services", ""):
            updates["services"] = [x for x in new_services_norm.split(";") if x]

        new_invoice = "yes" if self.invoice_var.get() else "no"
        if new_invoice != self.original.get("invoice_sent", "no"):
            updates["invoice_sent"] = new_invoice

        if updates:
            ok, msg = update_termin(self.tid, **updates)
            if not ok:
                messagebox.showerror("错误", msg)
                return

        self.parent.refresh()
        self.destroy()


if __name__ == "__main__":
    TerminApp().mainloop()
