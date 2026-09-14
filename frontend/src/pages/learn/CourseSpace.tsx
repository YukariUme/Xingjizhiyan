/** 课程学习空间：课程首页 / 预习 / AI讲堂 / 作业实验 / 复习 / 模拟 / 资料 / 答疑。 */

import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../../api";
import { ChatPanel } from "../../components/ChatPanel";
import { AiMeta } from "../../components/AiMeta";
import KnowledgeTree, { type KnowledgeGraphNode } from "../../components/KnowledgeTree";
import AiTutor from "../../components/AiTutor";
import StudyGuide from "../../components/StudyGuide";
import { DataStructurePlayer, DATA_STRUCTURES } from "../../components/DataStructurePlayer";
import Roundtable from "../Roundtable";
import { WorkflowSteps } from "../../components/WorkflowSteps";
import { Progress, Tabs } from "../../components/ui";
import { Card, EmptyState, ErrorBanner, Loading, Modal, useAsync } from "../../components/ui";
import type { Assignment, QuizQuestion } from "../../types";
import type { WorkflowRun } from "../../types";

type Overview = {
  course_name: string;
  code: string;
  semester: string;
  progress: number;
  mastery: number;
  current_chapter: { id: number; title: string } | null;
  chapters: Array<{ id: number; order: number; key: string; title: string; official_ref: string; summary: string; done: boolean }>;
  weak_points: Array<{ knowledge_point_id: number; name: string; mastery: number }>;
  pending_tasks: Array<{ id: number; title: string; reason: string; task_type: string; due_at: string | null }>;
  recent_records: Array<{ action: string; detail: Record<string, unknown>; created_at: string }>;
};

type Lecture = {
  depth: string;
  learning_goals: string[];
  sections: Array<{ title: string; content: string; example?: string; code?: string }>;
  common_errors: string[];
  exercises: Array<{ question: string; answer_hint: string }>;
  check: string[];
  ai_generated?: boolean;
  provider?: string;
  references?: Array<{ title: string; source: string; chapter: string; source_level: string; page: string }>;
  workflow_run_id?: number;
};

type Preview = {
  objectives: string[];
  prerequisites: string[];
  core_concepts: string[];
  materials: string[];
  pre_questions: Array<{ question: string; answer_hint: string }>;
  check: string[];
  ai_generated?: boolean;
  provider?: string;
  references?: Array<{ title: string; source: string; chapter: string; source_level: string; page: string }>;
  workflow_run_id?: number;
};

type QuizPaper = {
  quiz_id: number;
  title: string;
  questions: QuizQuestion[];
  workflow_run_id?: number;
};

type QuizOutcome = {
  result_id: number;
  score: number;
  max_score: number;
  accuracy: number;
  weak_points: Array<{ knowledge_point_id: number; name: string; accuracy: number }>;
  suggestions: Array<{ step: string; detail: string }>;
  references?: Array<{ title: string; source: string; chapter: string; source_level: string; page: string }>;
  workflow_run_id?: number;
};

const SCOPE_OPTIONS = [
  { key: "official", label: "课程官方资料" },
  { key: "shared", label: "教师审核/共享资料" },
  { key: "personal", label: "我的个人资料" },
  { key: "extended", label: "扩展知识" },
];

