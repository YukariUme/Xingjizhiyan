FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 系统依赖：docker CLI（判题沙箱）、curl/git（OCR 模型与工具下载）
RUN apt-get update && apt-get install -y --no-install-recommends \
        docker.io \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（PostgreSQL + pgvector 客户端、RAG/OCR 解析管线）
COPY requirements.txt requirements-ocr.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ocr.txt

COPY app ./app
COPY scripts ./scripts

# 数据目录（知识文件、嵌入缓存、判题临时工作区）
RUN mkdir -p /app/data/knowledge_files /app/data/embeddings /app/data/judge_work

EXPOSE 8000

# 判题通过挂载的 docker.sock 调用宿主 Docker（见 docker-compose.yml）。
# 容器以 root 运行仅为兼容 docker.sock；生产多租户建议判题 daemon 独立隔离。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
