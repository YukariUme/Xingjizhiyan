# 星计知研 · 面向高校计算机学科教学研一体化智能平台

面向高校计算机学科的“教学 — 学习 — 科研”一体化智能平台 MVP。底层共享统一计算机学科知识库、RAG、LLM、Agent、代码评测与学情分析能力，三大角色（教师 / 学生 / 科研用户）在统一平台上完成各自的业务闭环，并形成“教学 → 学习 → 学情分析 → 知识巩固 → 科研探索”的数据闭环。

> 赛题：XH-202620 面向一流学科建设的学科垂类大模型与创新应用开发（科大讯飞）
> 作品名：星计知研 · 面向高校计算机学科教学研一体化智能平台
> 技术选型：React + TypeScript + Vite / Python + FastAPI + SQLAlchemy + **PostgreSQL 17 + pgvector** / RapidOCR·RapidLayout·RapidTable / CodeCrucible 判题语义

## 一键启动

Windows 下双击根目录 `dev.bat`，会自动安装依赖、初始化演示数据并同时启动前后端两个窗口：

- 前端：http://localhost:5173
- 后端：http://127.0.0.1:8000（API 文档 http://127.0.0.1:8000/docs）

也可以分开启动：

```bash
# 后端（backend/run_backend.bat，勿用 --reload：其重载子进程在某些安全策略下会被拒绝建套接字）
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# 前端（frontend/run_frontend.bat）
cd frontend
npm install
npm run dev
```

> PostgreSQL 不在运行时后端会报 `connection timeout expired`：先执行根目录
> `start_pg.bat`（dev.bat 已自动调用）。想开机自启：以管理员运行
> `"C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" register -N jbgs-postgres -D "D:\MyStudy\2026Summer\jbgs\backend\data\pgdata" -o "-p 5433"`，
> 之后 `net start jbgs-postgres` 即可。

### 数据库：PostgreSQL（必须已启动）
```powershell
# 1) 启动仓库内独立 PG 实例（端口 5433，数据目录 backend/data/pgdata）
& 'C:\Program Files\PostgreSQL\17\bin\postgres.exe' -D 'D:\MyStudy\2026Summer\jbgs\backend\data\pgdata' -p 5433

# 2) 首次使用：启用 pgvector（backend/data/pgvector 已含 DLL 与 SQL，无需管理员）
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -U jbgs -h localhost -p 5433 -w -d jbgs -f backend/data/pgvector/vector_install.sql

# 3) 后端启动时自动建表/迁移/种子（DEMO_MODE=true）
```
旧 SQLite 数据迁移：`python -m scripts.migrate_pg`（详见 `docs/PG-STRUCTURED-PARSING.md`）。

### 云部署
云主机部署（Docker Compose 全栈：PostgreSQL + pgvector + 后端 + Docker 判题 + Nginx）：
```bash
cp .env.cloud.example .env   # 填写密码/密钥/域名
docker compose up -d --build
```
完整指南（HTTPS、备份、安全清单、升级）见 `docs/DEPLOYMENT.md`。

### 代码判题：Docker 沙箱（默认）
`.env` 已设 `JUDGE_PROVIDER=docker`：每次提交在一次性容器中执行
（断网 + 只读根文件系统 + CPU/内存/进程数硬限制），真实编译运行
Python/C/C++/Java，返回 AC/WA/TLE/MLE/RE/CE。需要本机安装并启动
Docker Desktop（详见 `docs/DOCKER-JUDGE.md`）；也可配置
`JUDGE_PROVIDER=codecrucible` 接 CodeCrucible 远程集群
（详见 `docs/CODECRUCIBLE-JUDGE.md`）。

## 演示账号

| 角色 | 用户名 | 密码 | 说明 |
| --- | --- | --- | --- |
| 教师 | teacher1 | 123456 | 王教授：课程 / 备课 / 作业 / 批改 / 学情 / 知识库管理 |
| 学生 | student1 | 123456 | 李明：作业评测 / AI 导师 / 个性化路径（另备 student2-6 供学情演示） |
| 科研 | researcher1 | 123456 | 周博士：论文阅读 / 前沿探索 |

首页三个入口卡片支持“一键切换角色”，无需手动输入密码。

## 功能总览

