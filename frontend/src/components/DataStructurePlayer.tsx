/** 可复用的数据结构动画播放器：结构 + 重点知识点（排序/二叉树遍历）。 */

import { useEffect, useState, type ReactNode } from "react";

export interface DsFrame {
  note: string;
  values: number[];
  highlight?: number;
  highlightIndex?: number;
  highlightIndex2?: number;
  visited?: number[];
}

interface DsStructure {
  id: string;
  name: string;
  en: string;
  desc: string;
  frames?: DsFrame[];
  variants?: string[];
  framesFor?: (variant: string) => DsFrame[];
  render: (f: DsFrame) => ReactNode;
}

const STACK_FRAMES: DsFrame[] = [
  { note: "空栈", values: [] },
  { note: "push 3", values: [3], highlight: 3 },
  { note: "push 7", values: [3, 7], highlight: 7 },
  { note: "push 5", values: [3, 7, 5], highlight: 5 },
  { note: "pop → 弹出 5", values: [3, 7], highlight: 7 },
  { note: "push 2", values: [3, 7, 2], highlight: 2 },
  { note: "pop → 弹出 2", values: [3, 7], highlight: 7 },
];

const QUEUE_FRAMES: DsFrame[] = [
  { note: "空队列", values: [] },
  { note: "enqueue 4", values: [4], highlight: 4 },
  { note: "enqueue 8", values: [4, 8], highlight: 4 },
  { note: "enqueue 15", values: [4, 8, 15], highlight: 4 },
  { note: "dequeue → 出队 4", values: [8, 15], highlight: 8 },
  { note: "enqueue 16", values: [8, 15, 16], highlight: 8 },
  { note: "dequeue → 出队 8", values: [15, 16], highlight: 15 },
];

const LIST_FRAMES: DsFrame[] = [
  { note: "构建链表 10 → 20 → 30", values: [10, 20, 30] },
  { note: "遍历指针指向 10", values: [10, 20, 30], highlight: 10 },
  { note: "指针移到 20", values: [10, 20, 30], highlight: 20 },
  { note: "指针移到 30", values: [10, 20, 30], highlight: 30 },
  { note: "在 20 后插入 25", values: [10, 20, 25, 30], highlight: 25 },
  { note: "删除节点 20", values: [10, 25, 30], highlight: 25 },
];

const BST_FRAMES: DsFrame[] = [
  { note: "空树", values: [] },
  { note: "插入 50（根节点）", values: [50], highlight: 50 },
  { note: "插入 30", values: [50, 30], highlight: 30 },
  { note: "插入 70", values: [50, 30, 70], highlight: 70 },
  { note: "插入 20", values: [50, 30, 70, 20], highlight: 20 },
  { note: "插入 40", values: [50, 30, 70, 20, 40], highlight: 40 },
  { note: "查找 40", values: [50, 30, 70, 20, 40], highlight: 40 },
];

function NodeBadge({ value, active }: { value: number; active: boolean }) {
  return <span className={`ds-node ${active ? "active" : ""}`}>{value}</span>;
}

function renderStack(f: DsFrame): ReactNode {
  return (
    <div className="ds-stack">
      {[...f.values].reverse().map((v) => (
        <div key={v} className={`ds-stack-item ${f.highlight === v ? "active" : ""}`}>
          {v}
        </div>
      ))}
      {f.values.length === 0 && <div className="muted small">（空栈）</div>}
    </div>
  );
}

function renderQueue(f: DsFrame): ReactNode {
  return (
    <div className="ds-queue">
      {f.values.map((v) => (
        <div key={v} className={`ds-queue-item ${f.highlight === v ? "active" : ""}`}>
          {v}
        </div>
      ))}
      {f.values.length === 0 && <div className="muted small">（空队列）</div>}
    </div>
  );
}

