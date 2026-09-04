/** 知识库管理：分类浏览、手动新增/上传/编辑/删除文档、知识点管理。 */

import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { Modal, Tabs, useAsync, EmptyState, ErrorBanner, Loading, Badge, Progress } from "../../components/ui";
import type { Course, KnowledgeDoc, KnowledgeJob, KnowledgePoint } from "../../types";

const COURSES = ["全部", "数据结构", "算法设计与分析", "操作系统", "计算机网络", "数据库系统", "人工智能"];
const TYPES = ["讲义", "教材", "论文精读", "实验", "规范"];
const DIFFICULTY = ["易", "中", "难"];

interface DocForm {
  title: string;
  course: string;
  topic: string;
  chapter: string;
  source: string;
  difficulty: string;
  type: string;
  year: number;
  content: string;
}

const emptyForm: DocForm = {
  title: "",
  course: "数据结构",
  topic: "",
  chapter: "",
  source: "",
  difficulty: "中",
  type: "讲义",
  year: 2026,
  content: "",
};

function CoursePicker({
  value,
  onChange,
  options,
  canCreate,
  onCreate,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  canCreate: boolean;
  onCreate: () => void;
}) {
  return (
    <div className="row" style={{ gap: 6 }}>
      <input
        className="input grow"
        list="kb-course-options"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="选择或输入课程名称"
      />
      <datalist id="kb-course-options">
        {options.map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
      {canCreate && (
        <button type="button" className="btn btn-sm" onClick={onCreate} title="创建课程（创建课程的第一步）">
          ＋ 新建课程
        </button>
      )}
    </div>
  );
}

function formatChars(n: number): string {
  if (n >= 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)}MB`;
  if (n >= 1024) return `${(n / 1024).toFixed(1)}KB`;
  return `${n}B`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function TeacherKnowledge() {
  const { user } = useAuth();
  const [tab, setTab] = useState("docs");
  const [course, setCourse] = useState("全部");
  const [docType, setDocType] = useState("");
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("time");
  const [order, setOrder] = useState("desc");
  const docs = useAsync<KnowledgeDoc[]>(
    () => {
      const params = new URLSearchParams();
      if (course !== "全部") params.set("course", course);
      if (docType) params.set("type", docType);
      if (q) params.set("q", q);
      params.set("sort", sort);
      params.set("order", order);
      const qs = params.toString();
      return api.get(`/knowledge/documents${qs ? `?${qs}` : ""}`);
    },
    [course, docType, q, sort, order]
  );
  const subjects = useAsync<Array<{ course: string; doc_count: number }>>(() => api.get("/knowledge/subjects"));
  const points = useAsync<KnowledgePoint[]>(() => api.get("/knowledge/points"));
  const platformCourses = useAsync<Course[]>(() => api.get("/courses"));
  const importScan = useAsync<{ dir: string; files: Array<{ filename: string; size_mb: number; imported: boolean; document_id: number | null }> }>(
    () => api.get("/knowledge/import/scan")
  );
  const jobs = useAsync<KnowledgeJob[]>(() => api.get("/knowledge/jobs"));
  const reviews = useAsync<Array<{ id: number; document_id: number; title: string; course: string; requester: string; status: string; created_at: string }>>(
    () => api.get("/knowledge/reviews?status=pending")
  );

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<KnowledgeDoc | null>(null);
  const [form, setForm] = useState<DocForm>(emptyForm);
  const [selected, setSelected] = useState<KnowledgeDoc | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const ragStats = useAsync<{
    total_documents: number;
    total_hits: number;
    source_levels: Record<string, number>;
    top_documents: Array<{ id: number; title: string; course: string; source_level: string; hits: number }>;
  }>(() => api.get("/knowledge/stats"));
  const [uploading, setUploading] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadForm, setUploadForm] = useState<DocForm>(emptyForm);
  const [importSel, setImportSel] = useState<string[]>([]);
  const [importCourse, setImportCourse] = useState("数据结构");
  const [importBusy, setImportBusy] = useState(false);
  const [importMsg, setImportMsg] = useState("");
  const [courseOptions, setCourseOptions] = useState<string[]>([]);
  const [newCourseOpen, setNewCourseOpen] = useState(false);
  const [newCourseForm, setNewCourseForm] = useState({ name: "", code: "", semester: "2026 春季" });
  const [newCourseBusy, setNewCourseBusy] = useState(false);
  const [reviewBusy, setReviewBusy] = useState(false);
  const hadActiveJob = useRef(false);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...emptyForm, course: course !== "全部" ? course : "数据结构" });
    setNotice("");
    setOpen(true);
  };

  const openUpload = () => {
    setUploadFile(null);
    setUploadForm({ ...emptyForm, course: course !== "全部" ? course : "数据结构" });
    setNotice("");
    setUploadOpen(true);
  };

  const createCourse = async () => {
    if (!newCourseForm.name.trim() || !newCourseForm.code.trim()) return;
    setNewCourseBusy(true);
    try {
      const created = await api.post<Course>("/courses", newCourseForm);
      setCourseOptions((opts) => Array.from(new Set([...opts, created.name])));
      setForm((f) => ({ ...f, course: created.name }));
      setUploadForm((f) => ({ ...f, course: created.name }));
      subjects.refresh();
      setNewCourseOpen(false);
      setNewCourseForm({ name: "", code: "", semester: "2026 春季" });
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "创建课程失败");
    } finally {
      setNewCourseBusy(false);
    }
  };

  useEffect(() => {
    if (platformCourses.data) {
      const names = platformCourses.data.map((c) => c.name);
      setCourseOptions((opts) =>
        Array.from(
          new Set([...opts, ...(names.length ? names : COURSES.filter((c) => c !== "全部"))])
        )
      );
    }
  }, [platformCourses.data]);

  // 后台任务轮询：有任务时每 3 秒刷新进度；任务全部结束后刷新文档列表
  useEffect(() => {
    const timer = setInterval(() => {
      jobs.refresh();
    }, 3000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const active = (jobs.data ?? []).some((j) => j.status === "running" || j.status === "pending");
    if (hadActiveJob.current && !active) {
      docs.refresh?.();
      importScan.refresh();
      subjects.refresh();
    }
    hadActiveJob.current = active;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs.data]);

  const openEdit = (d: KnowledgeDoc) => {
    setEditing(d);
    setForm({
      title: d.title,
      course: d.course,
      topic: d.topic,
      chapter: d.chapter,
      source: d.source,
      difficulty: d.difficulty,
      type: d.type,
      year: d.year,
      content: d.content,
    });
    setNotice("");
    setOpen(true);
  };

  const save = async () => {
    setBusy(true);
    setNotice("");
    try {
      if (editing) {
        await api.put(`/knowledge/documents/${editing.id}`, form);
        setNotice("已保存并重新索引");
      } else {
        await api.post("/knowledge/documents", form);
        setNotice("已创建并自动切分索引");
      }
      setOpen(false);
      docs.refresh?.();
      subjects.refresh();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "保存失败");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (d: KnowledgeDoc) => {
    if (!window.confirm(`确认删除「${d.title}」？相关切片与索引将一并删除。`)) return;
    await api.delete(`/knowledge/documents/${d.id}`);
    setSelected(null);
    docs.refresh?.();
    subjects.refresh();
  };

  const doUpload = async () => {
    if (!uploadFile) {
      setNotice("请先选择文件");
      return;
    }
    setUploading(true);
    setNotice("");
    try {
      const fd = new FormData();
      fd.append("file", uploadFile);
      fd.append("title", uploadForm.title || uploadFile.name);
      fd.append("course", uploadForm.course);
      fd.append("topic", uploadForm.topic);
      fd.append("chapter", uploadForm.chapter);
      fd.append("source", uploadForm.source || uploadFile.name);
      fd.append("difficulty", uploadForm.difficulty);
      fd.append("type", uploadForm.type);
      fd.append("year", String(uploadForm.year));
      const res = await api.upload<{ job_id: number; message: string }>("/knowledge/upload", fd);
      setUploadOpen(false);
      setUploadFile(null);
      setNotice(`已提交后台处理（任务 #${res.job_id}），可在页面上方查看进度`);
      jobs.refresh();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "上传失败");
    } finally {
      setUploading(false);
    }
  };

  const reindexAll = async () => {
    setBusy(true);
    try {
      const res = await api.post<{ documents: number; chunks: number }>("/knowledge/reindex-all", {});
      window.alert(`重建完成：${res.documents} 个文档 / ${res.chunks} 个切片`);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "重建失败");
    } finally {
      setBusy(false);
    }
  };

  const reviewAction = async (id: number, action: string) => {
    setReviewBusy(true);
    try {
      await api.post(`/knowledge/reviews/${id}`, { action });
      reviews.refresh();
      docs.refresh?.();
      subjects.refresh();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "操作失败");
    } finally {
      setReviewBusy(false);
    }
  };

  const runImport = async () => {
    const targets = importSel.length
      ? importSel
      : (importScan.data?.files ?? []).filter((f) => !f.imported).map((f) => f.filename);
    if (targets.length === 0) {
      setImportMsg("没有可导入的文件");
      return;
    }
    setImportBusy(true);
    setImportMsg("");
    try {
      const res = await api.post<{ job_id: number }>(
        "/knowledge/import/run",
        { course: importCourse, files: targets }
      );
      setImportMsg(`已提交后台任务 #${res.job_id}，可继续浏览或使用其他功能`);
      jobs.refresh();
    } catch (e) {
      setImportMsg(e instanceof Error ? e.message : "提交失败");
    } finally {
      setImportBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>知识库管理</h1>
          <p>按学科分类维护讲义与资料，新增/上传后自动切分并建立 RAG 索引，供 AI 检索引用</p>
        </div>
        <div className="row">
          <button className="btn" onClick={openUpload}>⬆ 上传文件</button>
          <button className="btn" onClick={() => void reindexAll()} disabled={busy}>⟳ 全量重建索引</button>
          <button className="btn btn-primary" onClick={openCreate}>＋ 手动新增</button>
        </div>
      </div>

      {notice && <div className="badge green mb-16">{notice}</div>}

      {ragStats.data && (
        <div className="grid grid-4 mb-16">
          <div className="card stat-card">
            <div className="stat-label">知识文档</div>
            <div className="stat-value">{ragStats.data.total_documents}</div>
          </div>
          <div className="card stat-card">
            <div className="stat-label">RAG 累计命中</div>
            <div className="stat-value">{ragStats.data.total_hits}</div>
            <div className="stat-hint">AI 答疑/讲堂实际引用次数</div>
          </div>
          <div className="card stat-card">
            <div className="stat-label">来源等级分布</div>
            <div className="stat-value" style={{ fontSize: 18 }}>
              {Object.entries(ragStats.data.source_levels)
                .map(([k, v]) => `${k}:${v}`)
                .join(" · ") || "—"}
            </div>
          </div>
          <div className="card stat-card">
            <div className="stat-label">Top 命中文档</div>
            <div className="stat-value" style={{ fontSize: 16 }}>
              {ragStats.data.top_documents.slice(0, 3).map((d) => (
                <div key={d.id} style={{ fontWeight: 500, lineHeight: 1.5 }}>
                  {d.title.slice(0, 16)}… × {d.hits}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {(jobs.data ?? []).length > 0 && (
        <div className="card mb-16">
          <div className="card-title">
            <h3>后台任务（上传 / 导入）</h3>
            <button className="btn btn-sm" onClick={jobs.refresh}>⟳ 刷新</button>
          </div>
          {jobs.data?.map((j) => (
            <div key={j.id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <div className="grow">
                <b>{j.filename || (j.kind === "import" ? "批量导入" : "上传")}</b>
                <div className="small muted">{j.message || j.status}</div>
                {j.error && <div className="small" style={{ color: "var(--danger)" }}>{j.error}</div>}
              </div>
              <div className="row" style={{ width: 240 }}>
                <Progress
                  value={j.progress}
                  tone={j.status === "failed" ? "red" : j.status === "success" ? "green" : "auto"}
                />
                <span className={`badge ${j.status === "success" ? "green" : j.status === "failed" ? "red" : j.status === "running" ? "orange" : "gray"}`}>
                  {{ success: "完成", failed: "失败", running: "处理中", pending: "排队中" }[j.status] ?? j.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <Tabs
        items={[
          { key: "docs", label: "文档管理" },
          { key: "points", label: "知识点管理" },
          { key: "import", label: "批量导入" },
          { key: "reviews", label: `资料审核${reviews.data?.length ? `（${reviews.data.length}）` : ""}` },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "docs" ? (
        <div className="kb-layout">
          <div>
            <div className="card">
              <h3 className="mb-16">学科分类</h3>
              <div
                className={`kb-tree-item ${course === "全部" ? "active" : ""}`}
                onClick={() => setCourse("全部")}
              >
                <span>全部</span>
                <span className="small muted">
                  {subjects.data?.reduce((s, x) => s + x.doc_count, 0) ?? 0}
                </span>
              </div>
              {(subjects.data ?? []).map((item) => (
                <div
                  key={item.course}
                  className={`kb-tree-item ${course === item.course ? "active" : ""}`}
                  onClick={() => setCourse(item.course)}
                >
                  <span>{item.course}</span>
                  <span className="small muted">{item.doc_count}</span>
                </div>
              ))}
            </div>
            <div className="card mt-16">
              <h3 className="mb-8">说明</h3>
              <p className="small muted" style={{ margin: 0 }}>
                文档内容将按段落切分并向量化；AI 回答会自动引用这里入库的文档来源，实现内容可追溯。
              </p>
            </div>
          </div>

          <div>
            <div className="card mb-16">
              <div className="row wrap" style={{ gap: 8 }}>
                <div className="row grow" style={{ gap: 6 }}>
                  <input
                    className="input grow"
                    placeholder="搜索标题 / 内容 / 来源…"
                    value={qInput}
                    onChange={(e) => setQInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && setQ(qInput.trim())}
                  />
                  <button className="btn" onClick={() => setQ(qInput.trim())}>搜索</button>
                  {q && <button className="btn btn-sm" onClick={() => { setQ(""); setQInput(""); }}>清除</button>}
                </div>
                <select className="select" style={{ width: 150 }} value={docType} onChange={(e) => setDocType(e.target.value)}>
                  <option value="">全部类型</option>
                  {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
                <select className="select" style={{ width: 150 }} value={sort} onChange={(e) => setSort(e.target.value)}>
                  <option value="time">按时间</option>
                  <option value="size">按大小</option>
                </select>
                <button className="btn" onClick={() => setOrder(order === "desc" ? "asc" : "desc")} title="切换正序/倒序">
                  {order === "desc" ? "↓ 倒序" : "↑ 正序"}
                </button>
              </div>
              <div className="small muted mt-8">
                共 {docs.data?.length ?? 0} 个文档
                {course !== "全部" && ` · 课程：${course}`}
                {docType && ` · 类型：${docType}`}
              </div>
            </div>
            {docs.loading ? (
              <Loading />
            ) : !docs.data || docs.data.length === 0 ? (
              <EmptyState text="当前筛选条件下没有文档" />
            ) : (
              docs.data.map((d) => (
                <div key={d.id} className="doc-row" onClick={() => setSelected(d)}>
                  <div className="doc-icon">📄</div>
                  <div className="grow">
                    <div className="doc-title">{d.title}</div>
                    <div className="doc-meta">
                      <span className={`badge ${d.source_level === "S" ? "green" : d.source_level === "A" ? "orange" : "purple"}`}>
                        [{d.source_level ?? "S"}]
                      </span>
                      {" "}
                      <span className={`badge ${d.type === "教材" ? "purple" : d.type === "实验" ? "orange" : "gray"}`}>{d.type}</span>
                      {" "}{d.course} · {d.topic || "未分类题"} · {d.chapter} · {d.year} · {d.source}
                    </div>
                    <div className="small muted mt-8" style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>
                      文本 {formatChars(d.size_chars)} · {d.chunk_count} 切片 · {formatDate(d.created_at)} · 难度 {d.difficulty}
                    </div>
                  </div>
                  <div className="row" onClick={(e) => e.stopPropagation()}>
                    <button className="btn btn-sm" onClick={() => openEdit(d)}>编辑</button>
                    <button className="btn btn-sm btn-danger" onClick={() => void remove(d)}>删除</button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      ) : tab === "import" ? (
        <div className="card">
          <div className="card-title">
            <h3>批量导入教材（目录扫描）</h3>
            <button className="btn btn-sm" onClick={importScan.refresh}>⟳ 刷新</button>
          </div>
          <p className="small muted">
            把合法拥有的教材 PDF / txt 放进目录：<span className="mono">{importScan.data?.dir ?? "…"}</span>
            ，然后在下方选择课程、勾选文件后一键导入。已导入的文件会跳过；
            文字版 PDF 秒级解析，扫描版自动 OCR（较慢）。
          </p>
          <div className="row wrap mb-16">
            <select
              className="select"
              style={{ width: 200 }}
              value={importCourse}
              onChange={(e) => setImportCourse(e.target.value)}
            >
              {COURSES.filter((c) => c !== "全部").map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
            <button className="btn btn-primary" onClick={() => void runImport()} disabled={importBusy}>
              {importBusy ? "导入解析中…" : "导入所选文件"}
            </button>
          </div>
          {importMsg && <div className="small mb-16" style={{ color: "var(--success)" }}>{importMsg}</div>}
          {importScan.loading ? (
            <Loading />
          ) : !importScan.data || importScan.data.files.length === 0 ? (
            <EmptyState
              emoji="📁"
              text="目录为空：把教材 PDF/txt 放进上面的文件夹后点「刷新」"
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>文件名</th>
                    <th>大小</th>
                    <th>状态</th>
                    <th>
                      <input
                        type="checkbox"
                        checked={importScan.data.files.every((f) => f.imported || importSel.includes(f.filename))}
                        onChange={(e) =>
                          setImportSel(
                            e.target.checked
                              ? importScan.data!.files.filter((f) => !f.imported).map((f) => f.filename)
                              : []
                          )
                        }
                      />
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {importScan.data.files.map((f) => (
                    <tr key={f.filename}>
                      <td><b>{f.filename}</b></td>
                      <td className="mono">{f.size_mb}MB</td>
                      <td>
                        {f.imported ? (
                          <Badge tone="green">已导入</Badge>
                        ) : (
                          <Badge tone="orange">待导入</Badge>
                        )}
                      </td>
                      <td>
                        <input
                          type="checkbox"
                          disabled={f.imported}
                          checked={importSel.includes(f.filename)}
                          onChange={(e) =>
                            setImportSel((sel) =>
                              e.target.checked
                                ? [...sel, f.filename]
                                : sel.filter((n) => n !== f.filename)
                            )
                          }
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {jobs.data?.find((j) => j.kind === "import" && Array.isArray(j.result?.results)) && (
            <div className="mt-16">
              <h3>导入结果</h3>
              {jobs.data!
                .find((j) => j.kind === "import" && Array.isArray(j.result?.results))!
                .result.results!.map((r, i) => (
                <div key={i} className="row space-between" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                  <span className="small">{r.filename}</span>
                  <span className={`badge ${r.status === "imported" ? "green" : r.status === "failed" ? "red" : "gray"}`}>
                    {{ imported: "✓ 已导入", failed: "失败", skipped: "跳过" }[r.status] ?? r.status}
                  </span>
                </div>
              ))}
              {jobs.data!
                .find((j) => j.kind === "import" && Array.isArray(j.result?.results))!
                .result.results!.some((r) => r.status === "failed") && (
                <div className="small muted mt-8">
                  失败原因：
                  {jobs.data!
                    .find((j) => j.kind === "import" && Array.isArray(j.result?.results))!
                    .result.results!.filter((r) => r.status === "failed")
                    .map((r) => r.reason)
                    .join("；")}
                </div>
              )}
            </div>
          )}
        </div>
      ) : tab === "reviews" ? (
        <div className="card">
          <div className="card-title">
            <h3>学生共享资料审核</h3>
            <button className="btn btn-sm" onClick={reviews.refresh}>⟳ 刷新</button>
          </div>
          <p className="small muted mb-16">
            学生申请加入课程共享的资料会进入审核队列：通过后成为 [A] 级共享资料并被其他学生 RAG 使用；驳回则保持个人私有。
          </p>
          {reviews.loading ? (
            <Loading />
          ) : !reviews.data || reviews.data.length === 0 ? (
            <EmptyState emoji="📭" text="暂无待审核资料" />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>资料</th><th>课程</th><th>申请人</th><th>提交时间</th><th>操作</th></tr>
                </thead>
                <tbody>
                  {reviews.data.map((r) => (
                    <tr key={r.id}>
                      <td><b>{r.title}</b></td>
                      <td>{r.course}</td>
                      <td>{r.requester}</td>
                      <td className="small muted">{new Date(r.created_at).toLocaleString("zh-CN")}</td>
                      <td>
                        <div className="row">
                          <button className="btn btn-sm btn-primary" disabled={reviewBusy} onClick={() => void reviewAction(r.id, "approve")}>通过</button>
                          <button className="btn btn-sm" disabled={reviewBusy} onClick={() => void reviewAction(r.id, "private")}>仅自己</button>
                          <button className="btn btn-sm btn-danger" disabled={reviewBusy} onClick={() => void reviewAction(r.id, "reject")}>驳回</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="card">
          {points.loading ? (
            <Loading />
          ) : points.error ? (
            <ErrorBanner message={points.error} />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>知识点</th><th>学科</th><th>章节</th><th>难度</th><th>说明</th></tr>
                </thead>
                <tbody>
                  {points.data?.map((p) => (
                    <tr key={p.id}>
                      <td><b>{p.name}</b></td>
                      <td><Badge tone="purple">{p.subject}</Badge></td>
                      <td className="small">{p.chapter}</td>
                      <td><Badge tone={p.difficulty === "难" ? "red" : p.difficulty === "易" ? "green" : "gray"}>{p.difficulty}</Badge></td>
                      <td className="small muted">{p.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 详情抽屉（点击文档行） */}
      {selected && (
        <Modal title={selected.title} open onClose={() => setSelected(null)}
          footer={<button className="btn" onClick={() => setSelected(null)}>关闭</button>}>
          <div className="row wrap mb-8">
            <Badge>{selected.course}</Badge>
            <Badge tone="purple">{selected.topic}</Badge>
            <Badge tone="gray">{selected.chapter}</Badge>
            <Badge tone="gray">{selected.type} · {selected.year}</Badge>
            <Badge tone={selected.difficulty === "难" ? "red" : "green"}>{selected.difficulty}</Badge>
          </div>
          <p className="small muted">来源：{selected.source || "平台录入"}</p>
          <div className="code-block" style={{ maxHeight: 340, overflow: "auto", whiteSpace: "pre-wrap" }}>
            {selected.content}
          </div>
        </Modal>
      )}

      {/* 新增 / 编辑表单 */}
      <Modal
        title={editing ? `编辑：${editing.title}` : "手动新增知识文档"}
        open={open}
        onClose={() => setOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={() => void save()} disabled={busy || !form.title || !form.content}>
              {busy ? "保存中…" : editing ? "保存修改" : "创建文档"}
            </button>
          </>
        }
      >
        {notice && <div className="badge green mb-8">{notice}</div>}
        <div className="form-grid">
          <div className="field">
            <label>文档标题 *</label>
            <input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="field">
            <label>学科分类 *</label>
            <CoursePicker
              value={form.course}
              onChange={(v) => setForm({ ...form, course: v })}
              options={courseOptions}
              canCreate={user?.role === "teacher"}
              onCreate={() => setNewCourseOpen(true)}
            />
          </div>
          <div className="field">
            <label>主题（知识点）</label>
            <input className="input" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} placeholder="如：二叉树" />
          </div>
          <div className="field">
            <label>章节</label>
            <input className="input" value={form.chapter} onChange={(e) => setForm({ ...form, chapter: e.target.value })} placeholder="如：第 4 章" />
          </div>
          <div className="field">
            <label>来源</label>
            <input className="input" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} placeholder="如：《数据结构》讲义" />
          </div>
          <div className="field">
            <label>类型</label>
            <select className="select" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
              {TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div className="field">
            <label>难度</label>
            <select className="select" value={form.difficulty} onChange={(e) => setForm({ ...form, difficulty: e.target.value })}>
              {DIFFICULTY.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div className="field">
            <label>年份</label>
            <input type="number" className="input" value={form.year} onChange={(e) => setForm({ ...form, year: Number(e.target.value) })} />
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>正文内容 *（保存后自动切分索引）</label>
            <textarea className="textarea" style={{ minHeight: 160 }} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} placeholder="粘贴讲义/资料全文…" />
          </div>
        </div>
      </Modal>

      {/* 上传文件（元数据与“编辑”一致） */}
      <Modal
        title="上传知识文件（txt / md / pdf）"
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setUploadOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={() => void doUpload()} disabled={uploading || !uploadFile}>
              {uploading ? "提交中…" : "提交后台处理"}
            </button>
          </>
        }
      >
        <div className="field">
          <label>选择文件 *（支持最大 200MB，可在 backend/.env 调整 MAX_UPLOAD_MB）</label>
          <input
            type="file"
            accept=".txt,.md,.pdf"
            className="input"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setUploadFile(f);
              if (f) setUploadForm((uf) => ({ ...uf, source: uf.source || f.name }));
            }}
          />
          {uploadFile && (
            <span className="small muted">
              {uploadFile.name} · {(uploadFile.size / 1024 / 1024).toFixed(1)}MB
            </span>
          )}
        </div>
        {notice && <div className="badge mb-8">{notice}</div>}
        <div className="form-grid">
          <div className="field">
            <label>文档标题（留空使用文件名）</label>
            <input className="input" value={uploadForm.title}
              onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })} />
          </div>
          <div className="field">
            <label>学科分类 *</label>
            <CoursePicker
              value={uploadForm.course}
              onChange={(v) => setUploadForm({ ...uploadForm, course: v })}
              options={courseOptions}
              canCreate={user?.role === "teacher"}
              onCreate={() => setNewCourseOpen(true)}
            />
          </div>
          <div className="field">
            <label>主题（知识点）</label>
            <input className="input" value={uploadForm.topic} placeholder="如：稳定匹配"
              onChange={(e) => setUploadForm({ ...uploadForm, topic: e.target.value })} />
          </div>
          <div className="field">
            <label>章节</label>
            <input className="input" value={uploadForm.chapter} placeholder="如：第 1 章"
              onChange={(e) => setUploadForm({ ...uploadForm, chapter: e.target.value })} />
          </div>
          <div className="field">
            <label>来源</label>
            <input className="input" value={uploadForm.source} placeholder="如：Algorithm Design (Kleinberg & Tardos)"
              onChange={(e) => setUploadForm({ ...uploadForm, source: e.target.value })} />
          </div>
          <div className="field">
            <label>类型</label>
            <select className="select" value={uploadForm.type}
              onChange={(e) => setUploadForm({ ...uploadForm, type: e.target.value })}>
              {TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div className="field">
            <label>难度</label>
            <select className="select" value={uploadForm.difficulty}
              onChange={(e) => setUploadForm({ ...uploadForm, difficulty: e.target.value })}>
              {DIFFICULTY.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div className="field">
            <label>年份</label>
            <input type="number" className="input" value={uploadForm.year}
              onChange={(e) => setUploadForm({ ...uploadForm, year: Number(e.target.value) })} />
          </div>
        </div>
        <p className="small muted" style={{ margin: 0 }}>
          大文件提示：188MB 级整本教材 PDF 可直接上传（流式解析）；文字版 PDF 秒级解析，
          扫描版（图片型）PDF 会自动走 OCR 中文识别（较慢，整本可能需要数分钟到更久）。
          更快的做法是先把 PDF 按章节拆分，或先转成带文字层的版本再上传。
        </p>
      </Modal>

      {/* 新建课程（创建课程的第一步：先建课，再邀请学生） */}
      <Modal
        title="新建课程"
        open={newCourseOpen}
        onClose={() => setNewCourseOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setNewCourseOpen(false)}>取消</button>
            <button
              className="btn btn-primary"
              onClick={() => void createCourse()}
              disabled={newCourseBusy || !newCourseForm.name.trim() || !newCourseForm.code.trim()}
            >
              {newCourseBusy ? "创建中…" : "创建课程"}
            </button>
          </>
        }
      >
        <p className="small muted mb-16">
          先创建课程（当前学生数 0），之后在「课程管理 → 学生管理」邀请学生，学生接受邀请后正式加入。
        </p>
        <div className="form-grid">
          <div className="field">
            <label>课程名称 *</label>
            <input
              className="input"
              value={newCourseForm.name}
              onChange={(e) => setNewCourseForm({ ...newCourseForm, name: e.target.value })}
              placeholder="如：计算机组成原理"
            />
          </div>
          <div className="field">
            <label>课程编号 *</label>
            <input
              className="input"
              value={newCourseForm.code}
              onChange={(e) => setNewCourseForm({ ...newCourseForm, code: e.target.value })}
              placeholder="如：CS250"
            />
          </div>
          <div className="field">
            <label>学期</label>
            <input
              className="input"
              value={newCourseForm.semester}
              onChange={(e) => setNewCourseForm({ ...newCourseForm, semester: e.target.value })}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