> 2026-08 重构后：顶部切换的是**工作模式**（教学 / 学习 / 研究）而非身份。教师可进教学+研究，本科生/研究生可进学习+研究。
> - 教学模式：首页 / 我的课程 / AI 教学设计（含班级学情）/ 教学诊断（数据→AI 建议→采用）/ 作业与实验 / 课程知识空间（S/A/P + 审核）/ 研究空间
> - 学习模式：首页 / 我的课程 → **课程学习空间**（课程首页·课前预习·AI课程讲堂·作业实验·课后复习·考前模拟·课程资料·AI答疑）/ 学习中心（今日任务·个性化计划）/ AI学科导师 / 研究空间
> - 研究模式：工作台 / 论文阅读（上传+引用）/ 论文对比 / 前沿探索 / 学习空间；课程知识点 ↔ 论文双向跳转

| 角色 | 页面 | 说明 |
| --- | --- | --- |
| 教师 | 首页 Dashboard | 当前课程、待批改、提交率、班级正确率、高频错误知识点、最近活动 |
| 教师 | 智能备课 | 输入课程/章节/主题，Agent 生成教案；**自动保存历史教案**，可查看/复用/删除 |
| 教师 | 课程管理 | 新建/删除课程，邀请学生（待接受），查看选课名单与待接受邀请 |
| 教师 | 作业管理 | 编程题（测试点规则）/ 简答题 / 实验报告，查看提交矩阵 |
| 教师 | AI 辅助批改 | AI 建议分 + 理由 + 知识点归因，教师确认最终成绩后才对学生可见 |
| 教师 | 学情分析 | 各知识点正确率、高频错误、能力分布、薄弱点清单（图表展示） |
| 教师 | 知识库管理 | 学科分类树（含 0 文档新课程）/ 按课程·类型筛选 / 关键词搜索 / 时间·大小排序 / 新增·上传·编辑·删除 / 后台任务进度 |
| 学生 | 作业中心 | 在线编辑代码、提交评测、查看测试点与错误、再次提交；简答题等待教师批改 |
| 学生 | 账号注册 | 首页「账号登录 / 注册」注册（用户名唯一，密码 ≥6 位），注册后自动登录 |

### 课程三步流程

1. **建课**：教师上传知识库文件或手动新增文档时可「＋ 新建课程」（也可在课程管理新建），新课程学生数为 0；
2. **邀请**：教师「课程管理 → 学生管理」按用户名邀请已注册学生，生成**待接受邀请**（不直接选课），卡片显示“N 待接受”，可撤销；
3. **接受**：学生首页出现“课程邀请”卡片，点击接受后才正式加入课程（我的课程/作业/学情随之生效），拒绝后教师可重新邀请。
| 学生 | AI 学科导师 | 提示 / 详细两种模式，回答附带知识点与知识库引用来源；**对话自动保存**，可查看历史/一键清空 |
| 学生 | 代码错误诊断 | 错误原因、涉及知识点、分析思路、学习建议（提示模式不给完整答案） |
| 学生 | 学习中心 | 知识掌握画像、个性化学习路径（复习章节 / 练习 / 实验 / 论文）、知识库浏览 |
| 科研 | 工作台 | 研究方向、最近论文、推荐与收藏（默认私有） |
| 科研 | 论文阅读助手 | 摘要/问题/方法/实验/结论/局限/延伸 + 引用来源 + 知识点跳转 |
| 科研 | 前沿探索 | 主题 → 研究方向、论文、热点、方法分类、时间趋势 |

## 教学研联动设计

1. 教师备课生成的知识点 → 成为学生学习内容（知识库）。
2. 教师发布编程作业 → 学生提交 → 自动评测 → 错误知识点写入学生学习画像。
3. 多名学生错误集中 → 教师端学情分析显示班级薄弱项，提示重点讲解。
4. 学生掌握某知识点 → 推荐关联科研论文。
5. 论文分析涉及的知识点 → 可跳转知识库基础讲义。

## 工作流引擎

平台内置轻量声明式工作流引擎（`backend/app/services/workflow/`），支持多步骤编排、条件分支与人工审批节点，每一步输入输出留痕，可在前端“工作流中心”可视化查看执行过程：

