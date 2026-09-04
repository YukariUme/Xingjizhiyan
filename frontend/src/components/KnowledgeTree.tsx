/** 课程知识思维导图：课程 → 章节 → 知识点（一级）→ 子知识点（二级），带连线、教材切换与在线编辑。 */

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Card, Loading } from "./ui";

export interface SubPoint {
  name: string;
  description: string;
  difficulty: string;
}

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
  sub_points?: SubPoint[];
}

export interface KnowledgeGraphData {
  course: { id: number; name: string };
  chapters: Array<{ id: number; order: number; title: string; official_ref: string }>;
  points: KnowledgeGraphNode[];
  textbooks?: Array<{ id: number; title: string; source: string }>;
}

const PALETTE = [
  { color: "#2a828e", fill: "#e7f2f3" },
  { color: "#47705e", fill: "#ebf2ee" },
  { color: "#b26b16", fill: "#f8efe1" },
  { color: "#6b6f9e", fill: "#eef0f6" },
  { color: "#9d5d74", fill: "#f6ecef" },
  { color: "#5f8a4e", fill: "#eef4ea" },
  { color: "#4a7a9b", fill: "#eaf1f6" },
  { color: "#8a6f3c", fill: "#f4efe3" },
];

const X_COURSE = 0;
const X_CHAPTER = 250;
const X_POINT = 520;
const X_SUB = 830;
const NODE_H = 42;
const SUB_H = 36;
const GAP = 12;

interface LNode {
  key: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  kind: "course" | "chapter" | "point" | "sub";
  color: string;
  fill: string;
  pointId?: number;
  subIndex?: number;
}

interface LEdge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  dash?: boolean;
}

function computeLayout(data: KnowledgeGraphData, expanded: Set<number>) {
  const nodes: LNode[] = [];
  const edges: LEdge[] = [];
  const courseColor = "#173f45";
  let cursor = 40;
  nodes.push({
    key: "course",
    label: data.course.name,
    x: X_COURSE,
    y: cursor,
    w: 190,
    h: 56,
    kind: "course",
    color: courseColor,
    fill: courseColor,
  });

  data.chapters.forEach((ch, ci) => {
    const palette = PALETTE[ci % PALETTE.length];
    const pts = data.points.filter((p) => p.chapter_id === ch.id);
    const blocks = pts.map((p) => {
      const subs = expanded.has(p.id) ? p.sub_points ?? [] : [];
      return NODE_H + subs.length * (SUB_H + GAP) + GAP;
    });
    const blockH = blocks.reduce((s, b) => s + b, 0) || NODE_H + GAP;
    const chY = cursor + blockH / 2 - NODE_H / 2;
    nodes.push({
      key: `ch-${ch.id}`,
      label: `第${ch.order}章 ${ch.title}`,
      x: X_CHAPTER,
      y: chY,
      w: 210,
      h: NODE_H,
      kind: "chapter",
      color: palette.color,
      fill: "#f6faf8",
    });
    edges.push({ x1: X_COURSE + 190, y1: cursor, x2: X_CHAPTER, y2: chY + NODE_H / 2, color: palette.color });

    let py = cursor;
    pts.forEach((p) => {
      const subs = expanded.has(p.id) ? p.sub_points ?? [] : [];
      const pY = py + (subs.length ? subs.length * (SUB_H + GAP) / 2 : 0);
      nodes.push({
        key: `kp-${p.id}`,
        label: p.name,
        x: X_POINT,
        y: pY,
        w: 210,
        h: NODE_H,
        kind: "point",
        color: palette.color,
        fill: palette.fill,
        pointId: p.id,
      });
      edges.push({ x1: X_CHAPTER + 210, y1: chY + NODE_H / 2, x2: X_POINT, y2: pY + NODE_H / 2, color: palette.color });
      subs.forEach((s, j) => {
        const sy = py + j * (SUB_H + GAP);
        nodes.push({
          key: `sub-${p.id}-${j}`,
          label: s.name,
          x: X_SUB,
          y: sy,
          w: 250,
          h: SUB_H,
          kind: "sub",
          color: palette.color,
          fill: "#ffffff",
          pointId: p.id,
          subIndex: j,
        });
        edges.push({ x1: X_POINT + 210, y1: pY + NODE_H / 2, x2: X_SUB, y2: sy + SUB_H / 2, color: palette.color });
      });
      py += NODE_H + subs.length * (SUB_H + GAP) + GAP;
    });
    cursor += blockH + GAP * 3;
  });
  return { nodes, edges, height: cursor + 60 };
}

