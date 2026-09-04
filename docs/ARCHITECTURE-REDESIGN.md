# 平台架构重构方案（Phase 1：项目审查 + 新架构设计）

> 目标产品：“面向高校计算机学科教学研一体化智能平台”
> 核心理念：让每一门高校计算机课程拥有自己的 AI 学习与教学空间，教学、学习、科研共享同一个专业知识底座。
> 本文档基于当前仓库（2026-08，D:\MyStudy\2026Summer\jbgs）现状编写，先审查后重构，不推倒重写。

---

## A. 当前项目架构分析

### A1. 技术栈

| 层 | 现状 |
| --- | --- |
| 前端 | React 18 + TypeScript + Vite + react-router v6；自研 CSS 设计系统（米白/深青蓝纸墨风）、SVG 图表、无重型 UI 库 |
| 后端 | Python + FastAPI + SQLAlchemy 2 + SQLite（WAL + 外键开启）；pydantic v2；分层：api / services / models / repositories / schemas / mock |
| AI 抽象 | `LLMService`（Mock/DeepSeek + 工厂）、`RAGService`（SQLite TF-IDF char_wb + 跨语言 + 元数据加权 + 可信门控）、`AgentService`（Teaching/Learning/Research）、`CodeJudgeService`（Mock，跨语言判定） |
| 工作流 | 轻量声明式引擎（步骤/分支/人工审批/留痕），3 个内置流程：备课、作业闭环、科研综述 |
| 数据库 | SQLite 单文件（backend/data/jbgs.db），启动时轻量迁移（_migrate） |
| 任务 | 知识库上传/批量导入为后台异步任务（队列 + 进度 + 并行 OCR） |

### A2. 数据模型（10 个模型文件）

User、Course、Enrollment（选课）、CourseInvitation（邀请三步流）、LessonPlan、KnowledgePoint、KnowledgeDocument、KnowledgeChunk、KnowledgeJob、Assignment、Question、Submission、CodeSubmission、SubjectiveSubmission、Evaluation、Feedback、StudentKnowledgeProfile、LearningRecommendation、ChatMessage、Paper、ResearchTopic、PaperReading、WorkflowRun/StepRun、Activity。

### A3. API（15 个路由）

auth、courses、course_invitations、assignments、submissions、grading、analytics、learning、research、knowledge（含 jobs/import/upload/OCR）、workflows、planning（教案历史）、ai（统一助手）、activities。

### A4. 前端页面（20 个，按角色目录）

教师：Dashboard / Courses / LessonPlan / Assignments / AssignmentDetail / Grading / Analytics / KnowledgeBase；
学生：Home / Courses / Assignments / AssignmentDetail / LearningCenter / Tutor；
科研：Workbench / Papers / Explore；共享：Landing / Search / Workflows。

### A5. 已有能力盘点（可直接复用）

- 认证/注册/登录、HMAC Token、RBAC 依赖（`require_roles`）
- 课程三步流程（建课→邀请→学生接受）
- 作业/题目/提交/批改闭环（AI 建议 + 教师确认；代码评测 + 画像回写）
- 学习画像（mastery/attempts/errors）与规则推荐
- 导师问答（RAG 命中/回退、来源引用、对话历史自动保存）
- 知识库：文档 CRUD、异步上传（OCR）、目录批量导入、筛选/排序、TF-IDF 检索
- 工作流引擎 + 可视化 + 运行记录
- 科研：论文库、AI 阅读、前沿探索、综述工作流、教案历史
- 教学研数据联动（作业→画像→学情→推荐；知识点↔论文）

---

## B. 当前产品功能分析

**已形成闭环的部分**：作业（编程评测/简答批改）→ 画像 → 班级学情 → 推荐；备课 → 教案历史；知识库 → RAG 引用 → 导师回答；论文 → 综述。

**仍显孤立的痛点**：
1. 课程只是“列表卡片”，没有可进入的独立课程空间；
2. 知识库是“管理/浏览页”，不是课程的底层知识能力；
3. 导师是全局聊天，不理解“当前课程/章节/资料范围”；
4. 学习中心是“推荐卡 + 文件浏览”，推荐不可解释；
5. 教师端以“批改/学情”为主，缺 AI 教学诊断→建议→教学设计闭环；
6. 科研与课程知识互不相通，且默认研究生专属；
7. 无预习/复习/模拟考试等学习流程，无资料 S/A/P 权限体系。

---

## C. 当前存在的问题（映射到产品原则）

