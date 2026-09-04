"""应用配置：从环境变量 / .env 读取，AI 提供方通过配置切换。"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _default_db_url() -> str:
    """默认 SQLite 路径固定位于 backend/data，与启动目录无关。"""
    path = Path(__file__).resolve().parent.parent / "data" / "jbgs.db"
    return f"sqlite:///{path.as_posix()}"


_BACKEND_DIR = Path(__file__).resolve().parent.parent


def _default_knowledge_files_dir() -> str:
    """批量导入目录：把教材 PDF/txt 放这里，一键扫描导入。"""
    return str(_BACKEND_DIR / "data" / "knowledge_files")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "星计知研 · 教学研一体化智能平台"
    debug_mode: bool = True
    database_url: str = _default_db_url()
    secret_key: str = "dev-secret-change-me"
    demo_mode: bool = True

    # AI 模块提供方
    llm_provider: str = "mock"
    rag_provider: str = "mock"
    judge_provider: str = "mock"
    codecrucible_base_url: str = ""  # 远程 CodeCrucible 判题集群（留空=本地模式）
    codecrucible_auth_token: str = ""
    codecrucible_jwt_secret: str = ""
    codecrucible_problem_id: str = ""
    judge_time_limit_ms: int = 1000
    judge_memory_limit_kb: int = 262144
    judge_allow_unsafe_local: bool = True
    judge_docker_image_python: str = "python:3.11-slim"
    judge_docker_image_c: str = "gcc:13"
    judge_docker_image_cpp: str = "gcc:13"
    judge_docker_image_java: str = "eclipse-temurin:17-jdk"
    judge_docker_cpus: float = 1.0
    judge_docker_pids_limit: int = 64
    judge_docker_global_timeout_s: int = 300
    # 后端容器化部署时设置为 compose 数据卷名（如 jbgs-data），
    # 判题容器通过命名卷挂载工作目录，避免宿主路径解析失败
    judge_docker_volume_name: str = ""
    # 科研前沿热点：arXiv 拉取与缓存
    hotspot_ttl_hours: int = 6
    hotspot_max_papers: int = 5
    vision_provider: str = "mock"  # mock | glm4v | qwen_vl
    asr_provider: str = "mock"
    tts_provider: str = "mock"
    ocr_provider: str = "auto"  # auto | rapid | paddle | mock
    rag_grounding_threshold: float = 0.05
    rag_semantic_threshold: float = 0.35
    embedding_provider: str = "auto"  # auto | hash | fastembed
    rag_search_mode: str = "hybrid"  # hybrid | lexical
    embeddings_cache_dir: str = ""  # 语义向量磁盘缓存目录；留空=数据库同目录/embeddings
    max_upload_mb: int = 200
    knowledge_files_dir: str = _default_knowledge_files_dir()
    pdf_ocr_enabled: bool = True

    # DeepSeek（真实 LLM 接入预留）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # 多模态视觉（预留：智谱 GLM-4V / 通义千问 Qwen-VL）
    glm4v_api_key: str = ""
    glm4v_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    glm4v_model: str = "glm-4v-flash"
    qwen_vl_api_key: str = ""
    qwen_vl_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_vl_model: str = "qwen-vl-plus"

    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, value):
        """兼容逗号分隔与 JSON 数组两种写法。"""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
