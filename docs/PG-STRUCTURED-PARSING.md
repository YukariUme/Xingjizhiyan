# PostgreSQL 切换 + 复杂教材结构化解析

## 1. 数据库：SQLite → PostgreSQL（已完成真实切换）

### 环境
- PostgreSQL 17（Windows，本机已装）：仓库内独立实例，端口 **5433**，用户 `jbgs`（超级用户，trust 认证），库 `jbgs`。
- 数据目录：`backend/data/pgdata`（仓库内，可随项目迁移）。
- 启动（管理员/普通终端均可）：

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\postgres.exe' -D 'D:\MyStudy\2026Summer\jbgs\backend\data\pgdata' -p 5433
```

### pgvector（0.8.6，PG17）
Windows 无官方预编译，已从社区预编译包（github.com/andreiramani/pgvector_pgsql_windows）安装：
- DLL：`backend/data/pgvector/lib/vector.dll`
- 扩展 SQL：`backend/data/pgvector/share/extension/*`
- 因 `CREATE EXTENSION` 需要写 Program Files（无管理员权限），采用**手动 SQL 注册**：
  `backend/data/pgvector/vector_install.sql`（已把 `MODULE_PATHNAME` 指向仓库内 DLL）。
- 验证：`SELECT to_regtype('vector'), '[1,2,3]'::vector;`

> 如果换机器：把 `backend/data/pgvector` 一起拷贝；新库执行
> `psql -f backend/data/pgvector/vector_install.sql` 即可，无需管理员。

### 配置
`.env`：`DATABASE_URL=postgresql+psycopg://jbgs@127.0.0.1:5433/jbgs`，`RAG_PROVIDER=auto`。
测试仍强制 SQLite（`tests/conftest.py`），不影响开发库。

### 数据迁移
```powershell
cd backend
$env:SOURCE_SQLITE='sqlite:///D:/MyStudy/2026Summer/jbgs/backend/data/jbgs.db'
$env:DATABASE_URL='postgresql+psycopg://jbgs@127.0.0.1:5433/jbgs'
python -m scripts.migrate_pg
```
脚本已处理：源表缺失跳过、bool/json/timestamp 类型规范化、NOT NULL 缺列补默认、
目标表无的列忽略、迁移后自增序列同步（避免新插入撞主键）。

### RAG：PostgresRAGService
- `app/services/rag/postgres.py`：pgvector 余弦候选池（≤300）→ 0.75 语义 + 0.25 词法
  + 关键词奖励 + 元数据加权 + 严格特征词门控（与本地混合检索同语义）。
- pgvector 不可用/未写入向量时自动回退内存混合检索（接口不变）。
- `ingest_document` 写入 `embedding_vector vector(512)`；HNSW 索引在 `_migrate` 自动创建。

## 2. 复杂教材结构化解析管线

```
              Document Ingestion
                     │
    ┌────────────────┼────────────────┐
    ↓                ↓                ↓
  有文字层         无文字层          PPT/Word
    ↓                ↓                ↓
 Native Parser   Layout + OCR    Native Parser
    │
    ┌──────────────┼──────────────┐
    ↓              ↓              ↓
   表格            公式            代码
    ↓              ↓              ↓
 Table Parser  Formula OCR    Code Parser
    └──────────────┼──────────────┘
                   ↓
             结构化文档（title/heading/paragraph/table/formula/code）
                   ↓
          Chunk + Metadata（block_type/page/language）→ Embedding → pgvector → RAG
```

### 新增模块
- `app/services/ocr/`：OCR Provider 抽象（`OCR_PROVIDER=auto|rapid|paddle|mock`）。
  - `rapid.py`：RapidOCR（ONNX，默认）；`paddle.py`：PaddleOCR 预留；`mock.py`：演示/测试。
- `app/services/parsing/`：
  - `blocks.py`：`StructuredBlock` / `ParsedDocument`（块类型 + 页码 + 来源）。
  - `layout.py`：RapidLayout 版面检测（title/text/table/formula/figure 区域）。
  - `table.py`：文字层用 pdfplumber 提取原生表格；扫描层用 RapidTable（HTML→Markdown），失败回退行合并。
  - `formula.py`：RapidLaTeXOCR 惰性封装（见下方评估结论），失败保留原文标记。
  - `code.py`：代码块/语言启发式识别（缩进 + 关键词 + 标点特征）。
  - `office.py`：PPTX/DOCX 结构化（段落/表格/代码块）。
  - `pipeline.py`：`parse_document_file(path)` 入口，按文件类型分流。
- 入库：`knowledge_jobs._parse_with_progress` 解析出结构化块 → `doc.metadata_json.blocks` →
  RAG `_chunks_for_document` 按块切分（表格/公式/代码保整），chunk metadata 含 `block_type/page/language`。

### RapidLayout / RapidTable / RapidLaTeXOCR 评估结论
| 组件 | 结论 | 状态 |
| --- | --- | --- |
| RapidLayout | 可解决版面错乱：扫描页先按区域分类，表格/公式/正文分路，避免整页 OCR 串行。CDLA 模型 `pp_layout_cdla` 首次使用自动下载。 | ✅ 已接入（加载失败自动退化为整页 OCR） |
| RapidTable | 可解决扫描表格：`RapidTable(use_ocr=False)` + 外部 OCR 行结果还原单元格；输出 HTML 转 Markdown。模型 SLANET+ 首次使用自动下载。 | ✅ 已接入（失败回退行合并） |
| RapidLaTeXOCR | **PyPI 无 `rapid_latex_ocr` 包**（文档与 PyPI 不一致）；需 GitHub 源码安装 + 单独下载模型（>100MB）；Python ≥3.13 的版本缺失。结论：**暂不默认安装**，接口已预留，安装后自动启用。 | ⏳ 接口就绪，待安装 |

### 安装依赖
```powershell
python -m pip install -r backend/requirements-ocr.txt
```

### 测试
`tests/test_parsing.py`：OCR 工厂、文字层 PDF、扫描 PDF（Mock OCR）、DOCX、结构化切分、表格 HTML→Markdown。
