"""测试配置：使用独立 SQLite 测试库并自动填充演示数据。"""

import os
import pathlib
import tempfile

# 必须在导入 app 之前设置环境变量。
# 测试库放在系统临时目录：避免污染仓库 data 目录，也兼容受限沙箱环境。
_TEST_DB = pathlib.Path(tempfile.gettempdir()) / "jbgs_test.db"
_TEST_KNOWLEDGE_DIR = pathlib.Path(tempfile.gettempdir()) / "jbgs_test_knowledge"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["KNOWLEDGE_FILES_DIR"] = str(_TEST_KNOWLEDGE_DIR)
os.environ["DEMO_MODE"] = "true"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["RAG_PROVIDER"] = "mock"
os.environ["JUDGE_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "hash"
os.environ["RAG_SEARCH_MODE"] = "lexical"

if _TEST_DB.exists():
    _TEST_DB.unlink()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def _db_ready():
    """确保所有测试（含直接连库的单元测试）先建表并填充数据。"""
    from app.database import SessionLocal, init_db
    from app.seed import seed_if_empty

    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


def login(client: TestClient, role: str) -> dict:
    resp = client.get(f"/api/auth/demo/{role}")
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture
def teacher(client):
    return login(client, "teacher")


@pytest.fixture
def student(client):
    return login(client, "student")


@pytest.fixture
def researcher(client):
    return login(client, "researcher")