| 工作流 | 流程 | 触发方式 |
| --- | --- | --- |
| 智能备课 | 检索知识库 → LLM 生成教案 → 按主题分支（编程案例/概念辨析）→ 保存教案 | 备课页 / 工作流中心 |
| 作业闭环 | 提交 → 按题型分支（编程评测 / AI 建议）→ 失败诊断 → 画像更新 → 教师审批 | 学生提交自动触发 |
| 科研综述 | 检索论文 → 逐篇 AI 精读 → 知识库参考 → LLM 生成综述 | 前沿探索页 / 工作流中心 |
| 课前预习 | 检索官方资料 → 预习 Agent → 记录学习行为 | 课程空间·预习 |
| AI 课程讲堂 | 检索资料 → 按深度分支 → 讲堂 Agent → 记录 | 课程空间·讲堂 |
| 课后复习 | 检索资料 + 画像 → 复习 Agent（总结/薄弱点/练习）→ 记录 | 课程空间·复习 |
| 考前模拟-出卷/评分 | 出卷 Agent（代码题接入 Judge）/ 评分 Agent（画像+建议） | 课程空间·模拟 |
| 教学诊断 | 班级学情统计 → 诊断 Agent（问题/证据/建议） | 教学诊断页 |
| 课程答疑 | 导师 Agent（RAG 命中/扩展知识 + 对话历史） | AI 学科导师 / 课程答疑 |

每个学习模式都有独立 Agent（预习/讲堂/复习/模拟考试/诊断/答疑），全部内容带 **AI 生成标签 + 参考来源（[S]/[A]/[P] + 页码）**，并返回 `workflow_run_id`，可在“工作流中心”回看每一步执行过程。

快速自检：后端启动后执行 `python -m scripts.smoke`，覆盖三个工作流、提交审批闭环与 RAG 落地/回退。

## RAG 回答策略（先检索，再生成）

对齐软件杯项目（softwarecup）的 TF-IDF（char_wb 2-4 gram）检索方案：

1. 每次 AI 回答前先检索知识库（文档上传/新增后自动切分索引，也可“全量重建索引”）；
2. 命中（相似度 ≥ `RAG_GROUNDING_THRESHOLD`，默认 0.05）→ 把知识库切片作为上下文交给 LLM，回答附带来源引用，前端显示“基于知识库回答”；
3. 未命中 → 回退为模型自身知识回答，前端显示“模型自身知识（未命中知识库）”；
4. 检索带**可信门控**，防止“假命中”：
   - 低分命中必须至少有 2 个特征词（非通用词，如“婚姻”“匹配”）真实出现在知识库切片中；只共享“算法/复杂度/数据结构”等通用词不算命中；
   - 知识库切片的主题名完整出现在问题中（如“栈和队列”）视为强命中信号；
   - **来源引用只取实际命中的知识库文档**，不信任模型自行编造的引用；
   - 因此“婚姻匹配算法”这类知识库没有对应内容的提问，会如实标注“模型自身知识”，不会假装引用了知识库。
5. **跨语言检索**：内置计算机术语中译英映射（婚姻匹配→stable marriage、二分图→bipartite graph、动态规划→dynamic programming 等）。
   中文提问会自动扩展英文关键词并保留中文原文，因此导入英文教材（如 Algorithm Design）后，
   用中文问“婚姻匹配问题”“二分图匹配”也能命中并引用教材原文；课程名/标题元数据（如“算法设计”→“算法设计与分析”）同样参与匹配。

手动配置知识库：教师/科研角色进入「知识库管理」，手动新增或上传 txt/md/pdf，保存后自动切分并进入 RAG 检索。

## 界面设计

前端视觉借鉴了 GeoAgent 城市数智服务平台的“纸墨编辑风”：暖纸底色、墨色文字、青色主色、衬线标题（Noto Serif SC）与等宽数字（IBM Plex Mono），整体更接近学术出版物的克制质感。

## 演示账号

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| 教师 | teacher1 | 123456 |
| 学生 | student1 | 123456 |
| 科研用户 | researcher1 | 123456 |

## 技术架构

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 项目结构

```text
backend/
  app/
    api/           HTTP 路由 + RBAC（auth/courses/assignments/submissions/
                   grading/analytics/learning/research/knowledge/ai/activities）
    services/
      llm/         LLMService 接口 + Mock/DeepSeek 实现 + 工厂
      rag/         RAGService 接口 + SQLite 本地检索实现 + 工厂
      agent/       AgentService 接口 + Teaching/Learning/Research Agent + 工厂
      judge/       CodeJudgeService 接口 + Mock 静态评测 + 工厂
      prompt.py    各 Agent 提示词模板（业务代码不散落拼 Prompt）
      grading/analytics/learning_path/knowledge/activity 业务服务
    models/        SQLAlchemy 实体（User/Course/Assignment/Question/Submission/
                   KnowledgeDocument/KnowledgeChunk/Paper/… 20+ 张表）
    repositories/  数据访问层
    schemas/       Pydantic 请求/响应模型
    mock/          知识库、论文、题库、演示账号数据
    seed.py        演示数据初始化（幂等）
  tests/           24 个单元/集成测试
frontend/
  src/
    api/           统一 API 客户端（Token / 错误处理）
    components/    Layout / UI / SVG 图表 / 代码编辑器 / AI 对话面板
    pages/         teacher/ student/ research/ 按角色组织
```

