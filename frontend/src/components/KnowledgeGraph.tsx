/** 课程知识图谱：Cytoscape + Dagre 层次布局，课程 → 章节 → 知识点 → 论文。 */

import { useEffect, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import dagre from "cytoscape-dagre";

cytoscape.use(dagre);

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

export interface KnowledgeGraphChapter {
  id: number;
  order: number;
  title: string;
  official_ref: string;
}

export interface KnowledgeGraphData {
  course: { id: number; name: string };
  chapters: KnowledgeGraphChapter[];
  points: KnowledgeGraphNode[];
}

// 章节配色（与平台深青蓝 / 青绿 / 赭石体系一致）
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

interface Props {
  data: KnowledgeGraphData;
  onSelect?: (node: KnowledgeGraphNode) => void;
  height?: number;
}

export default function KnowledgeGraph({ data, onSelect, height = 560 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const nodeById = new Map(data.points.map((p) => [p.id, p]));
    const chapterIndex = new Map(data.chapters.map((c, i) => [c.id, i]));
    const colorOf = (chapterId: number | null) => {
      const i = chapterId != null ? chapterIndex.get(chapterId) ?? 0 : 0;
      return PALETTE[i % PALETTE.length];
    };

    const chapterEls: ElementDefinition[] = data.chapters.map((c, i) => ({
        data: {
          id: `ch-${c.id}`,
          label: `第 ${c.order} 章 · ${c.title.length > 12 ? `${c.title.slice(0, 12)}…` : c.title}`,
          kind: "chapter",
          color: PALETTE[i % PALETTE.length].color,
        },
      }));
    const pointEls: ElementDefinition[] = data.points.map((p) => {
        const palette = colorOf(p.chapter_id);
        const badge = p.paper_count > 0 ? `  📄${p.paper_count}` : "";
        return {
          data: {
            id: `kp-${p.id}`,
            label: `${p.name}${badge}`,
            kind: "point",
            color: palette.color,
            fill: palette.fill,
            difficulty: p.difficulty,
          },
        };
      });
    const courseEdge: ElementDefinition[] = data.chapters.length
      ? [{ data: { id: "e-course", source: "course", target: `ch-${data.chapters[0].id}`, rel: "course" } }]
      : [];
    const chapterEdges: ElementDefinition[] = data.chapters.flatMap((c) => {
        const points = data.points.filter((p) => p.chapter_id === c.id);
        return points.map((p) => ({
          data: { id: `e-${c.id}-${p.id}`, source: `ch-${c.id}`, target: `kp-${p.id}`, rel: "chapter" },
        }));
      });
    const prereqEdges: ElementDefinition[] = data.points.flatMap((p) =>
        (p.prereq_ids || [])
          .filter((rid) => nodeById.has(rid))
          .map((rid) => ({
            data: { id: `pr-${rid}-${p.id}`, source: `kp-${rid}`, target: `kp-${p.id}`, rel: "prereq" },
          }))
      );
    const relatedEdges: ElementDefinition[] = data.points.flatMap((p) =>
        (p.related_ids || [])
          .filter((rid) => rid > p.id && nodeById.has(rid))
          .map((rid) => ({
            data: { id: `rl-${p.id}-${rid}`, source: `kp-${p.id}`, target: `kp-${rid}`, rel: "related" },
          }))
      );
    const elements: ElementDefinition[] = [
      { data: { id: "course", label: data.course.name, kind: "course" } },
      ...chapterEls,
      ...pointEls,
      ...courseEdge,
      ...chapterEdges,
      ...prereqEdges,
      ...relatedEdges,
    ];

    const cy = cytoscape({
      container,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "font-family": "Noto Serif SC, Songti SC, serif",
            "font-size": 11,
            color: "#24322f",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "ellipsis",
            "text-max-width": "140px",
            "overlay-opacity": 0,
          },
        },
        {
          selector: 'node[kind = "course"]',
          style: {
            shape: "round-rectangle",
            "background-color": "#173f45",
            "border-color": "#2a828e",
            "border-width": 2,
            color: "#f4efe7",
            "font-size": 16,
            "font-weight": 700,
            width: 190,
            height: 54,
            "text-max-width": "170px",
            "z-index": 10,
          },
        },
        {
          selector: 'node[kind = "chapter"]',
          style: {
            shape: "round-rectangle",
            "background-color": "#f6faf8",
            "border-color": "data(color)",
            "border-width": 2,
            width: 170,
            height: 40,
            "font-size": 11.5,
            "font-weight": 600,
            "z-index": 5,
          },
        },
        {
          selector: 'node[kind = "point"]',
          style: {
            shape: "round-rectangle",
            "background-color": "data(fill)",
            "border-color": "data(color)",
            "border-width": 1.5,
            width: 158,
            height: 32,
            "font-size": 10.5,
          },
        },
        {
          selector: 'node[kind = "point"][difficulty = "难"]',
          style: { "border-width": 2.5, "font-weight": 600 },
        },
        {
          selector: "edge",
          style: {
            width: 1.2,
            "line-color": "#c3cfcb",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#c3cfcb",
            "arrow-scale": 0.7,
            "curve-style": "bezier",
            "opacity": 0.85,
          },
        },
        {
          selector: 'edge[rel = "course"]',
          style: { "line-color": "#8aa8a0", "target-arrow-color": "#8aa8a0", width: 2 },
        },
        {
          selector: 'edge[rel = "related"]',
          style: {
            "line-style": "dashed",
            "line-color": "#c77b16",
            "target-arrow-color": "#c77b16",
            width: 1.4,
            opacity: 0.7,
          },
        },
        {
          selector: 'edge[rel = "prereq"]',
          style: {
            "line-color": "#2a828e",
            "target-arrow-color": "#2a828e",
            width: 1.7,
            opacity: 0.85,
          },
        },
        {
          selector: ":selected",
          style: { "border-width": 3, "border-color": "#b26b16", "z-index": 20 },
        },
        {
          selector: ".highlight",
          style: { "border-width": 3, "border-color": "#b26b16", "z-index": 20 },
        },
        {
          selector: ".faded",
          style: { opacity: 0.18 },
        },
      ],
      layout: {
        name: "dagre",
        rankDir: "LR",
        nodesep: 26,
        ranksep: 88,
        spacingFactor: 1.08,
        animate: true,
        fit: true,
        padding: 30,
      } as cytoscape.LayoutOptions,
      wheelSensitivity: 0.25,
      minZoom: 0.2,
      maxZoom: 2.5,
    });

    cyRef.current = cy;

    const highlight = (node: cytoscape.NodeSingular) => {
      cy.elements().removeClass("faded highlight");
      const neighborhood = node.closedNeighborhood();
      cy.elements().addClass("faded");
      neighborhood.removeClass("faded");
      node.addClass("highlight");
    };
    const clearHighlight = () => cy.elements().removeClass("faded highlight");

    cy.on("tap", "node", (e) => {
      const d = e.target.data();
      if (d.kind === "point" && nodeById.has(Number(d.id.replace("kp-", "")))) {
        onSelectRef.current?.(nodeById.get(Number(d.id.replace("kp-", "")))!);
      } else if (d.kind === "point" || d.kind === "chapter") {
        highlight(e.target);
      }
    });
    cy.on("mouseover", "node", (e) => highlight(e.target));
    cy.on("mouseout", "node", clearHighlight);

    const ro = new ResizeObserver(() => cy.resize());
    ro.observe(container);

    return () => {
      ro.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, [data]);

  const zoomBy = (factor: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.animate({ zoom: Math.min(2.5, Math.max(0.2, cy.zoom() * factor)), duration: 150 });
  };
  const fit = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.animate({ fit: { eles: cy.elements(), padding: 30 }, duration: 200 });
  };

  const legend = data.chapters.map((c, i) => ({
    label: `第${c.order}章`,
    color: PALETTE[i % PALETTE.length].color,
  }));

  return (
    <div>
      <div className="row space-between mb-8">
        <div className="row wrap" style={{ gap: 6 }}>
          {legend.map((l) => (
            <span key={l.label} className="row" style={{ gap: 5, alignItems: "center", fontSize: 12 }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, background: l.color, display: "inline-block" }} />
              {l.label}
            </span>
          ))}
        </div>
        <div className="row" style={{ gap: 6 }}>
          <button className="btn btn-sm" onClick={() => zoomBy(1.2)} title="放大">＋</button>
          <button className="btn btn-sm" onClick={() => zoomBy(0.8)} title="缩小">－</button>
          <button className="btn btn-sm" onClick={fit} title="适应画布">⛶ 适应</button>
        </div>
      </div>
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height,
          borderRadius: 12,
          border: "1px solid var(--border)",
          background:
            "radial-gradient(circle at 20% 20%, rgba(42,130,142,0.05), transparent 45%), #fbfaf7",
        }}
      />
      <div className="row wrap mt-8" style={{ gap: 14, fontSize: 12, color: "var(--text-2)" }}>
        <span className="row" style={{ gap: 5, alignItems: "center" }}>
          <span style={{ width: 18, height: 3, background: "#2a828e", borderRadius: 2, display: "inline-block" }} />
          前置关系
        </span>
        <span className="row" style={{ gap: 5, alignItems: "center" }}>
          <span style={{ width: 18, height: 0, borderTop: "2px dashed #c77b16", display: "inline-block" }} />
          知识点关联
        </span>
        <span>📄 = 关联论文数</span>
        <span>粗边框 = 难度：难</span>
        <span>悬停高亮邻居 · 点击知识点查看论文</span>
      </div>
    </div>
  );
}
