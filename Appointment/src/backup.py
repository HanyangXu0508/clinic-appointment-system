import shutil
from pathlib import Path
from db import DB_FILE, init_db

def auto_backup():
    # ⭐ 先确保数据库和表存在
    init_db()

    if not DB_FILE.exists():
        return

    backup_dir = DB_FILE.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    backup_file = backup_dir / "termins_backup.db"
    shutil.copy2(DB_FILE, backup_file)