function renderList(f: DsFrame): ReactNode {
  return (
    <div className="ds-list">
      {f.values.map((v, i) => (
        <div key={v} className="ds-list-cell">
          <NodeBadge value={v} active={f.highlight === v} />
          {i < f.values.length - 1 && <span className="ds-arrow">→</span>}
        </div>
      ))}
      {f.values.length === 0 && <div className="muted small">（空链表）</div>}
    </div>
  );
}

interface BstLayout {
  nodes: Array<{ value: number; x: number; y: number }>;
  edges: Array<[number, number]>;
  indexByValue: Map<number, number>;
}

function bstLayout(values: number[]): BstLayout {
  interface TNode {
    value: number;
    left: TNode | null;
    right: TNode | null;
  }
  let root: TNode | null = null;
  const insert = (n: TNode | null, value: number): TNode => {
    if (!n) return { value, left: null, right: null };
    if (value < n.value) n.left = insert(n.left, value);
    else n.right = insert(n.right, value);
    return n;
  };
  for (const v of values) root = insert(root, v);

  const nodes: BstLayout["nodes"] = [];
  const edges: BstLayout["edges"] = [];
  const indexByValue = new Map<number, number>();
  let col = 0;
  const walk = (n: TNode | null, depth: number): number => {
    if (!n) return -1;
    const leftIdx = walk(n.left, depth + 1);
    const idx = nodes.length;
    nodes.push({ value: n.value, x: col++, y: depth });
    indexByValue.set(n.value, idx);
    if (leftIdx >= 0) edges.push([idx, leftIdx]);
    const rightIdx = walk(n.right, depth + 1);
    if (rightIdx >= 0) edges.push([idx, rightIdx]);
    return idx;
  };
  walk(root, 0);
  return { nodes, edges, indexByValue };
}

