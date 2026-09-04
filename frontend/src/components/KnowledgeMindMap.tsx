/** 课程知识图谱（思维导图）：课程 → 章节 → 知识点；点击知识点钻取子知识点/论文。 */

import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Card, Loading } from "./ui";

export interface KnowledgeGraphNode {
  id: number;
  name: string;
  chapter_id: number | null;
  description: string;
  difficulty: string;
  prerequisites: string[];
  prereq_ids: number[];
  related_ids: number[];
  paper_count: number;
}

export interface KnowledgeGraphData {
  course: { id: number; name: string };
  chapters: Array<{ id: number; order: number; title: string; official_ref: string }>;
  points: KnowledgeGraphNode[];
}

const DIFF_TONE: Record<string, string> = {
  易: "#5f8a4e",
  中: "#2a828e",
  难: "#b26b16",
};

interface Related {
  knowledge_point: { id: number; name: string; description: string; prerequisites: string[]; related_points: string[] };
  papers: Array<{ id: number; title: string; year: number; venue: string }>;
  documents: Array<{ id: number; title: string; type: string; source: string }>;
}

export default function KnowledgeMindMap({ data }: { data: KnowledgeGraphData }) {
  const [selected, setSelected] = useState<KnowledgeGraphNode | null>(null);
  const [related, setRelated] = useState<Related | null>(null);
  const [busy, setBusy] = useState(false);

  const open = async (node: KnowledgeGraphNode) => {
    setSelected(node);
    setBusy(true);
    setRelated(null);
    try {
      const res = await api.get<Related>(`/knowledge/points/${node.id}/related`);
      setRelated(res);
    } catch {
      setRelated(null);
    } finally {
      setBusy(false);
    }
  };

  const subNodes = [
    ...(related?.knowledge_point.prerequisites ?? []).map((n) => ({ name: n, kind: "前置" as const })),
    ...(related?.knowledge_point.related_points ?? []).map((n) => ({ name: n, kind: "关联" as const })),
  ].filter((v, i, arr) => arr.findIndex((x) => x.name === v.name && x.kind === v.kind) === i);

  return (
    <div className="grid">
      <Card>
        <div className="mindmap">
          <div className="mindmap-root">
            <span className="mindmap-dot" />
            <b>{data.course.name}</b>
            <span className="badge gray">{data.points.length} 知识点</span>
          </div>
          {data.chapters.map((ch) => {
            const pts = data.points.filter((p) => p.chapter_id === ch.id);
            if (pts.length === 0) return null;
            return (
              <div key={ch.id} className="mindmap-branch">
                <div className="mindmap-chapter">
                  <span className="mindmap-dot" />
                  <b>第 {ch.order} 章 · {ch.title}</b>
                </div>
                <div className="mindmap-leaves">
                  {pts.map((p) => (
                    <button
                      key={p.id}
                      className={`mindmap-leaf ${selected?.id === p.id ? "active" : ""}`}
                      onClick={() => void open(p)}
                    >
                      <span className="mindmap-leaf-dot" style={{ background: DIFF_TONE[p.difficulty] ?? "#2a828e" }} />
                      {p.name}
                      {p.paper_count > 0 && <span className="badge purple">📄{p.paper_count}</span>}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {selected && (
        <Card title={`子知识点 · ${selected.name}`} extra={<button className="btn btn-sm" onClick={() => setSelected(null)}>收起</button>}>
          <p className="small muted">{selected.description || "暂无描述"}</p>
          {busy ? (
            <Loading text="加载子知识点…" />
          ) : (
            <>
              <div className="row wrap mt-8" style={{ gap: 8 }}>
                <span className="badge orange" style={{ fontWeight: 700 }}>{selected.name}</span>
                {subNodes.map((n) => (
                  <span key={`${n.kind}-${n.name}`} className={`badge ${n.kind === "前置" ? "gray" : "purple"}`}>
                    {n.kind === "前置" ? "←前置" : "关联"} {n.name}
                  </span>
                ))}
                {subNodes.length === 0 && <span className="muted small">该知识点暂无前置/关联子知识点</span>}
              </div>

              {(related?.papers.length ?? 0) > 0 && (
                <div className="mt-16">
                  <h3>相关论文</h3>
                  {related!.papers.map((p) => (
                    <div key={p.id} className="small" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                      <b>{p.title}</b>
                      <div className="muted">{p.venue} · {p.year}</div>
                      <Link to={`/research/papers?paper=${p.id}`} className="btn btn-sm mt-8">阅读论文 →</Link>
                    </div>
                  ))}
                </div>
              )}

              {(related?.documents.length ?? 0) > 0 && (
                <div className="mt-16">
                  <h3>关联资料</h3>
                  {related!.documents.map((d) => (
                    <div key={d.id} className="small" style={{ padding: "5px 0" }}>
                      <b>{d.title}</b> · {d.source} · {d.type}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </Card>
      )}
    </div>
  );
}
