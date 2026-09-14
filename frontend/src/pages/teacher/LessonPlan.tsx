/** 智能备课：输入区 + 全屏教案展示，班级学情自动检测可选参考。 */

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../api";
import { WorkflowSteps } from "../../components/WorkflowSteps";
import { AiMeta, type AiReference } from "../../components/AiMeta";
import { Card, EmptyState, Loading, useAsync } from "../../components/ui";
import type { ClassAnalytics, Course, LessonPlan, WorkflowRun } from "../../types";

const COURSE_OPTIONS = ["数据结构", "算法设计与分析", "操作系统", "计算机网络", "数据库系统", "人工智能"];
const COURSE_DEFAULTS: Record<string, { chapter: string; topic: string }> = {
  "数据结构": { chapter: "第 4 章 树", topic: "二叉树遍历" },
  "算法设计与分析": { chapter: "第 2 章 分治", topic: "归并排序" },
  "操作系统": { chapter: "第 4 章 进程同步", topic: "进程同步与信号量" },
  "计算机网络": { chapter: "第 3 章 传输层", topic: "TCP 滑动窗口" },
  "数据库系统": { chapter: "第 5 章 事务", topic: "事务与锁" },
  "人工智能": { chapter: "第 3 章 搜索", topic: "A* 搜索" },
};