interface Related {
  knowledge_point: { id: number; name: string; description: string; prerequisites: string[]; related_points: string[] };
  papers: Array<{ id: number; title: string; year: number; venue: string }>;
  documents: Array<{ id: number; title: string; type: string; source: string }>;
}

export default function KnowledgeTree({ data: initialData }: { data: KnowledgeGraphData }) {
  const [data, setData] = useState(initialData);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [selected, setSelected] = useState<KnowledgeGraphNode | null>(null);
  const [related, setRelated] = useState<Related | null>(null);
  const [busy, setBusy] = useState(false);
  const [textbook, setTextbook] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [draft, setDraft] = useState<SubPoint[]>([]);
  const [saving, setSaving] = useState(false);
  const [selSub, setSelSub] = useState<{ pointId: number; index: number; x: number; y: number; h: number } | null>(null);
  const [subEdit, setSubEdit] = useState<SubPoint | null>(null);

  useEffect(() => setData(initialData), [initialData]);

  const visiblePoints = useMemo(() => {
    if (!textbook) return data.points;
    const book = data.textbooks?.find((t) => t.title === textbook);
    if (!book) return data.points;
    const key = (book.title || "").replace(/《|》/g, "").slice(0, 6);
    const matched = data.points.filter((p) => {
      const ch = data.chapters.find((c) => c.id === p.chapter_id);
      return ch && ch.official_ref && ch.official_ref.includes(key);
    });
    return matched.length ? matched : data.points;
  }, [data, textbook]);

  const viewData = useMemo(() => ({ ...data, points: visiblePoints }), [data, visiblePoints]);
  const { nodes, edges, height } = useMemo(() => computeLayout(viewData, expanded), [viewData, expanded]);

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

  const toggleSubs = (node: KnowledgeGraphNode) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(node.id)) next.delete(node.id);
      else next.add(node.id);
      return next;
    });
    if (!editMode) void open(node);
  };

  const enterEdit = (node: KnowledgeGraphNode) => {
    setSelected(node);
    setDraft((node.sub_points ?? []).map((s) => ({ ...s })));
    setEditMode(true);
  };

  const saveSubEdit = async () => {
    if (!selSub || !subEdit) return;
    const p = data.points.find((x) => x.id === selSub.pointId);
    if (!p) return;
    setSaving(true);
    try {
      const subs = (p.sub_points ?? []).map((s, i) => (i === selSub.index ? subEdit : s));
      const res = await api.put<{ ok: boolean; sub_points: SubPoint[] }>(
        `/knowledge/points/${p.id}/subpoints`,
        { sub_points: subs }
      );
      setData((prev) => ({
        ...prev,
        points: prev.points.map((x) => (x.id === p.id ? { ...x, sub_points: res.sub_points } : x)),
      }));
      setSubEdit(null);
      setSelSub(null);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const saveSubPoints = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const res = await api.put<{ ok: boolean; sub_points: SubPoint[] }>(
        `/knowledge/points/${selected.id}/subpoints`,
        { sub_points: draft }
      );
      setData((prev) => ({
        ...prev,
        points: prev.points.map((p) => (p.id === selected.id ? { ...p, sub_points: res.sub_points } : p)),
      }));
      setEditMode(false);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid">
      <Card
        title="课程知识思维导图"
        extra={
          <div className="row wrap" style={{ gap: 8 }}>
            <select className="select" style={{ width: 240 }} value={textbook} onChange={(e) => setTextbook(e.target.value)}>
              <option value="">全部教材</option>
              {(data.textbooks ?? []).map((t) => (
                <option key={t.id} value={t.title}>{t.title}</option>
              ))}
            </select>
            <span className="small muted">点击知识点展开子知识点；「编辑」可在线增删二级知识点</span>
          </div>
        }
      >
        <div style={{ position: "relative", height, overflowX: "auto" }}>
          <svg width={X_SUB + 300} height={height} style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none" }}>
            {edges.map((e, i) => (
              <path
                key={i}
                d={`M ${e.x1} ${e.y1} C ${(e.x1 + e.x2) / 2} ${e.y1}, ${(e.x1 + e.x2) / 2} ${e.y2}, ${e.x2} ${e.y2}`}
                fill="none"
                stroke={e.color}
                strokeWidth={e.dash ? 1.2 : 2}
                strokeDasharray={e.dash ? "5 4" : undefined}
                opacity={0.7}
              />
            ))}
          </svg>
          {nodes.map((n) => (
            <div
              key={n.key}
              style={{
                position: "absolute",
                left: n.x,
                top: n.y,
                width: n.w,
                height: n.h,
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "0 12px",
                borderRadius: 12,
                background: n.kind === "course" ? "linear-gradient(135deg,#173f45,#2a828e)" : n.fill,
                border: `2px solid ${n.color}`,
                color: n.kind === "course" ? "#f4efe7" : "#24322f",
                fontWeight: n.kind === "course" ? 700 : n.kind === "sub" ? 400 : 600,
                fontSize: n.kind === "course" ? 16 : n.kind === "sub" ? 12 : 13,
                boxShadow: "0 4px 14px rgba(28,37,35,0.08)",
                cursor: n.kind === "point" || n.kind === "chapter" ? "pointer" : "default",
                transition: "transform 0.15s ease, box-shadow 0.15s ease",
              }}
              onClick={() => {
                if (n.kind === "point") {
                  const p = data.points.find((x) => x.id === n.pointId);
                  if (p) toggleSubs(p);
                } else if (n.kind === "sub" && n.pointId != null && n.subIndex != null) {
                  setSelSub({ pointId: n.pointId, index: n.subIndex, x: n.x, y: n.y, h: n.h });
                  setSubEdit(null);
                }
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = "0 10px 22px rgba(28,37,35,0.14)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.boxShadow = "0 4px 14px rgba(28,37,35,0.08)";
              }}
            >
              {n.kind === "chapter" && <span style={{ fontSize: 15 }}>▸</span>}
              {n.kind === "point" && (
                <span style={{ fontSize: 12, color: "#fff", background: n.color, borderRadius: 999, width: 18, height: 18, display: "inline-flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
                  {expanded.has(n.pointId!) ? "−" : "+"}
                </span>
              )}
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n.label}</span>
              {n.kind === "point" && n.pointId != null && (
                <button
                  className="btn btn-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    const p = data.points.find((x) => x.id === n.pointId);
                    if (p) enterEdit(p);
                  }}
                >
                  编辑
                </button>
              )}
            </div>
          ))}
          {selSub && (() => {
            const p = data.points.find((x) => x.id === selSub.pointId);
            const sub = subEdit ?? (p?.sub_points ?? [])[selSub.index];
            if (!p || !sub) return null;
            return (
              <div style={{ position: "absolute", left: Math.min(selSub.x, 780), top: selSub.y > 340 ? selSub.y - 340 : selSub.y + selSub.h + 10, width: 320, background: "#fff", border: "1px solid var(--border)", borderRadius: 12, boxShadow: "0 12px 32px rgba(0,0,0,0.18)", padding: 14, zIndex: 30 }}>
                <div className="row space-between" style={{ gap: 8 }}>
                  <b style={{ fontSize: 14 }}>{sub.name}</b>
                  <button className="btn btn-sm" onClick={() => { setSelSub(null); setSubEdit(null); }}>✕</button>
                </div>
                <div className="row wrap mt-8" style={{ gap: 6 }}>
                  <span className={`badge ${sub.difficulty === "难" ? "orange" : "gray"}`}>难度：{sub.difficulty}</span>
                  {!subEdit && (
                    <button className="btn btn-sm" onClick={() => setSubEdit({ ...sub })}>✎ 编辑</button>
                  )}
                </div>
                {subEdit ? (
                  <div className="grid mt-8">
                    <input className="input" value={subEdit.name} onChange={(e) => setSubEdit({ ...subEdit, name: e.target.value })} placeholder="子知识点名称" />
                    <select className="select" value={subEdit.difficulty} onChange={(e) => setSubEdit({ ...subEdit, difficulty: e.target.value })}>
                      <option value="易">易</option><option value="中">中</option><option value="难">难</option>
                    </select>
                    <textarea className="textarea" style={{ minHeight: 130 }} value={subEdit.description} onChange={(e) => setSubEdit({ ...subEdit, description: e.target.value })} placeholder="详细介绍（可编辑）" />
                    <div className="row" style={{ gap: 6 }}>
                      <button className="btn btn-primary btn-sm" disabled={saving} onClick={() => void saveSubEdit()}>{saving ? "保存中…" : "✓ 保存"}</button>
                      <button className="btn btn-sm" onClick={() => setSubEdit(null)}>取消</button>
                    </div>
                  </div>
                ) : (
                  <p className="small mt-8" style={{ whiteSpace: "pre-wrap", color: "var(--text-2)" }}>{sub.description || "暂无介绍"}</p>
                )}
              </div>
            );
          })()}
        </div>
      </Card>

      {(selected || editMode) && (
        <Card
          title={editMode ? `编辑子知识点 · ${selected?.name}` : `知识点详情 · ${selected?.name}`}
          extra={
            <div className="row" style={{ gap: 6 }}>
              {editMode ? (
                <>
                  <button className="btn btn-sm" disabled={saving} onClick={() => void saveSubPoints()}>
                    {saving ? "保存中…" : "✓ 保存"}
                  </button>
                  <button className="btn btn-sm" onClick={() => setEditMode(false)}>取消</button>
                </>
              ) : (
                <button className="btn btn-sm" onClick={() => setSelected(null)}>收起</button>
              )}
            </div>
          }
        >
          {editMode ? (
            <div className="grid">
              {draft.map((s, i) => (
                <div key={i} className="card" style={{ padding: 12 }}>
                  <div className="row wrap" style={{ gap: 6 }}>
                    <input className="input" style={{ width: 200 }} value={s.name} placeholder="子知识点名称"
                      onChange={(e) => setDraft(draft.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
                    <select className="select" style={{ width: 90 }} value={s.difficulty}
                      onChange={(e) => setDraft(draft.map((x, j) => (j === i ? { ...x, difficulty: e.target.value } : x)))}>
                      <option value="易">易</option><option value="中">中</option><option value="难">难</option>
                    </select>
                    <button className="btn btn-sm btn-danger" onClick={() => setDraft(draft.filter((_, j) => j !== i))}>删除</button>
                  </div>
                  <textarea className="textarea" style={{ marginTop: 6 }} value={s.description} placeholder="子知识点说明"
                    onChange={(e) => setDraft(draft.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)))} />
                </div>
              ))}
              <button className="btn btn-sm" onClick={() => setDraft([...draft, { name: "", description: "", difficulty: "中" }])}>
                ＋ 添加子知识点
              </button>
            </div>
          ) : selected ? (
            <>
              <p className="small muted">{selected.description || "暂无描述"}</p>
              <div className="row wrap mt-8" style={{ gap: 6 }}>
                <span className={`badge ${selected.difficulty === "难" ? "orange" : "gray"}`}>难度：{selected.difficulty}</span>
                {selected.prerequisites.map((p) => <span key={p} className="badge gray">←前置 {p}</span>)}
                {selected.paper_count > 0 && <span className="badge purple">📄{selected.paper_count} 篇论文</span>}
                <button className="btn btn-sm" onClick={() => enterEdit(selected)}>✎ 编辑子知识点</button>
              </div>
              {busy ? (
                <Loading text="加载关联内容…" />
              ) : (
                <>
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
                  {(!related || (related.papers.length === 0 && related.documents.length === 0)) && (
                    <div className="muted small mt-16">暂无直接关联的论文/资料</div>
                  )}
                </>
              )}
            </>
          ) : null}
        </Card>
      )}
    </div>
  );
}