## 知识库管理接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /api/knowledge/documents | 按学科/主题/关键词筛选文档 |
| GET | /api/knowledge/documents/{id}/chunks | 查看文档切片 |
| POST | /api/knowledge/documents | 手动新增（教师/科研） |
| PUT | /api/knowledge/documents/{id} | 编辑并重新索引 |
| DELETE | /api/knowledge/documents/{id} | 删除文档与切片 |
| POST | /api/knowledge/upload | 上传 txt/md/pdf，自动提取文本 |
| POST | /api/knowledge/documents/{id}/reindex | 重新切分 + 向量化 |
| GET | /api/knowledge/search | RAG 检索（切片 + 来源 + 相似度） |
| GET/POST | /api/knowledge/subjects / points | 分类统计 / 知识点管理 |
| GET/POST | /api/knowledge/import/scan · /run | 扫描并批量导入目录中的教材文件 |

### 批量导入教材（推荐做法）

把**合法拥有**的教材 PDF/txt 放进 `backend/data/knowledge_files/`（可用 `KNOWLEDGE_FILES_DIR` 改路径），
然后在「知识库管理 → 批量导入」选择课程、勾选文件一键入库；已导入的文件自动跳过，支持 188MB 级整本教材，
无需走 HTTP 上传。扫描版 PDF（无文字层）会提示导入失败，请先用 OCR/转换工具生成文字版。

## 代码多语言与大文件

### 代码提交支持 4 种语言

学生提交编程题时可选择 **Python / Java / C++ / C**，切换语言会自动替换为对应语言的模板。
Mock Judge 支持跨语言判定：`def reverse_list` 这类测试点在 Java 中按 `reverseList`（驼峰）判定，
`None` 等价于 `null / nullptr / NULL`，`True/False` 等价于 `true/false`。

### 知识库上传元数据

上传文件时可填写与“手动新增/编辑”完全一致的元数据（标题、学科、主题、章节、来源、类型、难度、年份），
便于跨语言检索与来源追溯。

### 大文件（如 188MB 整本教材 PDF）

上传上限由 `backend/.env` 的 `MAX_UPLOAD_MB` 控制，默认 **200MB**，上传采用流式落盘后再解析，不一次性读入内存。

### 支持的文件格式与扫描版 PDF

- 支持格式：**txt / md / pdf**（上传接口与目录批量导入一致）。
- **上传/导入为后台任务**：提交后立即返回任务号，页面顶部显示“后台任务”进度条，
  其他功能不受影响；通过 `GET /api/knowledge/jobs` 轮询进度。
- 文字版 PDF：pypdf 直接提取文本，秒级解析。
- 扫描版（图片型）PDF：自动检测并触发**离线中文 OCR**（PyMuPDF 渲染 + RapidOCR，**多线程并行识别**），
  逐页回报“OCR 识别 X/Y 页”进度。
  安装依赖：`python -m pip install -r backend/requirements-ocr.txt`；通过 `PDF_OCR_ENABLED` 开关控制。
  注意：整本扫描教材 OCR 仍需数分钟到更久（60MB 扫描书通常数百页），建议按章节拆分后再导入，
  或优先使用带文字层的版本。
- 若未安装 OCR 依赖，扫描版 PDF 会返回明确提示而不是静默失败。

放宽到 200MB 的代价（已做对应缓解）：

- 内存/CPU：PDF 文本提取（pypdf）是 CPU 密集操作，188MB 教材可能需要几十秒到数分钟，期间请求保持等待；
- 切片规模：百万级字符会切出数万切片（当前 197 万字符教材 → 6046 切片），入库与“全量重建索引”耗时变长；
- 检索性能：已把 TF-IDF 索引改为**进程级缓存**（同一批切片只训练一次向量化器），避免每次问答都重建索引。

更快的替代方案：把 PDF 按章节拆分后分别上传，或先用工具转成 txt 再上传；未来接入真实向量库后可进一步支撑更大语料。

## 可替换的 AI 模块

| 模块 | 接口 | Mock 实现 | 未来实现 |
| --- | --- | --- | --- |
| LLM | `LLMService.generate/chat/stream` | `MockLLMService` | `DeepSeekLLMService`（已预留） |
| RAG | `RAGService.ingest/embed/search/rerank/generate_answer` | SQLite 本地检索 | Embedding + Vector DB |
| Agent | `AgentService` | `TeachingAgent/LearningAgent/ResearchAgent` | 真实工作流编排 |
| 评测 | `CodeJudgeService.judge` | 静态规则 Mock Judge | Docker / 安全沙箱 |

