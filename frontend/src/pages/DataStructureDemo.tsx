/** 数据结构动画演示页：结构 + 重点知识点（排序/二叉树遍历）。 */

import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Card } from "../components/ui";
import { DataStructurePlayer, DATA_STRUCTURES } from "../components/DataStructurePlayer";

export default function DataStructureDemo() {
  const [params] = useSearchParams();
  const initialId = params.get("ds") ?? "stack";
  const initialIdx = (() => {
    const i = DATA_STRUCTURES.findIndex((s) => s.id === initialId);
    return i >= 0 ? i : 0;
  })();
  const [activeIdx, setActiveIdx] = useState(initialIdx);
  const active = DATA_STRUCTURES[activeIdx];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>数据结构动画演示</h1>
          <p>结构 + 重点知识点：栈、队列、链表、二叉搜索树、排序算法、二叉树遍历。</p>
        </div>
      </div>

      <div className="row wrap" style={{ gap: 6, marginBottom: 16 }}>
        {DATA_STRUCTURES.map((s, i) => (
          <button key={s.id} className={`btn btn-sm ${i === activeIdx ? "btn-primary" : ""}`} onClick={() => setActiveIdx(i)}>
            {s.name}（{s.en}）
          </button>
        ))}
      </div>

      <Card title={`${active.name} · ${active.en}`} extra={<span className="badge">{active.desc}</span>}>
        <DataStructurePlayer key={active.id} kind={active.id} />
      </Card>
    </div>
  );
}
