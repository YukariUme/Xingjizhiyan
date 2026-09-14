# 星计知研 · 面向高校计算机学科教学研一体化智能平台

> 赛题：XH-202620 面向一流学科建设的学科垂类大模型与创新应用开发（科大讯飞）\
> 作品：星计知研 · 面向高校计算机学科教学研一体化智能平台

## 一、作品简介

星计知研是一个面向高校计算机学科的“教学—学习—科研”一体化智能平台。底层共享统一计算机学科知识库、RAG 检索、大模型、Agent、代码评测与学情分析能力，教师、学生、科研用户在同一平台完成各自业务闭环，并形成“教学 → 学习 → 学情分析 → 知识巩固 → 科研探索”的数据闭环。

### 核心功能

- **教师端**：AI 教学诊断（数据→问题→证据→建议→采纳）、AI 智能备课（结合知识库与班级学情）、作业管理、AI 辅助批改、学情分析、课程知识库管理。
- **学生端**：课程学习空间、AI 自学链（目标→引入→讲解→动图→代码→练习→小结）、代码评测与行级错误诊断、个性化学习画像与路径、AI 导师（支持语音输入与朗读）、数据结构动画演示、AI 圆桌讨论。
- **科研端**：论文阅读与结构化分析、论文对比、前沿探索、课程知识点 ↔ 论文双向跳转。
- **统一能力**：RAG 检索增强（回答可追溯，标注具体来源与页码）、多智能体协作、代码 Docker 沙箱评测、可解释学情闭环、工作流全程留痕。

### 技术架构

| 层 | 技术 |
| --- | --- |
| 前端 | React + TypeScript + Vite |
| 后端 | Python + FastAPI + SQLAlchemy |
| 数据库 | PostgreSQL 17 + pgvector |
| 知识解析 | RapidOCR / RapidLayout / RapidTable、pypdf |
| 代码评测 | Docker 沙箱 / CodeCrucible |
| 大模型接入 | 支持 DeepSeek、OpenAI 兼容协议，离线可切换 Mock |
| 检索 | TF-IDF 词法 + Embedding 语义混合检索，支持跨语言术语映射 |

## 二、Demo 体验



### 演示账号

| 角色 | 账号 | 密码 |
| --- | --- | --- |
| 教师 | teacher1 | 123456 |
| 学生 | student1 | 123456 |
| 科研用户 | researcher1 | 123456 |

首页三个角色入口卡片支持“一键切换角色”，无需手动输入密码。

### 一键演示

登录后点击右上角“▶ 一键演示”，可选择预置场景：

- 教学—学习—科研一体化（完整主线）
- 教学闭环
- 学习闭环
- 数据结构动画演示
- AI 圆桌讨论

演示模式使用预置数据，不依赖真实大模型，保证现场演示稳定。快捷键：`Ctrl+Shift+D` 打开演示，`Ctrl+Shift+→/←` 上/下一步，`Ctrl+Shift+1/2/3` 切换角色。

## 三、本地部署教程

### 1. 环境要求

| 依赖 | 版本要求 | 说明 |
| --- | --- | --- |
| Python | ≥ 3.11（推荐 3.13） | 后端运行 |
| Node.js | ≥ 18（推荐 20+） | 前端构建 |
| npm | 随 Node 安装 | 前端依赖管理 |
| PostgreSQL | 17 | 主数据库，需启用 pgvector |
| Docker Desktop | 可选 | 代码判题沙箱（不装则代码评测使用 Mock） |
| Git | 任意 | 拉取代码 |

### 2. 获取代码

```bash
git clone https://github.com/YukariUme/Xingjizhiyan

```

### 3. 配置后端

进入 `backend` 目录，复制环境变量示例：

```bash
cd backend
cp .env.example .env.local   # Windows 可手动复制并改名
```

按需填写关键配置：

