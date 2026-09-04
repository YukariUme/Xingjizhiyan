"""数据库引擎、会话与 ORM 基类。"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


def utcnow() -> datetime:
    """返回无时区信息的 UTC 当前时间（SQLite 兼容）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ensure_db_dir(database_url: str) -> None:
    """SQLite 文件型数据库启动前确保父目录存在。"""
    if database_url.startswith("sqlite:///"):
        path = database_url.replace("sqlite:///", "", 1)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)


settings = get_settings()
_ensure_db_dir(settings.database_url)

engine = create_engine(
    settings.database_url,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    }
    if settings.database_url.startswith("sqlite")
    else {},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    """SQLite 并发优化：WAL 模式 + 外键 + 忙等待。"""
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的公共基类。"""


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：为每个请求提供一个数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表（幂等）。"""
    from app import models  # noqa: F401  确保模型注册到 Base.metadata

    Base.metadata.create_all(bind=engine)
    _migrate(engine)


def _migrate(db_engine) -> None:
    """轻量迁移：为已有数据库补充新列并回填（不删除任何数据）。"""
    with db_engine.begin() as conn:
        _ensure_columns(conn, "workflow_runs", [("submission_id", "INTEGER")])
        _ensure_columns(
            conn,
            "users",
            [
                ("identity", "VARCHAR(20)"),
                ("modes", "TEXT"),
            ],
        )
        _ensure_columns(
            conn,
            "knowledge_points",
            [
                ("related_points", "TEXT"),
                ("aliases", "TEXT"),
                ("chapter_id", "INTEGER"),
                ("sub_points", "TEXT"),
            ],
        )
        _ensure_columns(
            conn,
            "knowledge_documents",
            [
                ("course_id", "INTEGER"),
                ("source_level", "VARCHAR(8)"),
                ("visibility", "VARCHAR(16)"),
                ("owner_id", "INTEGER"),
                ("page", "VARCHAR(64)"),
                ("document_type", "VARCHAR(32)"),
                ("approved_by", "INTEGER"),
                ("approved_at", "DATETIME"),
                ("rag_hit_count", "INTEGER"),
            ],
        )
        _ensure_columns(
            conn,
            "knowledge_chunks",
            [
                ("course_id", "INTEGER"),
                ("source_level", "VARCHAR(8)"),
                ("visibility", "VARCHAR(16)"),
            ],
        )
        _ensure_columns(
            conn,
            "demo_scenarios",
            [("initial_role", "VARCHAR(16)")],
        )
        _ensure_columns(
            conn,
            "student_knowledge_profiles",
            [
                ("success_count", "INTEGER"),
                ("evidence_count", "INTEGER"),
                ("confidence", "FLOAT"),
                ("evidence_type", "VARCHAR(24)"),
            ],
        )
        # 回填：身份与工作模式
        conn.exec_driver_sql(
            "UPDATE users SET identity = CASE role WHEN 'teacher' THEN 'teacher' "
            "WHEN 'researcher' THEN 'graduate' ELSE 'student' END "
            "WHERE identity IS NULL OR identity = ''"
        )
        modes_sql = (
            "UPDATE users SET modes = CAST((CASE role "
            f"WHEN 'teacher' THEN '{json.dumps(['teaching', 'research'])}' "
            f"WHEN 'researcher' THEN '{json.dumps(['research', 'learning'])}' "
            f"ELSE '{json.dumps(['learning', 'research'])}' END) AS json) "
            "WHERE modes IS NULL OR CAST(modes AS TEXT) IN ('', '[]')"
        )
        conn.exec_driver_sql(modes_sql)
        # 回填：文档/切片关联课程与 S/A/P 默认值
        conn.exec_driver_sql(
            "UPDATE knowledge_documents SET course_id = "
            "(SELECT id FROM courses WHERE courses.name = knowledge_documents.course) "
            "WHERE course_id IS NULL"
        )
        conn.exec_driver_sql(
            "UPDATE knowledge_documents SET source_level='S', visibility='official' "
            "WHERE source_level IS NULL OR source_level = ''"
        )
        conn.exec_driver_sql(
            "UPDATE knowledge_chunks SET course_id = "
            "(SELECT course_id FROM knowledge_documents "
            "WHERE knowledge_documents.id = knowledge_chunks.document_id) "
            "WHERE course_id IS NULL"
        )
        conn.exec_driver_sql(
            "UPDATE knowledge_chunks SET source_level='S', visibility='official' "
            "WHERE source_level IS NULL OR source_level = ''"
        )
        conn.exec_driver_sql(
            "UPDATE knowledge_documents SET rag_hit_count = 0 WHERE rag_hit_count IS NULL"
        )
        # PostgreSQL：检测 pgvector 并补充 embedding_vector 列（SQLite 无需）
        if not settings.database_url.startswith("sqlite"):
            has_vector = conn.exec_driver_sql(
                "SELECT to_regtype('vector') IS NOT NULL"
            ).scalar()
            if has_vector:
                conn.exec_driver_sql(
                    "ALTER TABLE knowledge_chunks "
                    "ADD COLUMN IF NOT EXISTS embedding_vector vector(512)"
                )
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_chunks_embedding "
                    "ON knowledge_chunks USING hnsw (embedding_vector vector_cosine_ops)"
                )
            _sync_sequences(conn)


def _sync_sequences(conn) -> None:
    """PostgreSQL：数据迁移后同步自增序列，避免新插入撞主键。"""
    if settings.database_url.startswith("sqlite"):
        return
    conn.execute(
        text(
        """
        DO $$
        DECLARE r record;
        BEGIN
          FOR r IN
            SELECT c.table_name, c.column_name
            FROM information_schema.columns c
            JOIN pg_class t ON t.relname = c.table_name
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE c.column_name = 'id'
              AND c.table_schema = 'public'
              AND t.relkind = 'r'
          LOOP
            IF pg_get_serial_sequence(r.table_name, r.column_name) IS NOT NULL THEN
              EXECUTE format(
                'SELECT setval(pg_get_serial_sequence(%L, %L), '
                'GREATEST((SELECT COALESCE(MAX(%I), 1) FROM %I), 1))',
                r.table_name, r.column_name, r.column_name, r.table_name
              );
            END IF;
          END LOOP;
        END $$;
        """
        )
    )


def _ensure_columns(conn, table: str, columns: list[tuple[str, str]]) -> None:
    if not settings.database_url.startswith("sqlite"):
        _ensure_columns_pg(conn, table, columns)
        return
    existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
    for name, ctype in columns:
        if name not in existing:
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ctype}")


def _ensure_columns_pg(conn, table: str, columns: list[tuple[str, str]]) -> None:
    """PostgreSQL 版列迁移：information_schema 探测 + ADD COLUMN IF NOT EXISTS。"""
    existing = {
        row[0]
        for row in conn.exec_driver_sql(
            "SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{table}'"
        )
    }
    for name, ctype in columns:
        if name in existing:
            continue
        conn.exec_driver_sql(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{name}" {_pg_type(ctype)}')


def _pg_type(sqlite_type: str) -> str:
    """SQLite 列类型 → PostgreSQL 类型。"""
    mapping = {
        "INTEGER": "INTEGER",
        "VARCHAR": "VARCHAR",
        "TEXT": "TEXT",
        "FLOAT": "DOUBLE PRECISION",
        "DATETIME": "TIMESTAMP",
        "BOOLEAN": "BOOLEAN",
    }
    for prefix, pg in mapping.items():
        if sqlite_type.upper().startswith(prefix):
            # VARCHAR(20) 保留长度
            return sqlite_type if prefix == "VARCHAR" else pg
    return sqlite_type
