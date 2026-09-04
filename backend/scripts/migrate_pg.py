"""SQLite → PostgreSQL 数据迁移脚本（保持 ORM 实体一致）。

用法：
    set DATABASE_URL=postgresql+psycopg://user:pass@host:5432/jbgs
    set SOURCE_SQLITE=sqlite:///D:/.../backend/data/jbgs.db
    python -m scripts.migrate_pg

说明：目标库先建表（init_db 会自动建），脚本按表逐行复制。
"""

import os
import sys
import json as _json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402


def _rows(engine, table: str):
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {table}"))
        columns = list(result.keys())
        for row in result:
            yield columns, dict(zip(columns, row))


def _target_types(engine, table: str) -> dict[str, str]:
    """查询目标表列类型，用于值规范化（bool/json/timestamp）。"""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_name = :t"
            ),
            {"t": table},
        )
        return {
            name: {"type": dtype, "nullable": nullable == "YES"}
            for name, dtype, nullable in rows
        }


def _normalize_value(name: str, value, meta: dict):
    """把 SQLite 值转换为 PG 可绑定类型。"""
    target_type = meta.get("type", "")
    if value is None:
        t = (target_type or "").lower()
        if meta.get("nullable", True):
            return None
        if t in ("json", "jsonb"):
            # PG 部分 JSON 列为 NOT NULL；按列名推断默认容器
            dict_like = {
                "metadata_json", "initial_state", "settings", "detail",
                "result_json", "state", "preferences", "flows", "extra",
            }
            from psycopg.types.json import Json

            return Json({} if name in dict_like else [])
        if t.startswith("boolean"):
            return False
        if t in ("integer", "bigint", "smallint"):
            return 0
        if t.startswith("double precision") or t.startswith("numeric") or t.startswith("real"):
            return 0.0
        return ""
    t = (target_type or "").lower()
    if t.startswith("boolean"):
        return bool(int(value))
    if t in ("json", "jsonb"):
        if isinstance(value, str):
            try:
                value = _json.loads(value)
            except Exception:  # noqa: BLE001 - 保留原文
                value = {"raw": value}
        from psycopg.types.json import Json

        return Json(value)
    if t.startswith("timestamp"):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:  # noqa: BLE001 - 原样传入
                return value
        return value
    return value


def main() -> None:
    src_url = os.environ.get("SOURCE_SQLITE") or "sqlite:///./data/jbgs.db"
    dst_url = os.environ.get("DATABASE_URL", "")
    if not dst_url or "postgresql" not in dst_url:
        print("请设置 DATABASE_URL=postgresql+psycopg://... （当前非 PostgreSQL）")
        sys.exit(1)
    src = create_engine(src_url)
    dst = create_engine(dst_url)
    # 目标库建表（导入模型后 create_all）
    from app.database import Base  # noqa: E402
    from app import models  # noqa: F401,E402

    Base.metadata.create_all(bind=dst)
    tables = list(Base.metadata.tables.keys())
    with src.connect() as conn:
        src_tables = set(
            conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars()
        )
    with dst.begin() as conn:
        conn.execute(text("SET session_replication_role = 'replica'"))  # 跳过外键顺序
        try:
            for table in tables:
                if table not in src_tables:
                    print(f"迁移 {table}: 源库无此表，跳过")
                    continue
                types = _target_types(dst, table)
                count = 0
                first = True
                for columns, row in _rows(src, table):
                    if first:
                        missing_not_null = [
                            col
                            for col, meta in types.items()
                            if not meta["nullable"] and col not in columns
                        ]
                        insert_cols = list(columns) + missing_not_null
                        first = False
                    row = {
                        c: _normalize_value(c, v, types.get(c, {}))
                        for c, v in row.items()
                    }
                    for col in missing_not_null:
                        row[col] = _normalize_value(col, None, types[col])
                    cols = ", ".join(f'"{c}"' for c in insert_cols)
                    placeholders = ", ".join(f":{c}" for c in insert_cols)
                    conn.execute(
                        text(f'INSERT INTO "{table}" ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'),
                        row,
                    )
                    count += 1
                print(f"迁移 {table}: {count} 行")
        finally:
            conn.execute(text("SET session_replication_role = 'origin'"))
    # 同步自增序列（迁移显式 id 后必须，否则新插入撞主键）
    from app.database import _sync_sequences

    with dst.begin() as conn:
        _sync_sequences(conn)
    print("迁移完成。请把 .env 的 DATABASE_URL 指向 PostgreSQL 后重启后端。")


if __name__ == "__main__":
    main()
