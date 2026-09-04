# 重构路线图（Phase 2–12 任务清单）

## Phase 2：数据模型重构
- [x] 新增 CourseChapter、CourseKnowledgeSpace、KnowledgeReview、Quiz、QuizQuestion、QuizResult
- [x] 新增 LearningTask、LearningPlan、LearningRecord、ResearchDocument、UserResearchProfile
- [x] KnowledgePoint 增加 related_points / aliases / chapter_id
- [x] KnowledgeDocument/Chunk 增加 course_id / source_level / visibility / owner_id / page / document_type / approved_by
- [x] StudentKnowledgeProfile 增加 evidence_count / confidence / success_count / evidence_type
- [x] 迁移脚本（create_all + ALTER + 回填），不删数据；seed：7 门课 × 3~6 章，知识点关联章节

## Phase 3：身份 × 工作模式
- [x] 注册支持身份（教师/本科生/研究生），账号带可用模式
- [x] 顶部模式切换（教学/学习/研究）+ 身份校验
- [x] 路由 /teach、/learn、/research + 旧路径重定向

## Phase 4：学生端课程空间
- [x] 我的课程卡片增强（进度/掌握度/当前章节/待办）
- [x] 课程空间框架（8 模块）与课程首页
- [x] 课前预习流程（目标/预备知识/核心概念/预习题/检查 + 学习记录）
- [x] AI 课程讲堂（快速/标准/深度 + 结构化章节 + 练习/检查）
- [x] 课程资料页（S/A/P 展示）与个人资料上传（仅我/申请共享）

## Phase 5：学习中心
- [x] 学习画像（跨课程掌握度/薄弱点证据/今日任务）
- [x] 可解释个性化任务与计划（evidence 驱动：次数/错误/掌握度/截止）
- [x] AI 学习规划师入口（导师页）

## Phase 6：教师端
- [x] AI 教学设计（学生水平/教学时长/班级学情输入）
- [x] 教学诊断（数据→AI 诊断→教学建议→采用→回填设计）
- [x] 教师首页（课程/状态/待审核资料/建议）

## Phase 7：课程知识空间
- [x] S/A/P 三级资料维护（上传/编辑/删除 + 等级徽标）
- [x] 学生共享资料申请 → 教师审核（通过/驳回/仅自己）
- [x] RAG 按课程与资料等级/所有者过滤

## Phase 8：RAG/LLM/Embedding 抽象层
- [x] EmbeddingService 接口（embed_text/embed_documents + Hash 实现）
- [x] RAGService 增加 retrieve_context、source_level/visibility/owner 过滤
- [x] 来源冲突提示（“已优先采用课程官方资料”）

## Phase 9：研究空间
- [x] 科研资料上传（私有）+ 论文阅读分析（引用/依据 + 回到课程知识）
- [x] 论文对比（结构化表格）
- [x] 课程知识点 ↔ 论文双向跳转（深入研究/回到课程知识）

## Phase 10：跨模块联动
- [x] 学情 → 教学设计；资料审核 → 课程 RAG（重新入库）；作业/测验 → 画像 → 计划
- [x] 课程 ↔ 科研互跳

## Phase 11：UI/UX 统一
- [x] 三模式导航、课程空间信息架构、旧路由兼容重定向、错误边界

## Phase 12：测试与修复
- [x] 44 个测试全绿（新增课程空间/测验/资料审核/诊断/论文对比/知识点关联）
- [ ] 端到端冒烟与回归（随演示持续进行）