```ini
# 大模型（不填密钥时使用 Mock，离线演示）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的密钥

# 数据库（PostgreSQL + pgvector）
DATABASE_URL=postgresql://jbgs:你的密码@localhost:5433/jbgs

# 代码评测（docker 或 codecrucible；未装 Docker 时用 mock）
JUDGE_PROVIDER=docker
```

> 默认演示环境可保持 `LLM_PROVIDER=mock`，平台各页面仍可运行，AI 接口返回预置/兜底结果。

### 4. 启动 PostgreSQL（Windows 一键）

双击根目录 `start_pg.bat`，或在命令行执行：

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\postgres.exe' -D 'D:\你的路径\jbgs\backend\data\pgdata' -p 5433
```

首次使用需启用 pgvector：

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -U jbgs -h localhost -p 5433 -w -d jbgs -f backend\data\pgvector\vector_install.sql
```

### 5. 启动后端

```
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

启动后自动建表并初始化演示数据。验证：访问 `http://127.0.0.1:8000/api/health`。

### 6. 启动前端

```
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。

### 7. Windows 一键启动（推荐）

直接双击根目录 `dev.bat`，会自动：

1. 启动 PostgreSQL；
2. 安装依赖；
3. 初始化演示数据；
4. 启动后端窗口（:8000）；
5. 启动前端窗口（:5173）。

### 8. 生产构建

```bash
# 前端
cd frontend
npm run build

# 后端（可选 Docker Compose 全栈部署）
docker compose up -d --build
```

详细云部署（HTTPS、备份、安全清单、升级）见 `docs/DEPLOYMENT.md`。

### 9. 代码判题（可选）

- 方式一：本机安装并启动 Docker Desktop，保持 `JUDGE_PROVIDER=docker`，代码将在一次性容器中编译运行（断网 + 只读根文件系统 + CPU/内存/进程数硬限制）。
- 方式二：`JUDGE_PROVIDER=codecrucible` 接入 CodeCrucible 远程判题集群，见 `docs/CODECRUCIBLE-JUDGE.md`。
- 方式三：`JUDGE_PROVIDER=mock` 使用静态规则评测，仅用于离线演示。

## 四、项目结构

```bash
jbgs/
├── backend/                 # FastAPI 后端
│   ├── app/api/             # HTTP 路由（含 RBAC）
│   ├── app/models/          # SQLAlchemy 实体
│   ├── app/services/        # LLM/RAG/Agent/Judge/Workflow/学习状态引擎
│   ├── app/mock/            # 演示种子数据
│   ├── app/seed.py          # 初始化演示数据（幂等）
│   └── tests/               # 单元/集成测试
├── frontend/                # React + TS + Vite 前端
│   └── src/
│       ├── components/      # UI 组件（含 AI 导师悬浮球、动图、自学链）
│       └── pages/           # 教师/学生/科研页面
├── deploy/                  # 部署配置
├── docs/                    # 架构、部署、测试、修改报告等文档
├── dev.bat / start_pg.bat   # Windows 一键启动脚本
└── docker-compose.yml       # 云部署编排
```

## 五、常见问题

| 问题 | 解决 |
| --- | --- |
| 后端报 `connection timeout expired` | 确认 PostgreSQL 已启动（先运行 `start_pg.bat`） |
| 代码评测提示“未检测到 Docker” | 安装并启动 Docker Desktop，或把 `JUDGE_PROVIDER` 改为 `mock` |
| AI 接口返回 503 且提示密钥 | 在 `backend/.env` 填 `DEEPSEEK_API_KEY`，或 `LLM_PROVIDER=mock` |
| 扫描版 PDF 导入慢 | 先按章节拆分，或转成带文字层的 PDF/txt 再上传 |
| 前端无法访问后端 | 检查 Vite 代理端口与后端端口是否一致（默认 8000） |

## 六、文档

- `docs/ARCHITECTURE.md`：技术架构
- `docs/DEPLOYMENT.md`：云部署指南
- `docs/DEMO_SCRIPT.md`：演示脚本
- `docs/TEST_GUIDE.md`：测试指南
- `docs/MODIFICATION_REPORT.md`：修改说明