export default function CourseSpace() {
  const { courseId } = useParams();
  const id = Number(courseId);
  const [view, setView] = useState("home");
  const [selectedChapterId, setSelectedChapterId] = useState<number | null>(null);
  const [searchParams] = useSearchParams();

  // 支持旧 ?tab= 深链映射到新视图
  useEffect(() => {
    const t = searchParams.get("tab");
    const map: Record<string, string> = {
      overview: "home",
      study: "study",
      animation: "animation",
      roundtable: "roundtable",
      assignments: "assignments",
      review: "review",
      exam: "exam",
      materials: "materials",
      graph: "graph",
      preview: "study",
      lecture: "study",
      qa: "home",
    };
    if (t && map[t]) setView(map[t]);
  }, [searchParams]);
  const overview = useAsync<Overview>(() => api.get(`/curriculum/courses/${id}/overview`), [id]);
  const assignments = useAsync<Assignment[]>(() => api.get(`/assignments?course_id=${id}`), [id]);
  const graph = useAsync<GraphData>(() => api.get(`/curriculum/courses/${id}/graph`), [id]);

  if (overview.loading) return <Loading />;
  if (overview.error) return <ErrorBanner message={overview.error} />;
  const ov = overview.data;
  if (!ov) return <EmptyState text="课程不存在" />;

  const chapterOptions = ov.chapters.map((c) => ({
    key: String(c.id),
    label: `第${c.order}章 ${c.title}`,
  }));

  const openStudy = (chapterId?: number) => {
    if (chapterId) setSelectedChapterId(chapterId);
    setView("study");
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{ov.course_name} · 课程学习空间</h1>
          <p>{ov.code} · {ov.semester} · {view === "home" ? "这门课我现在该做什么？" : "返回首页查看整体进度与功能入口"}</p>
        </div>
        <div className="row">
          {view !== "home" && <button className="btn" onClick={() => setView("home")}>← 课程首页</button>}
          <Link to="/learn/courses" className="btn">← 我的课程</Link>
        </div>
      </div>

      {view === "home" && (
        <div className="course-home">
          <aside className="ch-left">
            <CourseNav graph={graph.data} selectedChapterId={selectedChapterId} onSelectChapter={openStudy} />
          </aside>
          <main className="ch-main">
            <HeroCard ov={ov} onStart={() => openStudy(ov.current_chapter?.id)} />
            <EntryCards onSelect={setView} />
            <OverviewTab overview={ov} onGo={(t) => setView(t)} />
          </main>
        </div>
      )}

      {view === "study" && (
        <div>
          <div className="study-breadcrumb">
            <span className="small muted">学习空间</span>
            <span className="muted">›</span>
            <b>{selectedChapterId ? (ov.chapters.find((c) => c.id === selectedChapterId)?.title ?? "自学") : "自学"}</b>
          </div>
          <StudyGuide courseId={id} courseName={ov.course_name} chapters={chapterOptions} initialChapterId={selectedChapterId ?? undefined} />
        </div>
      )}
      {view === "animation" && <AnimationPanel />}
      {view === "roundtable" && <Roundtable />}
      {view === "assignments" && (
        <div className="grid grid-2">
          {!assignments.data || assignments.data.length === 0 ? (
            <EmptyState text="本课程暂无作业" />
          ) : (
            assignments.data.map((a) => (
              <Card key={a.id} title={a.title} extra={<span className="badge gray">{a.course_name}</span>}>
                <p className="small muted">{a.description}</p>
                <div className="row wrap mb-8">
                  {a.questions.map((q) => (
                    <span key={q.id} className={`badge ${q.qtype === "programming" ? "purple" : "gray"}`}>
                      {q.qtype === "programming" ? "编程" : q.qtype === "report" ? "实验" : "简答"}
                    </span>
                  ))}
                </div>
                <Link to={`/learn/assignments/${a.id}`} className="btn btn-sm btn-primary">进入作业</Link>
              </Card>
            ))
          )}
        </div>
      )}
      {view === "review" && <ReviewTab courseId={id} chapters={chapterOptions} />}
      {view === "exam" && <ExamTab courseId={id} chapters={chapterOptions} />}
      {view === "materials" && <MaterialsTab courseId={id} />}
      {view === "graph" && <KnowledgeGraphTab courseId={id} />}
    </div>
  );
}

function CourseNav({
  graph,
  selectedChapterId,
  onSelectChapter,
}: {
  graph: GraphData | null;
  selectedChapterId: number | null;
  onSelectChapter: (id: number) => void;
}) {
  if (!graph) {
    return <Card title="章节 · 知识点"><Loading /></Card>;
  }
  return (
    <Card title="章节 · 知识点">
      {graph.chapters.map((ch) => {
        const pts = graph.points.filter((p) => p.chapter_id === ch.id);
        const active = selectedChapterId === ch.id;
        return (
          <div key={ch.id} style={{ marginBottom: 8 }}>
            <button className={`cw-chapter ${active ? "active" : ""}`} onClick={() => onSelectChapter(ch.id)}>
              第{ch.order}章 · {ch.title}
            </button>
            {active && (
              <div className="cw-points">
                {pts.map((p) => (
                  <button key={p.id} className="cw-point" onClick={() => onSelectChapter(ch.id)}>
                    {p.name}
                  </button>
                ))}
                {pts.length === 0 && <div className="muted small">暂无知识点</div>}
              </div>
            )}
          </div>
        );
      })}
      {graph.chapters.length === 0 && <div className="muted small">暂无章节数据</div>}
    </Card>
  );
}

const ENTRY_GROUPS: Array<{ title: string; items: Array<{ key: string; icon: string; title: string; desc: string }> }> = [
  {
    title: "学",
    items: [
      { key: "study", icon: "🧭", title: "AI 自学", desc: "按知识点逐步学习" },
      { key: "animation", icon: "🎬", title: "动画演示", desc: "栈/队列/树/排序/遍历" },
      { key: "roundtable", icon: "💬", title: "AI 圆桌", desc: "多角色友善讨论" },
    ],
  },
  {
    title: "练",
    items: [
      { key: "assignments", icon: "✍️", title: "作业实验", desc: "编程/简答/报告" },
      { key: "review", icon: "🔁", title: "课后复习", desc: "薄弱点补漏" },
      { key: "exam", icon: "📝", title: "考前模拟", desc: "测验与评分" },
    ],
  },
  {
    title: "查",
    items: [
      { key: "materials", icon: "📚", title: "课程资料", desc: "S/A/P 资料" },
      { key: "graph", icon: "🗺", title: "知识图谱", desc: "知识点关系" },
    ],
  },
];

