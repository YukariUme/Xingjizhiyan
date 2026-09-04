# 平台架构

## 业务闭环

```
教学（智能备课 / 发布作业）
   │
   ▼
学习（作业 / 编程评测 / AI 导师）
   │
   ▼
学习数据（提交 / 测试 / 批改结果）
   │
   ▼
学情分析（班级正确率 / 高频错误知识点）
   │
   ▼
知识巩固（薄弱知识点 → 个性化学习路径）
   │
   ▼
科研探索（知识点 → 相关论文 / 前沿追踪）
```

## 分层结构

```text
backend/
  api/           HTTP 路由 + RBAC 依赖
  services/      业务逻辑（分层于路由之上）
    llm/         LLMService 抽象 + Mock/DeepSeek 实现 + 工厂
    rag/         RAGService 抽象 + 本地检索实现 + 工厂
    agent/       AgentService 抽象 + 教学/学习/科研 Agent + 工厂
    judge/       CodeJudgeService 抽象 + Mock 评测 + 工厂
  models/        SQLAlchemy 实体
  repositories/  数据访问层
  schemas/       Pydantic 请求/响应模型
  mock/          知识库 / 论文 / 试题等演示数据
  analytics/     学情统计与个性化路径（规则 + Mock）
frontend/
  src/api/       API 客户端
  src/pages/     按角色组织页面
  src/components/ 通用组件 + AI 对话组件 + SVG 图表
```

## 关键设计

1. **AI 不是最终裁判**：主观题由 Mock LLM 给出建议分与理由，教师审核确认后才成为正式成绩。
2. **评测可替换**：`CodeJudgeService.judge(source, language, test_cases)` 返回统一 `JudgeResult`，未来替换为沙箱无需改业务代码。
3. **知识可追溯**：所有 AI 回答附带知识库引用（文档标题、章节、来源），为 RAG 接入预留同一响应结构。
4. **角色数据隔离**：学生只能读写自己的提交；教师只能访问自己课程的班级数据；科研数据默认私有。
5. **配置切换**：`LLM_PROVIDER=mock` 可切换为 `deepseek`，密钥只存在于 `.env`。
6. **知识库可运营**：提供文档 CRUD + txt/md/pdf 上传 + 重新切分索引接口，管理员/教师在界面上即可扩充知识资产，新增内容立即进入 RAG 检索与 AI 引用。

## 知识库管理设计

知识库是平台唯一的内容底座，管理界面（教师/科研）与业务侧共用同一套接口：

```text
管理界面/上传文件（txt · md · pdf）
        │
        ▼
KnowledgeDocument（统一 metadata：course/topic/chapter/difficulty/type/year/source）
        │
        ▼
KnowledgeService.create/update/delete → RAGService.ingest_document
        │
        ▼
段落级切分 + 哈希向量化 → KnowledgeChunk 入库
        │
        ▼
AI 导师 / 备课 / 论文分析 / 前沿探索 / 全局搜索 → search + rerank + 来源引用
```

删除文档会级联删除切片，避免检索到失效内容；上传仅允许 txt/md/pdf，大小上限由 `MAX_UPLOAD_MB` 配置
（默认 200MB，188MB 级整本教材可直接上传），大文件采用流式落盘后解析；TF-IDF 索引使用进程级缓存，
避免大语料入库后每次搜索都重建索引。