| # | 问题 | 与产品原则的冲突 |
| --- | --- | --- |
| C1 | 顶部“教师/学生/科研”被当作身份切换；教师进不了科研，学生进不了科研入口 | 原则 7：身份与工作模式分离 |
| C2 | 知识库是独立页面，非课程知识空间；无 S/A/P 三级资料与审核 | 原则 4、8、9 |
| C3 | RAG 无 source_level/visibility/owner 过滤，低可信资料可能覆盖官方资料 | 原则 9、38、39 |
| C4 | 学生端没有“我的课程→课程空间”学习主流程（预习/讲堂/作业/复习/模拟） | 原则 5、六～十六 |
| C5 | 个性化推荐为“score<60 → 章节卡”的静态规则，无证据解释 | 原则 18、52 |
| C6 | 学情分析有图表但缺“数据→AI 诊断→教学建议→采用→教学设计”闭环 | 原则 6、27、28 |
| C7 | AI 导师无课程上下文（当前课程/章节/资料范围） | 原则 37 |
| C8 | 研究空间缺论文对比、论文上传、课程↔科研互跳 | 原则 32～36 |
| C9 | 数据模型缺 CourseChapter / CourseKnowledgeSpace / KnowledgeReview / Quiz / LearningTask / LearningPlan / LearningRecord / ResearchDocument 等实体 | 原则 43 |
| C10 | 部分功能仍为硬编码演示（Mock 教材、规则推荐、无真实资料审核） | 原则 52、55 |

---

## D. 新产品架构建议

### D1. 身份 × 工作模式

```
用户身份（注册时确定）        可进入的工作模式
教师        → 教学 / 研究（可选学习）
本科生      → 学习 / 研究
研究生      → 学习 / 研究
```

顶部导航 = “当前工作模式”（教学 / 学习 / 研究），按身份显示可用模式；侧边栏按模式渲染。权限校验同时检查身份与模式。

### D2. 三大闭环

- 学习闭环：我的课程 → 课程空间（预习→讲堂→作业/实验→复习→模拟）→ 学习数据 → 画像/个性化计划
- 教学闭环：AI 教学设计 → 发布作业/资料 → 学情 → AI 教学诊断 → 教学建议 → 采用建议回填设计
- 科研闭环：研究方向 → 论文检索/上传 → 阅读/对比 → 前沿 → 研究资料；与课程知识双向跳转

### D3. 共享底座

课程知识空间（S/A/P 三级）+ RAG（带 source_level 过滤与优先级）+ LLM + Agent/Workflow + CodeJudgeService（现有，不动）+ 学习行为数据 + 学情分析 + 科研资料。

---

## E. 数据模型改造建议

### E1. 新增实体（Phase 2）

| 实体 | 说明 |
| --- | --- |
| CourseChapter | 课程章节（order、title、official 教材章节映射） |
| CourseKnowledgeSpace | 每门课程的知识空间配置（启用状态、默认资料范围） |
| KnowledgeReview | 学生共享资料审核记录（申请→通过/驳回/仅自己） |
| Quiz / QuizQuestion / QuizResult | 章节/模拟测验与作答结果（题型：单选/多选/判断/简答/算法/代码/SQL/综合） |
| LearningTask / LearningPlan / LearningRecord | 今日任务、个性化计划、学习行为记录 |
| ResearchDocument | 个人/课程科研资料（论文 PDF 等，默认私有） |
| UserResearchProfile | 研究方向画像 |

### E2. 改造实体

- `User`：role 语义改为 identity；新增 allowed_modes（或前端按身份推导）。
- `KnowledgePoint`：新增 related_points、aliases（如“婚姻匹配/稳定匹配”），支持前置知识链。
- `KnowledgeDocument / KnowledgeChunk`：新增 `course_id`、`source_level`（S/A/P）、`visibility`（official/shared/private）、`owner_id`、`page`、`document_type`、`approved_by`；metadata 保留 title/source/chapter/knowledge_point/year。
- `StudentKnowledgeProfile`：扩展 `evidence_count`、`confidence`、`success_count`、`last_updated`、`evidence_type`（作业/测验/代码/答疑）。
- `LearningRecommendation`：携带 evidence/reason 数据源（替代写死“优先级 5”）。
- `Submission/Question`：预留 quiz 来源标记（可选）。

### E3. 迁移策略

新增表用 `create_all`；已有表用现有 `_migrate` 机制 ALTER 补列；不删除既有数据；SQLite 保持单文件（后续可换 PostgreSQL）。

---

## F. 路由改造建议

前端按“模式 + 课程空间”重排（保留旧路径重定向兼容）：

