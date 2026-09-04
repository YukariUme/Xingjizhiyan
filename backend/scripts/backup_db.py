"""SQLite 数据库备份：复制主库 + 知识文件目录，保留最近 N 份。

用法：python -m scripts.backup_db [备份目录]
"""

import shutil
import sys
import time
from pathlib import Path

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    db_url = settings.database_url
    if not db_url.startswith("sqlite:///"):
        print("当前数据库不是 SQLite，无需此备份脚本。")
        return
    db_path = Path(db_url.replace("sqlite:///", "", 1))
    backup_root = Path(sys.argv[1]) if len(sys.argv) > 1 else db_path.parent / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = backup_root / f"jbgs_{stamp}"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, target / "jbgs.db")
    kb = Path(settings.knowledge_files_dir)
    if kb.exists():
        shutil.copytree(kb, target / "knowledge_files", dirs_exist_ok=True)
    # 只保留最近 10 份
    backups = sorted(backup_root.glob("jbgs_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[10:]:
        shutil.rmtree(old, ignore_errors=True)
    print(f"备份完成：{target}")


if __name__ == "__main__":
    main()