function renderBst(f: DsFrame): ReactNode {
  if (f.values.length === 0) {
    return <div className="muted small">（空树）</div>;
  }
  const { nodes, edges, indexByValue } = bstLayout(f.values);
  const width = 80 + Math.max(1, nodes.length) * 64;
  const height = 60 + Math.max(...nodes.map((n) => n.y)) * 86 + 40;
  const px = (n: { x: number; y: number }) => ({ cx: 48 + n.x * 64, cy: 46 + n.y * 86 });
  const highlightIdx = f.highlight != null ? indexByValue.get(f.highlight) : undefined;
  return (
    <svg className="ds-bst" viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: "100%", height: "auto" }}>
      {edges.map(([a, b], i) => {
        const p1 = px(nodes[a]);
        const p2 = px(nodes[b]);
        return <line key={i} x1={p1.cx} y1={p1.cy} x2={p2.cx} y2={p2.cy} />;
      })}
      {nodes.map((n, i) => {
        const p = px(n);
        return (
          <g key={i} className={i === highlightIdx ? "ds-bst-active" : ""}>
            <circle cx={p.cx} cy={p.cy} r={21} />
            <text x={p.cx} y={p.cy + 5} textAnchor="middle">
              {n.value}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function renderSorting(f: DsFrame): ReactNode {
  const max = Math.max(...f.values, 1);
  return (
    <div className="study-array">
      {f.values.map((v, i) => {
        const active = i === f.highlightIndex || i === f.highlightIndex2;
        return (
          <div
            key={i}
            className={`study-bar ${active ? "active" : ""}`}
            style={{ height: `${Math.max(12, (v / max) * 140)}px` }}
          >
            <span>{v}</span>
          </div>
        );
      })}
    </div>
  );
}

const TREE_VALUES = [4, 2, 6, 1, 3, 5, 7];
const TRAVERSAL_ORDERS: Record<string, number[]> = {
  preorder: [4, 2, 1, 3, 6, 5, 7],
  inorder: [1, 2, 3, 4, 5, 6, 7],
  postorder: [1, 3, 2, 5, 7, 6, 4],
  level: [4, 2, 6, 1, 3, 5, 7],
};

const VARIANT_LABEL: Record<string, string> = {
  bubble: "冒泡",
  selection: "选择",
  insertion: "插入",
  preorder: "前序",
  inorder: "中序",
  postorder: "后序",
  level: "层次",
};

function renderTraversal(f: DsFrame): ReactNode {
  const { nodes, edges, indexByValue } = bstLayout(f.values);
  const width = 80 + Math.max(1, nodes.length) * 64;
  const height = 60 + Math.max(...nodes.map((n) => n.y)) * 86 + 40;
  const px = (n: { x: number; y: number }) => ({ cx: 48 + n.x * 64, cy: 46 + n.y * 86 });
  const visited = new Set(f.visited ?? []);
  const currentIdx = f.highlight != null ? indexByValue.get(f.highlight) : undefined;
  return (
    <div>
      <svg className="ds-bst" viewBox={`0 0 ${width} ${height}`} style={{ maxWidth: "100%", height: "auto" }}>
        {edges.map(([a, b], i) => {
          const p1 = px(nodes[a]);
          const p2 = px(nodes[b]);
          return <line key={i} x1={p1.cx} y1={p1.cy} x2={p2.cx} y2={p2.cy} />;
        })}
        {nodes.map((n, i) => {
          const p = px(n);
          const cls = i === currentIdx ? "ds-bst-active" : visited.has(n.value) ? "ds-bst-visited" : "";
          return (
            <g key={i} className={cls}>
              <circle cx={p.cx} cy={p.cy} r={21} />
              <text x={p.cx} y={p.cy + 5} textAnchor="middle">
                {n.value}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="row wrap mt-8" style={{ gap: 6 }}>
        <span className="small muted">访问顺序：</span>
        {(f.visited ?? []).map((v) => (
          <span key={v} className="badge">{v}</span>
        ))}
      </div>
    </div>
  );
}

function sortFrames(kind: string): DsFrame[] {
  const start = [5, 3, 8, 4, 2];
  const a = [...start];
  const frames: DsFrame[] = [{ note: "初始数组", values: [...a] }];

  if (kind === "bubble") {
    for (let i = 0; i < a.length - 1; i++) {
      for (let j = 0; j < a.length - 1 - i; j++) {
        frames.push({ note: `比较 ${a[j]} 与 ${a[j + 1]}`, values: [...a], highlightIndex: j, highlightIndex2: j + 1 });
        if (a[j] > a[j + 1]) {
          [a[j], a[j + 1]] = [a[j + 1], a[j]];
          frames.push({ note: `交换 ${a[j]} 与 ${a[j + 1]}`, values: [...a], highlightIndex: j, highlightIndex2: j + 1 });
        }
      }
    }
  } else if (kind === "selection") {
    for (let i = 0; i < a.length - 1; i++) {
      let min = i;
      for (let j = i + 1; j < a.length; j++) {
        frames.push({ note: `寻找最小值（当前 ${a[min]}）`, values: [...a], highlightIndex: j, highlightIndex2: min });
        if (a[j] < a[min]) min = j;
      }
      if (min !== i) {
        [a[i], a[min]] = [a[min], a[i]];
        frames.push({ note: `把最小值 ${a[i]} 放到位置 ${i}`, values: [...a], highlightIndex: i });
      }
    }
  } else {
    for (let i = 1; i < a.length; i++) {
      const key = a[i];
      let j = i - 1;
      frames.push({ note: `取出 ${key}`, values: [...a], highlightIndex: i });
      while (j >= 0 && a[j] > key) {
        a[j + 1] = a[j];
        frames.push({ note: `${a[j]} 后移`, values: [...a], highlightIndex: j + 1 });
        j--;
      }
      a[j + 1] = key;
      frames.push({ note: `插入 ${key}`, values: [...a], highlightIndex: j + 1 });
    }
  }

  frames.push({ note: "排序完成 ✅", values: [...a] });
  return frames;
}

function traversalFrames(order: string): DsFrame[] {
  const seq = TRAVERSAL_ORDERS[order] ?? TRAVERSAL_ORDERS.preorder;
  const frames: DsFrame[] = [{ note: `${VARIANT_LABEL[order] ?? order}遍历：按顺序访问节点`, values: TREE_VALUES, visited: [] }];
  const visited: number[] = [];
  for (const v of seq) {
    visited.push(v);
    frames.push({ note: `访问节点 ${v}`, values: TREE_VALUES, highlight: v, visited: [...visited] });
  }
  return frames;
}

export const DATA_STRUCTURES: DsStructure[] = [
  { id: "stack", name: "栈", en: "Stack", desc: "后进先出（LIFO），只在一端进出。", frames: STACK_FRAMES, render: renderStack },
  { id: "queue", name: "队列", en: "Queue", desc: "先进先出（FIFO），一端进另一端出。", frames: QUEUE_FRAMES, render: renderQueue },
  { id: "list", name: "链表", en: "Linked List", desc: "节点 + 指针串联，可灵活插入删除。", frames: LIST_FRAMES, render: renderList },
  { id: "bst", name: "二叉搜索树", en: "BST", desc: "左小右大，查找/插入沿树逐层下探。", frames: BST_FRAMES, render: renderBst },
  {
    id: "sorting",
    name: "排序算法",
    en: "Sorting",
    desc: "通过比较与交换，把无序数组排成有序序列。",
    variants: ["bubble", "selection", "insertion"],
    framesFor: sortFrames,
    render: renderSorting,
  },
  {
    id: "traversal",
    name: "二叉树遍历",
    en: "Tree Traversal",
    desc: "前序 / 中序 / 后序 / 层次遍历的访问顺序。",
    variants: ["preorder", "inorder", "postorder", "level"],
    framesFor: traversalFrames,
    render: renderTraversal,
  },
];

export function DataStructurePlayer({
  kind,
  initialVariant,
}: {
  kind: string;
  initialVariant?: string;
}) {
  const structure = DATA_STRUCTURES.find((s) => s.id === kind) ?? DATA_STRUCTURES[0];
  const [variant, setVariant] = useState(
    initialVariant && structure.variants?.includes(initialVariant)
      ? initialVariant
      : structure.variants?.[0] ?? ""
  );
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying] = useState(false);

  const frames = structure.framesFor ? structure.framesFor(variant) : structure.frames ?? [];
  const frame = frames[Math.min(frameIdx, frames.length - 1)] ?? frames[0];
  const max = frames.length - 1;

  useEffect(() => {
    if (structure.variants && !structure.variants.includes(variant)) {
      setVariant(structure.variants[0]);
    }
  }, [structure.id, variant]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => setFrameIdx((i) => Math.min(max, i + 1)), 950);
    return () => window.clearInterval(timer);
  }, [playing, max]);

  return (
    <div>
      {structure.variants?.length ? (
        <div className="row wrap" style={{ gap: 6, marginBottom: 12 }}>
          {structure.variants.map((v) => (
            <button
              key={v}
              className={`btn btn-sm ${variant === v ? "btn-primary" : ""}`}
              onClick={() => {
                setVariant(v);
                setFrameIdx(0);
                setPlaying(false);
              }}
            >
              {VARIANT_LABEL[v] ?? v}
            </button>
          ))}
        </div>
      ) : null}
      <div className="ds-canvas" key={`${structure.id}-${variant}-${Math.min(frameIdx, max)}`}>
        {structure.render(frame)}
      </div>
      <div className="ds-note">↳ {frame.note}</div>
      <div className="row mt-8" style={{ justifyContent: "center", gap: 6 }}>
        <button className="btn btn-sm" onClick={() => setFrameIdx((i) => Math.max(0, i - 1))} disabled={frameIdx === 0}>← 上一步</button>
        <button className="btn btn-sm btn-primary" onClick={() => setPlaying((p) => !p)}>{playing ? "暂停" : "播放"}</button>
        <button className="btn btn-sm" onClick={() => setFrameIdx((i) => i + 1)} disabled={frameIdx >= max}>下一步 →</button>
        <button className="btn btn-sm" onClick={() => { setFrameIdx(0); setPlaying(false); }}>⟲ 重置</button>
      </div>
    </div>
  );
}