```
学习模式 /learn
  /learn                   学生首页（今日建议/课程/薄弱点/任务）
  /learn/courses           我的课程
  /learn/courses/:courseId 课程学习空间（一级对象）
    /overview   课程首页（进度/本周建议/任务/薄弱点）
    /preview    课前预习
    /lecture    AI 课程讲堂（快速/标准/深度）
    /assignments 作业与实验
    /review     课后复习
    /exam       考前模拟
    /materials  课程资料（S/A/P）
    /qa         课程 AI 答疑（带来源范围选择）
  /learn/center  学习中心（画像/计划/错题/记录）
  /learn/tutor   全局 AI 学科导师

教学模式 /teach
  /teach                   教师首页
  /teach/courses           我的课程
  /teach/design            AI 教学设计
  /teach/diagnostics       教学诊断（数据→AI建议→采用）
  /teach/assignments       作业与实验
  /teach/knowledge         课程知识空间（S/A/P 管理+审核）
  /teach/reviews           资料审核

研究模式 /research
  /research                科研工作台
  /research/papers         论文阅读（选择/上传/分析）
  /research/compare        论文对比
  /research/frontier       前沿探索
  /research/materials      我的科研资料

共享：/workflows、/search、/assistant
兼容：/student/* → /learn/*、/teacher/* → /teach/*（重定向）
```

---

## G. 页面改造建议

### 学生端
- 首页：今天该学什么（综合掌握度、今日建议、薄弱知识点、当前课程、科研探索入口）。
- 我的课程：课程卡片含课程代码/学期/教师/进度/掌握度/当前章节/待办/最近学习；点击进入课程空间。
- 课程空间：8 个模块（首页/预习/讲堂/作业实验/复习/模拟/资料/答疑），构成完整学习流程。
- 学习中心：个人学习控制台（画像/进度/今日任务/计划/薄弱点/错题模式/学习记录/AI 学习规划师）。
- AI 学科导师：携带当前课程/章节/资料范围上下文；多模态输入预留接口。

### 教师端
- 首页：当前课程、教学进度、班级状态、薄弱点、AI 教学建议、待审核资料、下一节课建议。
- AI 教学设计：输入课程/章节/目标/水平/时长 + 班级学情 → 输出完整教案。
- 教学诊断：数据 → AI 诊断（哪里有问题/为什么/怎么调/补什么/是否加练/下节重点）→ “采用建议”进入设计。
- 课程知识空间：官方资料维护、共享资料审核（通过/驳回/仅自己）、分类、RAG 使用情况。

### 研究空间
- 工作台、论文阅读（选择/上传/分析+引用）、论文对比（结构化表格）、前沿、科研资料、AI 科研助手；
- 课程知识点 ↔ 论文双向跳转（“深入研究”/“回到课程知识”）。

---

## H. 开发顺序（每阶段运行+验证，不一次性堆代码）

| Phase | 内容 |
| --- | --- |
| 1 | 项目审查 + 架构设计（本文档） |
| 2 | 数据模型重构（新增实体 + 迁移） |
| 3 | 身份 × 工作模式重构（注册/登录/导航/权限） |
| 4 | 学生端“我的课程”+ 课程学习空间 |
| 5 | 学习中心重构（画像/计划/可解释推荐） |
| 6 | 教师端教学设计 + 教学诊断 |
| 7 | 课程知识空间 + S/A/P 权限 + 审核流 |
| 8 | RAG/LLM/Embedding 抽象层（metadata filtering + 来源优先级） |
| 9 | 研究空间扩展（对比/上传/双向跳转） |
| 10 | 跨模块联动 |
| 11 | UI/UX 统一 |
| 12 | 测试与 Bug 修复 |

---

## Phase 1 具体修改清单（本轮）

1. 本架构文档落盘（docs/ARCHITECTURE-REDESIGN.md）。
2. 建立 docs/ROADMAP.md：把 Phase 2–12 拆成可勾选任务清单。
3. 暂不修改业务代码；保留当前项目可运行。
4. 确认后进入 Phase 2（数据模型重构）。

## 明确复用 / 重构 / 保持 Mock

- **复用**：认证、课程邀请、作业/提交/批改、代码评测（不改）、画像、导师问答、知识库 CRUD+异步上传+OCR+批量导入、TF-IDF 检索、工作流引擎、教案历史、科研论文/前沿。
- **重构**：导航（身份×模式）、学生“我的课程→课程空间”、学习中心、教师教学设计/诊断、知识库→课程知识空间（S/A/P+审核）、RAG metadata 过滤与来源优先级、AI 导师课程上下文。
- **保持 Mock（结构真实）**：测验题库、预习/复习/模拟生成（走 Agent/Workflow）、论文库（预留真实检索接口）、学情 AI 诊断文案。

