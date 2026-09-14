/** AI 圆桌讨论：预置第一轮 → 学生加入 → 他人友善回应 → 实时总结。 */

import { useState } from "react";
import { api } from "../api";
import { Card, ErrorBanner, Loading } from "../components/ui";
import { AiMeta } from "../components/AiMeta";

interface Persona {
  id: string;
  name: string;
  role: string;
  color: string;
}

interface Whiteboard {
  kind: "points" | "compare";
  title?: string;
  items?: string[];
  left?: string;
  right?: string;
}

interface Turn {
  speaker: string;
  stance: string;
  content: string;
  whiteboard: Whiteboard | null;
  student?: boolean;
}

const PRESETS = ["递归与迭代", "不同排序算法的取舍", "为什么需要哈希表", "链表与数组的适用场景"];

export default function Roundtable() {
  const [topic, setTopic] = useState("");
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [provider, setProvider] = useState("");
  const [references, setReferences] = useState<Array<{ title?: string; source?: string; source_level?: string; page?: string }>>([]);

  const start = async (t: string) => {
    const q = t.trim();
    if (!q) return;
    setLoading(true);
    setError("");
    setSummary("");
    try {
      const res = await api.post<{ topic: string; personas: Persona[]; turns: Turn[]; provider?: string; references?: Array<{ title?: string; source?: string; source_level?: string; page?: string }> }>("/roundtable/start", { topic: q });
      setTopic(res.topic);
      setPersonas(res.personas);
      setTurns(res.turns);
      setProvider(res.provider ?? "");
      setReferences(res.references ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setLoading(false);
    }
  };

  const join = async () => {
    const msg = input.trim();
    if (!msg || !topic) return;
    const next = [...turns, { speaker: "我", stance: "学生", content: msg, whiteboard: null, student: true }];
    setTurns(next);
    setInput("");
    setBusy(true);
    try {
      const res = await api.post<{ turns: Turn[]; provider?: string; references?: Array<{ title?: string; source?: string; source_level?: string; page?: string }> }>("/roundtable/reply", {
        topic,
        turns,
        student_message: msg,
      });
      setTurns([...next, ...res.turns]);
      setProvider(res.provider ?? provider);
      setReferences(res.references ?? references);
    } catch (e) {
      setError(e instanceof Error ? e.message : "回应失败");
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    if (!topic || turns.length === 0) return;
    setBusy(true);
    try {
      const res = await api.post<{ summary: string; provider?: string; references?: Array<{ title?: string; source?: string; source_level?: string; page?: string }> }>("/roundtable/summary", { topic, turns });
      setSummary(res.summary);
      setProvider(res.provider ?? provider);
      setReferences(res.references ?? references);
    } catch (e) {
      setError(e instanceof Error ? e.message : "总结失败");
    } finally {
      setBusy(false);
    }
  };

  if (!topic || personas.length === 0) {
    return (
      <div className="page">
        <div className="page-header">
          <div>
            <h1>AI 圆桌讨论</h1>
            <p>几位同学先各抒己见，资深程序员和老师也会适时补充，你可以随时加入，大家会友善地回应你。</p>
          </div>
        </div>
        <Card title="发起一场圆桌讨论">
          <div className="field">
            <label>讨论主题</label>
            <input className="input" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="输入你想讨论的 CS 问题" onKeyDown={(e) => e.key === "Enter" && void start(topic)} />
          </div>
          <div className="row wrap" style={{ gap: 6 }}>
            {PRESETS.map((p) => (
              <button key={p} className="btn btn-sm" onClick={() => { setTopic(p); void start(p); }}>
                {p}
              </button>
            ))}
          </div>
          <button className="btn btn-primary mt-16" onClick={() => void start(topic)} disabled={loading || !topic.trim()}>
            {loading ? "组织第一轮中…" : "开始讨论"}
          </button>
          {error && <ErrorBanner message={error} />}
        </Card>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>AI 圆桌讨论</h1>
          <p className="muted">友善、鼓励式的讨论：你可以随时加入，表达你的想法。</p>
        </div>
        <button className="btn btn-primary" onClick={() => void finish()} disabled={busy || !!summary}>
          {summary ? "已总结" : "结束并总结"}
        </button>
      </div>

      <Card title={`圆桌 · ${topic}`}>
        <div className="row wrap" style={{ gap: 10 }}>
          {personas.map((p) => (
            <div key={p.id} className="row" style={{ gap: 8 }}>
              <span className="avatar" style={{ background: p.color }}>{(p.name ?? "").slice(0, 1)}</span>
              <div>
                <b className="small">{p.name}</b>
                <div className="small muted">{p.role}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="roundtable-log">
        {turns.map((t, i) => (
          <div key={i} className={`roundtable-msg ${t.student ? "student" : ""}`}>
            <div className="row mb-4">
              <b>{t.speaker}</b>
              {t.stance && <span className="badge gray">{t.stance}</span>}
            </div>
            <p>{t.content}</p>
            {t.whiteboard && <Whiteboard board={t.whiteboard} />}
          </div>
        ))}
        {busy && <div className="small muted">大家正在思考并回应你…</div>}
      </div>

      {summary ? (
        <Card className="mt-16" title="🎉 讨论总结">
          <p style={{ whiteSpace: "pre-wrap" }}>{summary}</p>
        </Card>
      ) : (
        <Card className="mt-16" title="加入讨论">
          <div className="row" style={{ alignItems: "flex-end" }}>
            <textarea className="textarea grow" style={{ minHeight: 60 }} value={input} onChange={(e) => setInput(e.target.value)} placeholder="说说你的看法，大家会友善地回应你…" onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void join(); } }} />
            <button className="btn btn-primary" onClick={() => void join()} disabled={busy || !input.trim()}>
              {busy ? "回应中…" : "发言"}
            </button>
          </div>
        </Card>
      )}

      <AiMeta provider={provider} references={references} />

      {error && <ErrorBanner message={error} />}
    </div>
  );
}

function Whiteboard({ board }: { board: Whiteboard }) {
  return (
    <div className="whiteboard mt-8">
      <div className="small muted mb-8">📋 {board.title || "白板"}</div>
      {board.kind === "points" && board.items ? (
        <div className="row wrap" style={{ gap: 8 }}>
          {board.items.map((it, i) => (
            <span key={i} className="badge badge-purple">{it}</span>
          ))}
        </div>
      ) : board.kind === "compare" ? (
        <div className="grid grid-2">
          <div className="whiteboard-col"><div className="small muted">左</div><b>{board.left}</b></div>
          <div className="whiteboard-col"><div className="small muted">右</div><b>{board.right}</b></div>
        </div>
      ) : null}
    </div>
  );
}