function HeroCard({ ov, onStart }: { ov: Overview; onStart: () => void }) {
  const chapter = ov.current_chapter?.title ?? ov.chapters[0]?.title ?? "从第一章开始";
  return (
    <div className="hero-card">
      <div className="hero-copy">
        <span className="badge">继续学习</span>
        <h2>{chapter}</h2>
        <p className="small muted">课程进度 {ov.progress}% · 综合掌握度 {ov.mastery}%</p>
      </div>
      <button className="btn btn-primary btn-lg" onClick={onStart}>▶ 开始自学</button>
    </div>
  );
}

function EntryCards({ onSelect }: { onSelect: (key: string) => void }) {
  return (
    <div>
      {ENTRY_GROUPS.map((g) => (
        <div key={g.title} style={{ marginBottom: 16 }}>
          <div className="entry-group-title">{g.title}</div>
          <div className="entry-cards">
            {g.items.map((e) => (
              <button key={e.key} className="entry-tile" onClick={() => onSelect(e.key)}>
                <span className="entry-tile-icon">{e.icon}</span>
                <b>{e.title}</b>
                <span className="small muted">{e.desc}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function AnimationPanel() {
  const [kind, setKind] = useState("sorting");
  const active = DATA_STRUCTURES.find((s) => s.id === kind) ?? DATA_STRUCTURES[0];
  return (
    <div>
      <div className="row wrap" style={{ gap: 6, marginBottom: 16 }}>
        {DATA_STRUCTURES.map((s) => (
          <button key={s.id} className={`btn btn-sm ${kind === s.id ? "btn-primary" : ""}`} onClick={() => setKind(s.id)}>
            {s.name}（{s.en}）
          </button>
        ))}
      </div>
      <Card title={`${active.name} · ${active.en}`} extra={<span className="badge">{active.desc}</span>}>
        <DataStructurePlayer key={kind} kind={kind} />
      </Card>
    </div>
  );
}

type GraphData = {
  course: { id: number; name: string };
  chapters: Array<{ id: number; order: number; title: string; official_ref: string }>;
  points: KnowledgeGraphNode[];
};

function KnowledgeGraphTab({ courseId }: { courseId: number }) {
  const graph = useAsync<GraphData>(() => api.get(`/curriculum/courses/${courseId}/graph`), [courseId]);
  if (graph.loading) return <Loading />;
  const data = graph.data;
  if (!data || data.points.length === 0) return <EmptyState text="暂无知识点数据" />;
  return <KnowledgeTree data={data} />;
}

function OverviewTab({ overview, onGo }: { overview: Overview; onGo: (t: string) => void }) {
  const nextStep = (() => {
    const homework = overview.pending_tasks.find((t) => t.task_type === "homework");
    const reviewTask = overview.pending_tasks.find((t) => t.task_type === "review" || t.task_type === "retry");
    const weak = overview.weak_points[0];
    if (homework) {
      return { tab: "assignments", title: "先完成作业", reason: homework.reason, action: "去作业页" };
    }
    if (weak) {
      return { tab: "review", title: `先复习「${weak.name}」`, reason: `当前掌握度 ${weak.mastery}% ，先补这个点更划算。`, action: "去复习" };
    }
    if (reviewTask) {
      return { tab: "review", title: reviewTask.title, reason: reviewTask.reason, action: "去复盘" };
    }
    return { tab: "study", title: "开始自学", reason: "当前没有明显待办，可以从一个知识点开始自学。", action: "去自学" };
  })();

  return (
    <div className="grid">
      <div className="grid grid-4">
        <Card>
          <div className="stat-card">
            <div className="stat-label">课程进度</div>
            <div className="stat-value">{overview.progress}%</div>
            <Progress value={overview.progress} tone="auto" />
          </div>
        </Card>
        <Card>
          <div className="stat-card">
            <div className="stat-label">综合掌握度</div>
            <div className="stat-value">{overview.mastery}%</div>
            <Progress value={overview.mastery} tone="auto" />
          </div>
        </Card>
        <Card>
          <div className="stat-card">
            <div className="stat-label">当前章节</div>
            <div className="stat-value" style={{ fontSize: 18 }}>
              {overview.current_chapter?.title ?? "尚未开始"}
            </div>
          </div>
        </Card>
        <Card>
          <div className="stat-card">
            <div className="stat-label">待完成任务</div>
            <div className="stat-value">{overview.pending_tasks.length}</div>
          </div>
        </Card>
      </div>

      <div className="grid grid-2">
        <Card title="本周学习建议">
          {overview.pending_tasks.length === 0 && overview.weak_points.length === 0 ? (
            <div className="badge green">当前状态良好，可以预习下一章节或进入研究空间</div>
          ) : (
            <>
              {overview.pending_tasks.slice(0, 3).map((t) => (
                <div key={t.id} className="small" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                  <b>{t.title}</b>
                  <div className="muted">{t.reason}</div>
                </div>
              ))}
              {overview.weak_points.slice(0, 2).map((w) => (
                <div key={w.knowledge_point_id} className="small" style={{ padding: "6px 0" }}>
                  <b>{w.name}</b> 掌握度 {w.mastery}%，建议先完成章节复习。
                </div>
              ))}
            </>
          )}
        </Card>
        <Card title="薄弱知识点">
          {overview.weak_points.length === 0 ? (
            <div className="badge green">无明显薄弱点</div>
          ) : (
            overview.weak_points.map((w) => (
              <div key={w.knowledge_point_id} className="row space-between" style={{ padding: "7px 0" }}>
                <b>{w.name}</b>
                <div className="row" style={{ width: 150 }}>
                  <Progress value={w.mastery} tone="auto" />
                  <span className="small">{w.mastery}%</span>
                </div>
              </div>
            ))
          )}
        </Card>
      </div>

      <Card title="下一步建议">
        <div className="row space-between" style={{ alignItems: "flex-start", gap: 12 }}>
          <div>
            <div className="badge blue mb-8">{nextStep.title}</div>
            <div className="small muted">{nextStep.reason}</div>
          </div>
          <button className="btn btn-primary" onClick={() => onGo(nextStep.tab)}>{nextStep.action}</button>
        </div>
      </Card>

      <Card title="最近学习活动">
        {overview.recent_records.length === 0 ? (
          <div className="muted small">还没有学习记录，从预习开始吧</div>
        ) : (
          overview.recent_records.map((r, i) => (
            <div key={i} className="small" style={{ padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
              {r.action} · {new Date(r.created_at).toLocaleString("zh-CN")}
            </div>
          ))
        )}
      </Card>
    </div>
  );
}
function ChapterSelect({ chapters, value, onChange }: {
  chapters: Array<{ key: string; label: string }>;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <select className="select" style={{ width: 260 }} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">选择章节</option>
      {chapters.map((c) => (
        <option key={c.key} value={c.key}>{c.label}</option>
      ))}
    </select>
  );
}

function PreviewTab({ courseId, chapters }: { courseId: number; chapters: Array<{ key: string; label: string }> }) {
  const [chapterId, setChapterId] = useState("");
  const [data, setData] = useState<Preview | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [traceRun, setTraceRun] = useState<WorkflowRun | null>(null);
  const runPreview = async () => {
    if (!chapterId) return;
    setLoading(true); setErr("");
    try {
      const res = await api.post<Preview>(`/curriculum/courses/${courseId}/chapters/${chapterId}/preview`, {});
      setData(res);
      if (res.workflow_run_id) {
        api.get<WorkflowRun>(`/workflows/runs/${res.workflow_run_id}`).then(setTraceRun).catch(() => undefined);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="grid">
      {!data ? (
        <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <Card title="课前预习">
          <ChapterSelect chapters={chapters} value={chapterId} onChange={setChapterId} />
          <button className="btn btn-primary mt-16" onClick={() => void runPreview()} disabled={loading || !chapterId}>
            {loading ? "生成中…" : "生成预习内容"}
          </button>
          {err && <div className="badge red mt-8">{err}</div>}
        </Card>
        </div>
      ) : (
        <>
          <Card className="mb-16">
            <div className="row wrap" style={{ gap: 8 }}>
              <ChapterSelect chapters={chapters} value={chapterId} onChange={setChapterId} />
              <button className="btn btn-primary" onClick={() => void runPreview()} disabled={loading || !chapterId}>
                {loading ? "生成中…" : "重新生成"}
              </button>
              {err && <span className="badge red">{err}</span>}
            </div>
          </Card>
          <div className="grid">
          <Card title="学习目标"><List items={data.objectives} /></Card>
          <Card title="预备知识"><List items={data.prerequisites} /></Card>
          <Card title="核心概念">
            {data.core_concepts.map((c) => <span key={c} className="badge" style={{ margin: "0 6px 6px 0" }}>{c}</span>)}
          </Card>
          <Card title="预习材料"><List items={data.materials} /></Card>
          <Card title="预习题">
            {data.pre_questions.map((q, i) => (
              <div key={i} className="small" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                <b>{q.question}</b>
                <div className="muted">提示：{q.answer_hint}</div>
              </div>
            ))}
          </Card>
          <Card title="学习检查"><List items={data.check} /></Card>
          <AiMeta provider={data.provider} references={data.references} />
          {traceRun && (
            <Card title={`预习工作流 #${traceRun.id}（可追踪）`}>
              <WorkflowSteps run={traceRun} />
            </Card>
          )}
          <button className="btn btn-primary" onClick={() => void api.post("/curriculum/records", { action: "preview_done", course_id: courseId, chapter_id: Number(chapterId) })}>
            ✓ 完成预习
          </button>
          </div>
        </>
      )}
    </div>
  );
}

function LectureTab({ courseId, chapters }: { courseId: number; chapters: Array<{ key: string; label: string }> }) {
  const [chapterId, setChapterId] = useState("");
  const [depth, setDepth] = useState("standard");
  const [data, setData] = useState<Lecture | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [traceRun, setTraceRun] = useState<WorkflowRun | null>(null);
  const runLecture = async () => {
    if (!chapterId) return;
    setLoading(true); setErr("");
    try {
      const res = await api.post<Lecture>(`/curriculum/chapters/${chapterId}/lecture`, { depth });
      setData(res);
      if (res.workflow_run_id) {
        api.get<WorkflowRun>(`/workflows/runs/${res.workflow_run_id}`).then(setTraceRun).catch(() => undefined);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div>
      <Card className="mb-16">
        <div className="row wrap">
          <ChapterSelect chapters={chapters} value={chapterId} onChange={setChapterId} />
          <select className="select" style={{ width: 150 }} value={depth} onChange={(e) => setDepth(e.target.value)}>
            <option value="quick">快速讲解</option>
            <option value="standard">标准课程</option>
            <option value="deep">深度讲解</option>
          </select>
          <button className="btn btn-primary" onClick={() => void runLecture()} disabled={loading || !chapterId}>
            {loading ? "生成中…" : "开始课程"}
          </button>
        </div>
        {err && <div className="badge red mt-8">{err}</div>}
      </Card>
      {data && (
        <div className="grid">
          <Card title="学习目标"><List items={data.learning_goals} /></Card>
          {data.sections.map((s, i) => (
            <Card key={i} title={`${i + 1}. ${s.title}`}>
              <p className="small" style={{ whiteSpace: "pre-wrap" }}>{s.content}</p>
              {s.example && <div className="small muted mt-8">示例：{s.example}</div>}
              {s.code && <pre className="code-block mt-8">{s.code}</pre>}
            </Card>
          ))}
          <Card title="常见错误"><List items={data.common_errors} /></Card>
          <Card title="随堂练习">
            {data.exercises.map((e, i) => (
              <div key={i} className="small" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                <b>{e.question}</b>
                <div className="muted">提示：{e.answer_hint}</div>
              </div>
            ))}
          </Card>
          <Card title="理解检查"><List items={data.check} /></Card>
          <AiMeta provider={data.provider} references={data.references} />
          {traceRun && (
            <Card title={`讲堂工作流 #${traceRun.id}（可追踪）`}>
              <WorkflowSteps run={traceRun} />
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function List({ items }: { items: string[] }) {
  if (!items.length) return <div className="muted small">暂无</div>;
  return (
    <div>
      {items.map((it, i) => (
        <div key={i} className="small" style={{ padding: "5px 0" }}>• {typeof it === "string" ? it : JSON.stringify(it)}</div>
      ))}
    </div>
  );
}

function ReviewTab({ courseId, chapters }: { courseId: number; chapters: Array<{ key: string; label: string }> }) {
  const [chapterId, setChapterId] = useState("");
  const [related, setRelated] = useState<{
    knowledge_point: { id: number; name: string; subject: string; description: string; prerequisites: string[]; related_points: string[] };
    papers: Array<{ id: number; title: string; year: number; venue: string }>;
    documents: Array<{ id: number; title: string; type: string; source: string }>;
  } | null>(null);
  const [relatedBusy, setRelatedBusy] = useState(false);
  const [reviewPack, setReviewPack] = useState<{
    summary: string;
    key_points: string[];
    weak_plan: Array<{ kp: string; reason: string; action: string }>;
    exercises: Array<{ question: string; answer_hint: string }>;
    next_steps: string[];
    provider?: string;
    references?: Array<{ title: string; source: string; chapter: string; source_level: string; page: string }>;
    workflow_run_id?: number;
  } | null>(null);
  const [reviewRun, setReviewRun] = useState<WorkflowRun | null>(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const data = useAsync<{
    title: string; summary: string;
    knowledge_points: Array<{ id: number; name: string; description: string }>;
    weak_points: Array<{ name: string; mastery: number }>;
    errors: Array<{ knowledge_point: string; errors: number; mastery: number }>;
  }>(
    () => (chapterId ? api.get(`/curriculum/chapters/${chapterId}/view`) : Promise.resolve(null as never)),
    [chapterId]
  );
  const openRelated = async (kpId: number) => {
    setRelatedBusy(true);
    try {
      const res = await api.get<{
        knowledge_point: { id: number; name: string; subject: string; description: string; prerequisites: string[]; related_points: string[] };
        papers: Array<{ id: number; title: string; year: number; venue: string }>;
        documents: Array<{ id: number; title: string; type: string; source: string }>;
      }>(`/knowledge/points/${kpId}/related`);
      setRelated(res);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "加载失败");
    } finally {
      setRelatedBusy(false);
    }
  };
  const generateReview = async () => {
    if (!chapterId) return;
    setReviewBusy(true);
    try {
      const res = await api.post<{
        summary: string;
        key_points: string[];
        weak_plan: Array<{ kp: string; reason: string; action: string }>;
        exercises: Array<{ question: string; answer_hint: string }>;
        next_steps: string[];
        provider?: string;
        references?: Array<{ title: string; source: string; chapter: string; source_level: string; page: string }>;
        workflow_run_id?: number;
      }>(`/curriculum/chapters/${chapterId}/review`, {});
      setReviewPack(res);
      if (res.workflow_run_id) {
        api.get<WorkflowRun>(`/workflows/runs/${res.workflow_run_id}`).then(setReviewRun).catch(() => undefined);
      }
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "生成失败");
    } finally {
      setReviewBusy(false);
    }
  };
  return (
    <div className="grid grid-2" style={{ alignItems: "start" }}>
      <Card title="课后复习 · 选择章节">
        <ChapterSelect chapters={chapters} value={chapterId} onChange={setChapterId} />
        <button className="btn btn-primary mt-8" onClick={() => void generateReview()} disabled={reviewBusy || !chapterId}>
          {reviewBusy ? "生成中…" : "✦ 生成复习包"}
        </button>
        {reviewPack && (
          <div className="mt-16">
            <h3>本章总结</h3>
            <p className="small">{reviewPack.summary}</p>
            <h3>复习要点</h3>
            <List items={reviewPack.key_points} />
            <h3>薄弱点复习计划</h3>
            {reviewPack.weak_plan.map((w, i) => (
              <div key={i} className="small" style={{ padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
                <b>{w.kp}</b> · {w.reason}
                <div className="muted">行动：{w.action}</div>
              </div>
            ))}
            <h3>强化练习</h3>
            {reviewPack.exercises.map((e, i) => (
              <div key={i} className="small" style={{ padding: "5px 0" }}>
                {e.question}
                <div className="muted">提示：{e.answer_hint}</div>
              </div>
            ))}
            <h3>下一步建议</h3>
            <List items={reviewPack.next_steps} />
            <AiMeta provider={reviewPack.provider} references={reviewPack.references} />
            {reviewRun && (
              <Card title={`复习工作流 #${reviewRun.id}（可追踪）`} className="mt-16">
                <WorkflowSteps run={reviewRun} />
              </Card>
            )}
          </div>
        )}
        {data.data && (
          <>
            <h3 className="mt-16">本章总结</h3>
            <p className="small">{data.data.summary}</p>
            <h3>知识结构</h3>
            {data.data.knowledge_points.map((kp) => (
              <div key={kp.id} className="row space-between" style={{ padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
                <div>
                  <b>{kp.name}</b>
                  <div className="muted">{kp.description}</div>
                </div>
                <button className="btn btn-sm" onClick={() => void openRelated(kp.id)}>深入研究</button>
              </div>
            ))}
          </>
        )}
      </Card>
      <div className="grid">
        <Card title="我的薄弱点">
          {data.data?.weak_points.length ? (
            data.data.weak_points.map((w) => (
              <div key={w.name} className="row space-between" style={{ padding: "6px 0" }}>
                <b>{w.name}</b>
                <span className="badge red">{w.mastery}%</span>
              </div>
            ))
          ) : (
            <div className="muted small">本章暂无薄弱点</div>
          )}
        </Card>
        <Card title="错题复习">
          {data.data?.errors.length ? (
            data.data.errors.map((e) => (
              <div key={e.knowledge_point} className="small" style={{ padding: "5px 0" }}>
                {e.knowledge_point} · 错误 {e.errors} 次
              </div>
            ))
          ) : (
            <div className="muted small">暂无错题记录</div>
          )}
        </Card>
      </div>

      <Modal
        title={related ? `深入研究 · ${related.knowledge_point.name}` : "深入研究"}
        open={related != null}
        onClose={() => setRelated(null)}
        footer={<button className="btn" onClick={() => setRelated(null)}>关闭</button>}
      >
        {relatedBusy ? (
          <Loading />
        ) : related ? (
          <div>
            <p className="small">{related.knowledge_point.description}</p>
            <div className="row wrap mb-8">
              {related.knowledge_point.prerequisites.map((p) => <span key={p} className="tag">前置：{p}</span>)}
              {related.knowledge_point.related_points.map((p) => <span key={p} className="tag">关联：{p}</span>)}
            </div>
            <h3>相关论文（可进入研究空间）</h3>
            {related.papers.length === 0 ? (
              <div className="muted small">暂未检索到相关论文</div>
            ) : (
              related.papers.map((p) => (
                <div key={p.id} className="row space-between" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                  <span className="small grow">{p.title}</span>
                  <Link to={`/research/papers?paper=${p.id}`} className="btn btn-sm">阅读</Link>
                </div>
              ))
            )}
            <h3>课程资料</h3>
            {related.documents.map((d) => (
              <div key={d.id} className="small" style={{ padding: "5px 0" }}>• {d.title}（{d.type}）</div>
            ))}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

function ExamTab({ courseId, chapters }: { courseId: number; chapters: Array<{ key: string; label: string }> }) {
  const [quizType, setQuizType] = useState("chapter");
  const [chapterId, setChapterId] = useState("");
  const [paper, setPaper] = useState<QuizPaper | null>(null);
  const [answers, setAnswers] = useState<Record<number, unknown>>({});
  const [outcome, setOutcome] = useState<QuizOutcome | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [runId, setRunId] = useState<number | null>(null);
  const start = async () => {
    if (quizType === "chapter" && !chapterId) {
      setErr("章节测验请选择章节");
      return;
    }
    setLoading(true); setErr(""); setOutcome(null); setPaper(null); setAnswers({});
    try {
      const res = await api.post<QuizPaper>("/curriculum/quizzes", {
        course_id: courseId,
        quiz_type: quizType,
        chapter_id: quizType === "chapter" ? Number(chapterId) : undefined,
      });
      setPaper(res);
      setRunId(res.workflow_run_id ?? null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  };
  const submit = async () => {
    if (!paper) return;
    setLoading(true);
    try {
      const res = await api.post<QuizOutcome>(`/curriculum/quizzes/${paper.quiz_id}/submit`, {
        answers: Object.entries(answers).map(([question_id, answer]) => ({ question_id: Number(question_id), answer })),
      });
      setOutcome(res);
      setRunId(res.workflow_run_id ?? null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "提交失败");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div>
      <Card className="mb-16">
        <div className="row wrap">
          <select className="select" style={{ width: 170 }} value={quizType} onChange={(e) => setQuizType(e.target.value)}>
            <option value="chapter">章节测验</option>
            <option value="mock">全范围模拟</option>
            <option value="weakness">薄弱点专项</option>
            <option value="wrong_retest">错题重测</option>
          </select>
          {quizType === "chapter" && <ChapterSelect chapters={chapters} value={chapterId} onChange={setChapterId} />}
          <button className="btn btn-primary" onClick={() => void start()} disabled={loading}>
            {loading ? "生成中…" : "开始测验"}
          </button>
        </div>
        {err && <div className="badge red mt-8">{err}</div>}
      </Card>

      {paper && !outcome && (
        <Card title={paper.title} extra={<div className="row">{runId && <span className="badge gray">工作流 #{runId}</span>}<button className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={loading}>提交</button></div>}>
          {paper.questions.map((q) => (
            <div key={q.question_id} className="mb-16" style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
              <div className="row space-between">
                <b className="small">{q.title}</b>
                <span className="badge gray">{q.max_score} 分 · {q.qtype}</span>
              </div>
              {q.qtype === "single" || q.qtype === "judge" ? (
                <div className="row wrap mt-8">
                  {q.options.map((opt, i) => (
                    <button key={i} className={`btn btn-sm ${answers[q.question_id] === i ? "btn-primary" : ""}`} onClick={() => setAnswers({ ...answers, [q.question_id]: i })}>
                      {opt}
                    </button>
                  ))}
                </div>
              ) : (
                <textarea
                  className="textarea mt-8"
                  placeholder={q.qtype === "code" ? "在此输入代码…" : "输入你的答案…"}
                  value={String(answers[q.question_id] ?? "")}
                  onChange={(e) => setAnswers({ ...answers, [q.question_id]: e.target.value })}
                />
              )}
            </div>
          ))}
        </Card>
      )}

      {outcome && (
        <div className="grid">
          <Card title="测验结果">
            <div className="row">
              <span className="stat-value">{outcome.score}</span>
              <span className="muted">/ {outcome.max_score} 分 · 正确率 {outcome.accuracy}%</span>
            </div>
            <div className="row wrap mt-8">
              {outcome.weak_points.map((w) => (
                <span key={w.knowledge_point_id} className="badge red">{w.name} {w.accuracy}%</span>
              ))}
            </div>
          </Card>
          <Card title="复习建议">
            {outcome.suggestions.map((s, i) => (
              <div key={i} className="small" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                <b>{i + 1}. {s.step}</b>
                <div className="muted">{s.detail}</div>
              </div>
            ))}
          </Card>
          {runId && <span className="badge gray">评分工作流 #{runId}</span>}
          <AiMeta provider="quiz-engine" references={outcome.references} />
        </div>
      )}
    </div>
  );
}

function MaterialsTab({ courseId }: { courseId: number }) {
  const materials = useAsync<Array<{ id: number; title: string; source: string; source_level: string; visibility: string; type: string; topic: string; chapter: string; owner_me: boolean }>>(
    () => api.get(`/curriculum/courses/${courseId}/materials`),
    [courseId]
  );
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [scope, setScope] = useState("private");
  const [title, setTitle] = useState("");
  const [msg, setMsg] = useState("");
  const [reader, setReader] = useState<{ id: number; title: string; content: string; source: string; type: string; chapter: string } | null>(null);
  const [readerBusy, setReaderBusy] = useState(false);
  const openReader = async (m: { id: number; title: string }) => {
    setReaderBusy(true);
    try {
      const d = await api.get<{ id: number; title: string; content: string; source: string; type: string; chapter: string }>(
        `/knowledge/documents/${m.id}`
      );
      setReader(d);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "打开失败");
    } finally {
      setReaderBusy(false);
    }
  };
  const upload = async () => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("scope", scope);
    fd.append("title", title || file.name);
    try {
      const res = await api.upload<{ ok: boolean; review_pending: boolean }>(
        `/curriculum/courses/${courseId}/materials/upload`,
        fd
      );
      setMsg(res.review_pending ? "已提交，等待教师审核后进入课程共享空间" : "已上传（仅自己可见）");
      setOpen(false);
      setFile(null);
      materials.refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "上传失败");
    }
  };
  const levelLabel: Record<string, string> = { S: "官方", A: "审核共享", P: "个人" };
  return (
    <div>
      <div className="row space-between mb-16">
        <div className="small muted">[S] 官方资料 · [A] 教师审核共享 · [P] 个人资料（仅自己可见）</div>
        <button className="btn btn-primary" onClick={() => setOpen(true)}>⬆ 上传资料</button>
      </div>
      {materials.loading ? (
        <Loading />
      ) : !materials.data || materials.data.length === 0 ? (
        <EmptyState text="本课程暂无资料" />
      ) : (
        <div className="grid grid-2">
          {materials.data.map((m) => (
            <Card key={m.id} title={m.title} extra={<span className={`badge ${m.source_level === "S" ? "green" : m.source_level === "A" ? "orange" : "purple"}`}>[{m.source_level}] {levelLabel[m.source_level]}</span>}>
              <p className="small muted">{m.type} · {m.topic} · {m.chapter} · {m.source}</p>
              <div className="row mt-8">
                <button className="btn btn-sm btn-primary" onClick={() => void openReader(m)} disabled={readerBusy}>打开阅读</button>
                {m.owner_me && <span className="badge gray">我的资料</span>}
              </div>
            </Card>
          ))}
        </div>
      )}
      {msg && <div className="badge green mt-8">{msg}</div>}
      <Modal
        title="上传课程资料"
        open={open}
        onClose={() => setOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={() => void upload()} disabled={!file}>上传</button>
          </>
        }
      >
        <div className="field">
          <label>选择文件（txt / md / pdf / epub）</label>
          <input
            type="file"
            accept=".txt,.md,.markdown,.pdf,.epub,.ppt,.pptx,.doc,.docx"
            className="input"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <div className="field">
          <label>资料范围</label>
          <div className="row wrap">
            <button className={`btn btn-sm ${scope === "private" ? "btn-primary" : ""}`} onClick={() => setScope("private")}>仅我使用</button>
            <button className={`btn btn-sm ${scope === "shared" ? "btn-primary" : ""}`} onClick={() => setScope("shared")}>申请加入课程共享</button>
          </div>
        </div>
        <div className="field">
          <label>标题（留空使用文件名）</label>
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
      </Modal>

      <Modal
        title={reader?.title ?? "阅读资料"}
        open={reader != null}
        onClose={() => setReader(null)}
        footer={<button className="btn" onClick={() => setReader(null)}>关闭</button>}
      >
        {reader && (
          <>
            <div className="row wrap mb-8">
              {reader.type && <span className="badge">{reader.type}</span>}
              {reader.chapter && <span className="badge gray">{reader.chapter}</span>}
              {reader.source && <span className="badge gray">{reader.source}</span>}
            </div>
            <div className="code-block" style={{ maxHeight: "62vh", overflow: "auto", whiteSpace: "pre-wrap" }}>
              {reader.content || "（无正文内容）"}
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}

function QaTab({ courseId, chapters }: { courseId: number; chapters: Array<{ key: string; label: string }> }) {
  const [chapterId, setChapterId] = useState("");
  const [scope, setScope] = useState("official");
  return (
    <div>
      <Card className="mb-16">
        <div className="row wrap">
          <select className="select" style={{ width: 220 }} value={chapterId} onChange={(e) => setChapterId(e.target.value)}>
            <option value="">不限章节</option>
            {chapters.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
          </select>
          <select className="select" style={{ width: 200 }} value={scope} onChange={(e) => setScope(e.target.value)}>
            {SCOPE_OPTIONS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </div>
      </Card>
      <Card>
        <ChatPanel
          agent="learning"
          extraPayload={{ course_id: courseId, chapter_id: chapterId ? Number(chapterId) : undefined, scope }}
          placeholder="基于当前课程知识空间提问，如：为什么这里需要信号量？"
        />
      </Card>
      <p className="small muted mt-8">默认官方课程资料优先；资料不足时会明确提示“以下回答属于扩展知识”。</p>
    </div>
  );
}
