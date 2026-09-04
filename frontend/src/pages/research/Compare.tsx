/** 论文对比：选择多篇论文，AI 生成研究问题/方法/数据/指标/结果/局限的结构化对比表。 */

import { useState } from "react";
import { api } from "../../api";
import { Card, Loading, toDisplayText, useAsync } from "../../components/ui";
import { AiLabel } from "../../components/AiMeta";
import type { Paper } from "../../types";

export default function ResearchCompare() {
  const papers = useAsync<Paper[]>(() => api.get("/research/papers"));
  const [selected, setSelected] = useState<number[]>([]);
  const [rows, setRows] = useState<Array<{ dimension: string; cells: string[] }>>([]);
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const toggle = (id: number) =>
    setSelected((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));

  const compare = async () => {
    if (selected.length < 2) {
      setErr("请至少选择 2 篇论文");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const res = await api.post<{ rows: typeof rows; summary: string }>("/research/compare", {
        paper_ids: selected,
      });
      setRows(res.rows);
      setSummary(res.summary);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "对比失败");
    } finally {
      setBusy(false);
    }
  };

  const exportMarkdown = () => {
    if (rows.length === 0) return;
    const lines = ["# 论文对比", ""];
    rows.forEach((r) => {
      lines.push(`## ${r.dimension}`, "");
      r.cells.forEach((c, i) => lines.push(`- 论文${i + 1}：${c}`));
      lines.push("");
    });
    if (summary) lines.push("## 总结", "", summary, "");
    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "论文对比.md";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (papers.loading) return <Loading />;
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>论文对比</h1>
          <p>选择 2~5 篇论文，AI 输出研究问题 / 方法 / 数据集 / 指标 / 结果 / 局限性的结构化对比</p>
        </div>
        <div className="row">
          <button className="btn" onClick={exportMarkdown} disabled={rows.length === 0}>⬇ 导出</button>
          <button className="btn btn-primary" onClick={() => void compare()} disabled={busy}>
            {busy ? "对比中…" : "开始对比"}
          </button>
        </div>
      </div>
      {err && <div className="badge red mb-16">{err}</div>}

      <Card className="mb-16">
        <div className="grid grid-2">
          {(papers.data ?? []).map((p) => (
            <div key={p.id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", cursor: "pointer" }} onClick={() => toggle(p.id)}>
              <div className="grow">
                <b className="small">{p.title}</b>
                <div className="small muted">{p.venue} · {p.year}</div>
              </div>
              <input type="checkbox" readOnly checked={selected.includes(p.id)} />
            </div>
          ))}
        </div>
      </Card>

      {rows.length > 0 && (
        <Card title="对比结果">
          <AiLabel provider="deepseek" />
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>维度</th>
                  {selected.map((id, i) => (
                    <th key={id}>论文 {i + 1}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td><b>{r.dimension}</b></td>
                    {r.cells.map((c, j) => <td key={j} className="small">{toDisplayText(c)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {summary && <p className="small mt-16">{summary}</p>}
        </Card>
      )}
    </div>
  );
}