function toStr(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export default function TeacherLessonPlan() {
  const [params] = useSearchParams();
  const [form, setForm] = useState({
    course: "数据结构",
    chapter: COURSE_DEFAULTS["数据结构"].chapter,
    topic: COURSE_DEFAULTS["数据结构"].topic,
    grade: "大二",
    objective: "",
    level: "中等",
    duration: "45 分钟",
  });
  const [refAnalytics, setRefAnalytics] = useState(true);
  const [classSummary, setClassSummary] = useState("");
  const [analyticsBusy, setAnalyticsBusy] = useState(false);
  const [plan, setPlan] = useState<LessonPlan | null>(null);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const history = useAsync<LessonPlan[]>(() => api.get("/lesson-plans"));
  const courses = useAsync<Course[]>(() => api.get("/courses"));

  // 演示模式通过 URL 参数内置必填项（章节 / 主题）
  useEffect(() => {
    const course = params.get("course");
    const suggestion = params.get("suggestion");
    const chapter = params.get("chapter");
    const topic = params.get("topic");
    setForm((f) => ({
      ...f,
      course: course ?? f.course,
      chapter: chapter ?? f.chapter,
      topic: topic ?? f.topic,
      objective: suggestion ?? f.objective,
    }));
  }, [params]);

  const detectAnalytics = async () => {
    if (!refAnalytics) {
      setClassSummary("");
      return;
    }
    const course = courses.data?.find((c) => c.name === form.course);
    if (!course) {
      setClassSummary("");
      return;
    }
    setAnalyticsBusy(true);
    try {
      const a = await api.get<ClassAnalytics>(`/analytics/courses/${course.id}`);
      const hf = (a.high_frequency_errors ?? []).slice(0, 3).map((x) => x.name).join("、") || "无";
      const weak = (a.weak_points ?? []).slice(0, 3).join("、") || "无";
      setClassSummary(`班级平均正确率 ${a.avg_accuracy}%；高频错误：${hf}；薄弱点：${weak}。`);
    } catch {
      setClassSummary("该课程暂无学情数据");
    } finally {
      setAnalyticsBusy(false);
    }
  };

  useEffect(() => {
    void detectAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.course, refAnalytics, courses.data]);

  const generate = async () => {
    if (!form.chapter.trim() || !form.topic.trim()) {
      setErr("请填写章节与教学主题");
      return;
    }
    setErr("");
    setLoading(true);
    try {
      const res = await api.post<WorkflowRun>("/workflows/lesson_plan/run", {
        ...form,
        class_analytics: refAnalytics ? classSummary : "",
      });
      setRun(res);
      setPlan(res.output.save as unknown as LessonPlan);
      history.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  };

  const removePlan = async (p: LessonPlan) => {
    if (!window.confirm(`确认删除教案《${p.topic}》？`)) return;
    try {
      await api.delete(`/lesson-plans/${p.id}`);
      history.refresh();
      if (plan?.id === p.id) setPlan(null);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "删除失败");
    }
  };

  const clearAll = async () => {
    if (!history.data?.length) return;
    if (!window.confirm("确认清空全部历史教案？此操作不可恢复。")) return;
    try {
      await api.delete("/lesson-plans");
      history.refresh();
      setPlan(null);
      setRun(null);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "清空失败");
    }
  };

  return (
    <div className="page lesson-page">
      <div className="page-header">
        <div>
          <h1>智能备课</h1>
          <p>输入教学目标，AI 结合知识库与班级学情生成结构化教案</p>
        </div>
      </div>

      <Card title="备课输入">
        <div className="lesson-form-grid">
          <div className="field">
            <label>课程</label>
            <select
              className="select"
              value={form.course}
              onChange={(e) => {
                const v = e.target.value;
                const d = COURSE_DEFAULTS[v] ?? { chapter: "", topic: "" };
                setForm((f) => ({ ...f, course: v, chapter: d.chapter, topic: d.topic }));
              }}
            >
              {COURSE_OPTIONS.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="field">
            <label>学生年级</label>
            <input className="input" value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })} />
          </div>
          <div className="field">
            <label>学生水平</label>
            <select className="select" value={form.level} onChange={(e) => setForm({ ...form, level: e.target.value })}>
              <option>基础</option>
              <option>中等</option>
              <option>良好</option>
            </select>
          </div>
          <div className="field">
            <label>教学时长</label>
            <input className="input" value={form.duration} onChange={(e) => setForm({ ...form, duration: e.target.value })} placeholder="如：45 分钟" />
          </div>
          <div className="field">
            <label>章节 *</label>
            <input className="input" value={form.chapter} onChange={(e) => setForm({ ...form, chapter: e.target.value })} placeholder="如：第 4 章 树" />
          </div>
          <div className="field">
            <label>教学主题 *</label>
            <input className="input" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} placeholder="如：二叉树遍历" />
          </div>
        </div>

        <div className="field">
          <label>教学目标（可选）</label>
          <textarea className="textarea" style={{ minHeight: 72 }} value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} placeholder="如：掌握三种遍历方式的递归实现" />
        </div>

        <div className="field">
          <div className="row space-between">
            <label style={{ margin: 0 }}>班级学情参考</label>
            <button className={`btn btn-sm ${refAnalytics ? "btn-primary" : ""}`} onClick={() => setRefAnalytics((v) => !v)}>
              {refAnalytics ? "● 自动参考" : "○ 不参考"}
            </button>
          </div>
          {refAnalytics && (
            analyticsBusy ? (
              <Loading text="正在检测班级学情…" />
            ) : (
              <div className="lesson-analytics">
                {classSummary || "该课程暂无学情数据，将按通用目标生成。"}
              </div>
            )
          )}
        </div>

        {err && <div className="badge red mb-8">{err}</div>}
        <button className="btn btn-primary btn-lg" onClick={() => void generate()} disabled={loading}>
          {loading ? "AI 备课中…" : "✦ 生成教案"}
        </button>
      </Card>

      <Card
        title={`历史教案（自动保存 · ${history.data?.length ?? 0}）`}
        className="mt-16"
        extra={<button className="btn btn-sm btn-danger" onClick={() => void clearAll()}>清空历史</button>}
      >
        {history.loading ? (
          <Loading />
        ) : !history.data || history.data.length === 0 ? (
          <EmptyState emoji="📋" text="还没有历史教案，生成后会在这里自动保存" />
        ) : (
          history.data.map((p) => (
            <div key={p.id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <div className="grow" style={{ cursor: "pointer" }} onClick={() => { setPlan(p); setRun(null); }}>
                <b>{p.topic}</b>
                <div className="small muted">{p.course} · {p.chapter} · {formatDate(p.created_at)}</div>
              </div>
              <div className="row">
                <button
                  className="btn btn-sm"
                  onClick={() => setForm((f) => ({
                    ...f,
                    course: p.course,
                    chapter: p.chapter,
                    topic: p.topic,
                    grade: p.grade,
                    objective: typeof p.objectives === "string" ? p.objectives.slice(0, 80) : "",
                  }))}
                  title="填入表单后重新生成"
                >
                  复用
                </button>
                <button className="btn btn-sm btn-danger" onClick={() => void removePlan(p)}>删除</button>
              </div>
            </div>
          ))
        )}
      </Card>

      {loading ? (
        <Card className="mt-16"><Loading text="AI 正在结合知识库与班级学情生成教案…" /></Card>
      ) : plan ? (
        <div className="lesson-plan">
          {run && (
            <Card
              title={`工作流执行过程 #${run.id}（共 ${run.steps.length} 步）`}
              extra={<span className="badge green">✓ 执行成功</span>}
            >
              <WorkflowSteps run={run} />
            </Card>
          )}

          <Card title={`教案：${plan.topic}`} extra={<span className="badge">备课工作流 · 知识库增强</span>}>
            <div className="small muted mb-8">{plan.course} · {plan.chapter} · {plan.grade}</div>
            <h3>教学目标</h3>
            <p className="small" style={{ whiteSpace: "pre-wrap" }}>{plan.objectives}</p>
            <div className="row wrap">
              {plan.knowledge_points.map((k) => <span key={k} className="badge">{toStr(k)}</span>)}
            </div>
          </Card>

          {run && (
            (() => {
              const out = run.output as { generate?: { provider?: string }; retrieve?: { hits?: AiReference[] } };
              return <AiMeta provider={out.generate?.provider} references={out.retrieve?.hits} />;
            })()
          )}

          <div className="grid grid-2">
            <Card title="重点">
              {plan.key_points.map((k, i) => <div key={i} className="small" style={{ padding: "5px 0" }}>• {toStr(k)}</div>)}
            </Card>
            <Card title="难点">
              {plan.difficulties.map((k, i) => <div key={i} className="small" style={{ padding: "5px 0" }}>• {toStr(k)}</div>)}
            </Card>
          </div>

          <Card title="教学流程">
            {plan.flow.map((f, i) => (
              <div key={i} className="row" style={{ alignItems: "flex-start", padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
                <span className="badge purple">{f.step}</span>
                <span className="small">{f.content}</span>
              </div>
            ))}
          </Card>

          <Card title="课堂案例">
            {plan.cases.map((c, i) => <div key={i} className="small" style={{ padding: "4px 0" }}>• {toStr(c)}</div>)}
          </Card>

          <div className="grid grid-2">
            <Card title="随堂练习">
              {plan.exercises.map((e, i) => (
                <div key={i} style={{ padding: "6px 0" }}>
                  <b className="small">{e.title}</b>
                  <div className="small muted">{e.desc}</div>
                </div>
              ))}
            </Card>
            <Card title="课后作业建议">
              {plan.homework.map((h, i) => <div key={i} className="small" style={{ padding: "5px 0" }}>• {toStr(h)}</div>)}
            </Card>
          </div>
        </div>
      ) : (
        <Card className="mt-16">
          <div className="empty">
            <div className="emoji">🧑‍🏫</div>
            <div>填写上方信息，点击「生成教案」，AI 将输出完整的教学设计</div>
          </div>
        </Card>
      )}
    </div>
  );
}
