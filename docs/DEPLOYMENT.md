# 云部署指南（Docker Compose 全栈）

> 面向公网生产的部署文档。本地开发仍按根 README 的 dev 流程（后端 uvicorn + 前端 vite）。
> 判题默认走 Docker 沙箱（见 `docs/DOCKER-JUDGE.md`），数据库用 PostgreSQL + pgvector。

## 一、架构

```
用户浏览器
    │ https://your-domain.com
    ▼
Caddy / Nginx（HTTPS，可选用 deploy/Caddyfile.example）
    │ :80 / :443
    ▼
frontend（Nginx 静态站点 + 反代 /api）
    │
    ▼
backend（FastAPI，挂载 docker.sock 调用判题）
    ├── db（pgvector/pgvector:pg17，命名卷持久化）
    ├── Docker 判题沙箱（python/gcc/temurin 镜像，--network none）
    └── 命名卷 jbgs-data（知识文件、嵌入缓存、判题工作区）
```

## 二、前置条件（云主机）

- Linux x86_64（Ubuntu 22.04 / Debian 12 等），≥ 4 核 8G（判题容器 + Embedding/OCR 模型需要内存）；
- Docker Engine ≥ 24 + Docker Compose v2（`docker compose version`）；
- 域名 A 记录解析到主机公网 IP（HTTPS 需要）；
- 出网权限：拉镜像、DeepSeek API、fastembed 模型下载、OCR 模型下载。

## 三、快速开始

```bash
# 1) 克隆/上传代码到云主机（含 backend、frontend、deploy、docker-compose.yml）
# 2) 配置环境变量（.env 已被 .gitignore 排除，不会提交）
cp .env.cloud.example .env
vi .env          # 至少填写：POSTGRES_PASSWORD / SECRET_KEY / DEEPSEEK_API_KEY / CORS_ORIGINS

# 3) 预拉取判题镜像（可选，避免首次提交等待）
bash deploy/pull-images.sh

# 4) 构建并启动
docker compose up -d --build
docker compose ps            # 三个服务 healthy/running
docker compose logs -f backend
```

启动后访问 `http://服务器IP`（未配 HTTPS 前先开 80 端口）。后端自动建表、启用 pgvector、
执行轻量迁移；`DEMO_MODE=false` 时不种演示数据，需用「注册」创建账号。

## 四、环境变量说明（.env）

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | 是 | 数据库密码（compose 自动建库） |
| `SECRET_KEY` | 是 | JWT/会话密钥，用随机长字符串 |
| `DEEPSEEK_API_KEY` | 是 | LLM Key |
| `CORS_ORIGINS` | 是 | 例如 `https://your-domain.com` |
| `DOMAIN` / `WEB_PORT` | 是 | 域名与前端映射端口 |
| `DEMO_MODE` | 否 | `false`（生产） |
| `JUDGE_PROVIDER` | 否 | `docker`（默认）或 `codecrucible` |
| `OCR_PROVIDER` | 否 | `auto`（RapidOCR） |

## 五、HTTPS + 域名

两种方式任选：

1. **Caddy（推荐，自动证书）**：修改 `deploy/Caddyfile.example` 中的域名，
   按文件内注释运行 caddy 容器；
2. **云厂商负载均衡**：SLB/CLB 挂 80 端口，托管证书，转发到主机 `WEB_PORT`。

配好后把 `.env` 的 `CORS_ORIGINS` 改为 `https://your-domain.com` 并 `docker compose up -d`。

## 六、安全清单

- 云安全组只放行 80/443（调试用的 8000 仅在临时开放）；数据库、Docker 端口不对公网；
- `.env` 不入库；`SECRET_KEY`/`DEEPSEEK_API_KEY` 用强随机值；
- `DEMO_MODE=false`，避免生产库被自动种子；
- 判题沙箱已断网 + 只读根文件系统 + 资源硬限制（`docs/DOCKER-JUDGE.md`）；
  backend 容器挂 docker.sock 相当于授予 Docker 控制权，单机部署可接受；
  多租户/高安全场景应把判题拆到独立 daemon 或远程 CodeCrucible 集群；
- 定期备份（见下）。

## 七、备份与恢复

```bash
# 手动备份（PG dump + 知识文件），可加 crontab
bash deploy/backup.sh

# 恢复数据库
docker compose exec -T db pg_restore -U jbgs -d jbgs -c < backups/jbgs-xxxx.dump
```

建议把 `backups/` 目录同步到对象存储（ossutil / s3cmd / rclone）。

## 八、升级/迁移

- 代码更新：`git pull && docker compose up -d --build`；
- 数据库结构变更由启动时 `_migrate` 自动补充新列（不删数据）；
- 从本地 SQLite 上云：先在本地 `python -m scripts.migrate_pg` 迁到 PG，
  再用 `pg_dump -F c` 导出并在云上 `pg_restore`；
- pgvector 由 `pgvector/pgvector:pg17` 镜像内置，`deploy/init-db-vector.sql`
  在首次建库时自动 `CREATE EXTENSION vector`。

## 九、已知注意事项

- **首次使用的联网下载**：RapidOCR/RapidLayout/RapidTable 模型、fastembed 模型、
  判题镜像都会在首次运行时下载；建议部署后预热（上传一个小 PDF、提交一道题）。
- **单实例限制**：后台任务（知识库入库）与 RAG 内存索引是进程内实现，
  当前架构只支持单后端副本；需要横向扩容时再引入 Redis/Celery 与共享向量索引。
- **上传体积**：Nginx `client_max_body_size 200m` 已与后端 `MAX_UPLOAD_MB` 对齐。
- **对象存储**：上传文件目前落盘在 `jbgs-data` 卷；数据量大后可改接 OSS/S3
  （需要新增存储抽象，不在本次范围）。