通过 `backend/.env` 中的 `LLM_PROVIDER` / `RAG_PROVIDER` / `JUDGE_PROVIDER` 切换实现。

## 接入 DeepSeek（三步）

1. 打开 `backend/.env`（已生成，且被 .gitignore 排除，不会提交密钥），把 `LLM_PROVIDER` 改为 `deepseek`，并在 `DEEPSEEK_API_KEY` 填入你的密钥（形如 `sk-xxxx`）：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-你的密钥
```

2. **必须重启后端**（`dev.bat` 或 `backend/run_backend.bat`），否则运行中的服务仍使用旧配置（启动时读取一次）。

3. 验证连通性（注意：要在 `backend` 目录下运行，或直接双击根目录 `check_llm.bat`）：

```bash
cd backend
python -m app.check_llm
```

看到「✓ 调用成功」即接入完成。也可以打开 http://127.0.0.1:8000/api/health 查看 `providers.llm=deepseek`。

说明：

- 未填写 Key 时，AI 接口会返回清晰的 503 提示，普通页面不受影响（RAG 检索、知识库管理仍可用）；
- 配置读取已固定指向 `backend/.env`（与启动目录无关）；`CORS_ORIGINS` 同时兼容逗号分隔与 JSON 数组写法；
- 业务代码不感知提供方：备课 / 导师 / 论文分析 / 前沿探索 / 主观题批改全部走 `LLMService` 接口，Mock 与 DeepSeek 共用同一套 Prompt 与解析逻辑；
- 想换回离线演示，把 `LLM_PROVIDER` 改回 `mock` 即可。

## 测试

```bash
cd backend
python -m pytest -q
```

覆盖：LLM 生成、RAG 切分/检索/引用、Mock Judge 判定、三类 Agent、API 认证与 RBAC
（学生隔离、教师课程隔离、科研私有）、AI 批改闭环、知识库 CRUD、代码提交与诊断。
## 本次更新

- 新增统一学习状态引擎，把画像、答题、答疑和学习节奏统一成可解释状态。
- 个性化推荐升级为“规则 + 行为窗口”联动，不再只看静态画像。
- 学生 AI 导师接入最近学习行为、重复错题和高频提问主题。
- 教师教学诊断支持“采纳 / 修改 / 拒绝”留痕，并可回看最近决策。
- 教师批改后会自动回流到画像、任务和学习路径。
- 学习中心新增“统一学习状态”和“学习前后对比”展示。
- 课程学习空间首页新增“下一步建议”，减少用户手动找入口。
- 新增 `docs/MODIFICATION_REPORT.md` 与 `docs/TEST_GUIDE.md`，便于验收和答辩演示。

## 高级改进建议（优秀参赛作品标准）

### 1. 做成真正的“自适应闭环”
当前已经有行为信号，但还可以进一步把 `LearningRecord`、答题耗时、错因、对话主题、回看频次统一成一个“学习状态向量”，让推荐不只是“给建议”，而是自动决定下一步的学习形式、难度和节奏。

### 2. 做成“可解释 AI”
把每一条推荐都补上证据链：最近错了什么、为什么推荐、来自哪次作业或哪条对话、对应哪个知识点。评委通常很吃这一套，因为它体现的是“系统不是拍脑袋”。

### 3. 做成“教师可干预”
给教师端加一个一键接受/调整推荐的入口，让教师可以把系统建议改成班级统一任务。这样会更像真实教学场景，而不是孤立的个人练习工具。

### 4. 做成“演示强可视化”
把学情变化做成时间轴或前后对比卡片，展示“提交前 / 批改后 / 推荐后”的变化。参赛时评委通常只看几分钟，视觉对比会比长文本更有说服力。

### 5. 做成“数据可追踪”
每一次自动生成都保留 `workflow_run_id`、输入证据、生成结果和人工确认记录。这样你答辩时能直接讲“闭环证据”，而不是只讲功能名词。

### 6. 做成“边界更稳”
给 RAG、导师答疑、批改三个环节都补失败回退：无命中时明确说明、低置信度时降低自动化程度、敏感内容时只给引导不直接给答案。这个会显得系统更成熟。

### 7. 做成“一个月可见成长”
如果后续还有时间，优先做：行为画像仪表盘、推荐解释卡、教师一键采纳、课程页自动跳转、答疑历史聚类。这几项最容易让作品从“能用”变成“像成品”。
