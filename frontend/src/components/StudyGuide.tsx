/** 可重复自学链：围绕一个知识点，按有序步骤逐步推进 + 可回放时间线 + 人工跳步。 */

import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { CodeEditor } from "./CodeEditor";
import { DataStructurePlayer } from "./DataStructurePlayer";
import { AiMeta } from "./AiMeta";
import { Card, EmptyState, ErrorBanner, Loading, Progress } from "./ui";
import type { LearningSession, SessionStep } from "../types";

interface ChapterOpt {
  key: string;
  label: string;
}

const STEP_LABEL: Record<string, string> = {
  goal: "目标",
  warmup: "引入",
  explain: "讲解",
  visualize: "演示",
  code: "代码",
  practice: "练习",
  check: "自检",
  wrapup: "小结",
};

const STEP_ICON: Record<string, string> = {
  goal: "🎯",
  warmup: "💭",
  explain: "📖",
  visualize: "🧭",
  code: "⌨️",
  practice: "✍️",
  check: "🔍",
  wrapup: "🏁",
};

export default function StudyGuide({
  courseId,
  courseName,
  chapters,
  initialChapterId,
}: {
  courseId: number;
  courseName: string;
  chapters: ChapterOpt[];
  initialChapterId?: number;
}) {
  const [phase, setPhase] = useState<"setup" | "running">("setup");
  const [chapterId, setChapterId] = useState("");
  const [kpId, setKpId] = useState("");
  const [depth, setDepth] = useState("standard");
  const [kps, setKps] = useState<Array<{ id: number; name: string }>>([]);
  const [sessions, setSessions] = useState<LearningSession[]>([]);
  const [session, setSession] = useState<LearningSession | null>(null);
  const [current, setCurrent] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<
    Record<number, {
      message?: string;
      hint?: string;
      correct?: boolean;
      answer?: string;
      analysis?: string;
      error_analysis?: string;
      knowledge_points?: string[];
    }>
  >({});
  const [busy, setBusy] = useState(false);

  const loadSessions = async () => {
    try {
      setSessions(await api.get<LearningSession[]>("/sessions/list"));
    } catch {
      /* 历史列表失败不阻塞主流程 */
    }
  };

  useEffect(() => {
    void loadSessions();
  }, []);

  useEffect(() => {
    if (initialChapterId) {
      setChapterId(String(initialChapterId));
    }
  }, [initialChapterId]);

  useEffect(() => {
    if (!chapterId) {
      setKps([]);
      setKpId("");
      return;
    }
    let alive = true;
    api
      .get<{ knowledge_points: Array<{ id: number; name: string }> }>(`/curriculum/chapters/${chapterId}/view`)
      .then((d) => {
        if (alive) {
          setKps(d.knowledge_points || []);
          setKpId("");
        }
      })
      .catch(() => alive && setKps([]));
    return () => {
      alive = false;
    };
  }, [chapterId]);

  const start = async () => {
    setLoading(true);
    setError("");
    try {
      const s = await api.post<LearningSession>("/sessions/create", {
        course_id: courseId,
        chapter_id: chapterId ? Number(chapterId) : undefined,
        knowledge_point_id: kpId ? Number(kpId) : undefined,
        depth,
      });
      setSession(s);
      setCurrent(s.current_index ?? 0);
      setFeedback({});
      setPhase("running");
      void recordView(s, 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  };

  const resume = (s: LearningSession) => {
    setSession(s);
    setCurrent(s.current_index ?? 0);
    setFeedback({});
    setPhase("running");
  };

  const recordView = async (s: LearningSession, index: number) => {
    try {
      await api.post(`/sessions/${s.id}/steps/${index}/action`, { action: "view" });
    } catch {
      /* 留痕失败不阻塞 */
    }
  };

  const goTo = (index: number) => {
    if (!session) return;
    const i = Math.max(0, Math.min(session.steps.length - 1, index));
    setCurrent(i);
    setAnswer("");
    void recordView(session, i);
  };

  const submitStep = async () => {
    if (!session) return;
    const step = session.steps[current];
    if (!step) return;
    setBusy(true);
    try {
      const res = await api.post<{
        message?: string;
        hint?: string;
        correct?: boolean;
        answer?: string;
        analysis?: string;
        error_analysis?: string;
        knowledge_points?: string[];
      }>(
        `/sessions/${session.id}/steps/${current}/action`,
        { action: "submit", answer }
      );
      setFeedback((f) => ({ ...f, [current]: res }));
    } catch (e) {
      setFeedback((f) => ({ ...f, [current]: { message: e instanceof Error ? e.message : "提交失败" } }));
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    if (!session) return;
    try {
      await api.post(`/sessions/${session.id}/complete`);
    } catch {
      /* 忽略 */
    }
    setPhase("setup");
    setSession(null);
    setCurrent(0);
    void loadSessions();
  };

  if (phase === "setup") {
    return (
      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <Card title="开始一次自学">
          <p className="small muted">
            选一个知识点，AI 会生成一条“目标 → 引入 → 讲解 → 演示/代码 → 练习 → 自检 → 小结”的交互链，跟着走即可。
          </p>
          <div className="field">
            <label>章节</label>
            <select className="select" value={chapterId} onChange={(e) => setChapterId(e.target.value)}>
              <option value="">不限章节（整门课）</option>
              {chapters.map((c) => (
                <option key={c.key} value={c.key}>{c.label}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>知识点（可选，不选自动取章节第一个）</label>
            <select className="select" value={kpId} onChange={(e) => setKpId(e.target.value)} disabled={!kps.length}>
              <option value="">{kps.length ? "自动选择" : "先选章节"}</option>
              {kps.map((k) => (
                <option key={k.id} value={k.id}>{k.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>深度</label>
            <div className="row wrap">
              {[
                { key: "quick", label: "快速热身" },
                { key: "standard", label: "标准学习" },
                { key: "deep", label: "深度精讲" },
              ].map((d) => (
                <button
                  key={d.key}
                  className={`btn btn-sm ${depth === d.key ? "btn-primary" : ""}`}
                  onClick={() => setDepth(d.key)}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>
          {error && <ErrorBanner message={error} />}
          <button className="btn btn-primary btn-lg" onClick={() => void start()} disabled={loading}>
            {loading ? "AI 生成中…" : "✦ 开始自学"}
          </button>
        </Card>

        <Card title={`我的自学记录（${sessions.length}）`}>
          {sessions.length === 0 ? (
            <EmptyState emoji="🧭" text="还没有自学记录，开始一次吧" />
          ) : (
            sessions.map((s) => (
              <div
                key={s.id}
                className="row space-between study-history"
                onClick={() => resume(s)}
              >
                <div className="grow">
                  <b>{s.title}</b>
                  <div className="small muted">
                    {s.depth} · {s.steps.length} 步 · {s.status === "completed" ? "已完成" : `进行到第 ${(s.current_index ?? 0) + 1} 步`}
                  </div>
                </div>
                <span className="btn btn-sm">继续</span>
              </div>
            ))
          )}
        </Card>
      </div>
    );
  }

  if (!session) return <Loading />;
  const step = session.steps[current];
  const total = session.steps.length;
  const fb = feedback[current];

  return (
    <div className="study-guide">
      <div className="study-progress-row">
        <div className="row space-between">
          <span className="small muted">学习进度</span>
          <span className="small muted">{current + 1} / {total} 步</span>
        </div>
        <Progress value={((current + 1) / Math.max(1, total)) * 100} />
      </div>
      <div className="study-stepper" aria-label="学习进度">
        {session.steps.map((s, i) => (
          <button
            key={i}
            className={`study-step-dot ${i < current ? "done" : ""} ${i === current ? "active" : ""}`}
            onClick={() => goTo(i)}
            title={`${STEP_LABEL[s.type] ?? s.type}${s.title ? `：${s.title}` : ""}`}
          >
            <span className="study-step-icon">{STEP_ICON[s.type] ?? "•"}</span>
            <span className="study-step-label">{STEP_LABEL[s.type] ?? s.type}</span>
            {i < current && <span className="study-step-check">✓</span>}
          </button>
        ))}
      </div>

      <div className="study-step-panel" key={current}>
        <StepRenderer step={step} answer={answer} setAnswer={setAnswer} />
      </div>

      {fb && (
        <div className={`study-feedback ${fb.correct === true ? "ok" : fb.correct === false ? "bad" : ""}`}>
          <div className="row space-between">
            <b>{fb.message}</b>
            {fb.correct != null && (
              <span className={`badge ${fb.correct ? "green" : "red"}`}>
                {fb.correct ? "正确" : "不正确"}
              </span>
            )}
          </div>
          {fb.answer && (
            <div className="small mt-8">
              <b>参考答案：</b>{fb.answer}
            </div>
          )}
          {fb.analysis && (
            <div className="small mt-8">
              <b>解析：</b>{fb.analysis}
            </div>
          )}
          {fb.error_analysis && (
            <div className="small mt-8" style={{ color: "var(--warning)" }}>
              <b>错因：</b>{fb.error_analysis}
            </div>
          )}
          {fb.knowledge_points?.length ? (
            <div className="row wrap mt-8">
              {fb.knowledge_points.map((k) => (
                <span key={k} className="badge">{k}</span>
              ))}
            </div>
          ) : null}
          {fb.hint && <div className="small muted mt-8">💡 {fb.hint}</div>}
        </div>
      )}

      {["warmup", "practice", "check"].includes(step.type) && (
        <div className="row mt-16">
          <button className="btn btn-primary" onClick={() => void submitStep()} disabled={busy}>
            {busy ? "提交中…" : "提交"}
          </button>
        </div>
      )}

      <div className="study-controls">
        <button className="btn" onClick={() => goTo(current - 1)} disabled={current === 0}>← 上一步</button>
        <span className="small muted">{current + 1} / {total}</span>
        {current < total - 1 ? (
          <button className="btn btn-primary" onClick={() => goTo(current + 1)}>下一步 →</button>
        ) : (
          <button className="btn btn-primary" onClick={() => void finish()}>✓ 完成本次自学</button>
        )}
      </div>

      <AiMeta provider={session.provider} references={session.references} />

      <div className="study-foot muted small">
        每次推进都会留痕，可点击上方步骤任意跳转回看。
      </div>
    </div>
  );
}

function StepRenderer({
  step,
  answer,
  setAnswer,
}: {
  step: SessionStep;
  answer: string;
  setAnswer: (v: string) => void;
}) {
  switch (step.type) {
    case "goal":
      return (
        <Card title="🎯 学习目标">
          <p className="study-goal">{step.text}</p>
        </Card>
      );
    case "warmup":
      return (
        <Card title="💭 先想一想">
          <p>{step.question}</p>
          {step.options?.length ? (
            <div className="row wrap mt-8">
              {step.options.map((o, i) => (
                <button key={i} className={`btn btn-sm ${answer === o ? "btn-primary" : ""}`} onClick={() => setAnswer(o)}>
                  {o}
                </button>
              ))}
            </div>
          ) : (
            <textarea className="textarea mt-8" value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="写下你的想法…" />
          )}
        </Card>
      );
    case "explain":
      return (
        <Card title={step.title || "讲解"}>
          <ExplainContent content={step.content || ""} anchor={step.anchor} />
          {step.example && (
            <div className="study-example mt-16">
              <div className="small muted mb-8">例</div>
              <div>{step.example}</div>
            </div>
          )}
        </Card>
      );
    case "visualize":
      return <VisualizeStep step={step} />;
    case "code":
      return (
        <CodePlayground step={step} code={answer || step.code || ""} onCodeChange={setAnswer} />
      );
    case "practice":
      return (
        <Card title="✍️ 随堂练习">
          <p>{step.question}</p>
          {step.options?.length ? (
            <div className="row wrap mt-8">
              {step.options.map((o, i) => (
                <button key={i} className={`btn btn-sm ${answer === o ? "btn-primary" : ""}`} onClick={() => setAnswer(o)}>
                  {o}
                </button>
              ))}
            </div>
          ) : (
            <textarea className="textarea mt-8" value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="输入你的答案…" />
          )}
        </Card>
      );
    case "check":
      return (
        <Card title="🔍 自检">
          <p>{step.prompt}</p>
          <textarea className="textarea mt-8" value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="用自己的话说一遍…" />
        </Card>
      );
    case "wrapup":
      return (
        <Card title="🏁 本次小结">
          <p>{step.summary}</p>
          {step.weak_points?.length ? (
            <div className="row wrap mt-8">
              {step.weak_points.map((w, i) => (
                <span key={i} className="badge badge-orange">{w}</span>
              ))}
            </div>
          ) : null}
          {step.suggestion && <div className="study-example mt-16">💡 {step.suggestion}</div>}
        </Card>
      );
    default:
      return <Card>未知步骤类型</Card>;
  }
}

function CodePlayground({
  step,
  code,
  onCodeChange,
}: {
  step: SessionStep;
  code: string;
  onCodeChange: (v: string) => void;
}) {
  const [stdin, setStdin] = useState("");
  const [result, setResult] = useState<{
    ok?: boolean;
    stdout?: string;
    stderr?: string;
    exit_code?: number;
    runtime_ms?: number;
    error?: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    setResult(null);
    try {
      const res = await api.post<typeof result>("/playground/run", {
        code,
        language: step.language || "python",
        stdin,
      });
      setResult(res);
    } catch (e) {
      setResult({ ok: false, error: e instanceof Error ? e.message : "运行失败" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title={`⌨️ 代码${step.language ? ` · ${step.language}` : ""}`}>
      <CodeEditor
        value={code}
        language={step.language || "python"}
        minHeight={160}
        onChange={onCodeChange}
      />
      <div className="field mt-8">
        <label>标准输入（可选，按行输入）</label>
        <textarea className="textarea" style={{ minHeight: 52 }} value={stdin} onChange={(e) => setStdin(e.target.value)} placeholder="stdin…" />
      </div>
      <div className="row mt-8">
        <button className="btn btn-primary" onClick={() => void run()} disabled={busy}>
          {busy ? "运行中…" : "▶ 运行"}
        </button>
        {result?.runtime_ms != null && <span className="small muted">耗时 {result.runtime_ms}ms</span>}
      </div>
      {step.expected_output && (
        <div className="study-output mt-8">
          <div className="small muted mb-8">预期输出</div>
          <pre>{step.expected_output}</pre>
        </div>
      )}
      {result && (
        <div className="study-output mt-8">
          <div className="small muted mb-8">运行输出</div>
          {result.error && <pre style={{ color: "var(--danger)" }}>{result.error}</pre>}
          {result.stdout !== undefined && result.stdout !== "" && <pre>{result.stdout}</pre>}
          {result.stderr && <pre style={{ color: "var(--warning)" }}>{result.stderr}</pre>}
        </div>
      )}
    </Card>
  );
}

function ExplainContent({ content, anchor }: { content: string; anchor?: string }) {
  if (!anchor) return <p className="study-content">{content}</p>;
  const idx = content.indexOf(anchor);
  if (idx < 0) return <p className="study-content">{content}</p>;
  return (
    <p className="study-content">
      {content.slice(0, idx)}
      <mark className="study-anchor">{content.slice(idx, idx + anchor.length)}</mark>
      {content.slice(idx + anchor.length)}
    </p>
  );
}

const DS_IDS = ["stack", "queue", "list", "bst", "sorting", "traversal"];

function dsKindFor(step: SessionStep): string {
  const p = (step.payload ?? {}) as Record<string, unknown>;
  const cand = p.ds ?? p.kind ?? p.structure ?? step.kind;
  if (typeof cand === "string") {
    if (DS_IDS.includes(cand)) return cand;
    if (cand === "algorithm") return "sorting";
    if (cand === "data_structure" || cand === "simulation") return "stack";
    if (cand === "traversal" || cand === "tree") return "traversal";
  }
  return "stack";
}

function VisualizeStep({ step }: { step: SessionStep }) {
  const kind = dsKindFor(step);
  return (
    <Card title={`🧭 ${step.title || "可视化演示"}`}>
      <DataStructurePlayer key={kind} kind={kind} />
    </Card>
  );
}
