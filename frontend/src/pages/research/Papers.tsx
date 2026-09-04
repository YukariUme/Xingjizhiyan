/** 论文阅读：列表 + AI 结构化阅读（含引用来源与知识点）。 */

import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../../api";
import { Card, EmptyState, ErrorBanner, Loading, Modal, RichText, useAsync } from "../../components/ui";
import { AiLabel } from "../../components/AiMeta";
import type { Paper, PaperAnalysis } from "../../types";

export default function ResearchPapers() {
  const [params] = useSearchParams();
  const preset = params.get("paper");
  const papers = useAsync<Paper[]>(() => api.get("/research/papers"));
  const [q, setQ] = useState("");
  const [active, setActive] = useState<number | null>(preset ? Number(preset) : null);
  const [analysis, setAnalysis] = useState<PaperAnalysis | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [detail, setDetail] = useState<Paper | null>(null);
  const [tab, setTab] = useState<"ai" | "text">("ai");

  const openPaper = async (p: Paper, initialTab: "ai" | "text" = "ai") => {
    setActive(p.id);
    setTab(initialTab);
    setDetail(p);
    setAnalysis(null);
    setLoadingAnalysis(true);
    try {
      // 拉取论文原文（content / knowledge_point_ids）
      api.get<Paper>(`/research/papers/${p.id}`).then(setDetail).catch(() => undefined);
      const res = await api.post<PaperAnalysis>(`/research/papers/${p.id}/analyze`, {});
      setAnalysis(res);
    } catch {
      /* 忽略 */
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const setStatus = async (status: string) => {
    if (!active) return;
    await api.post(`/research/papers/${active}/reading`, { status });
    papers.refresh();
  };

  const exportAnalysis = () => {
    if (!analysis) return;
    const refs = analysis.references.map((r) => `- [${r.source_level ?? "S"}] ${r.title}（${r.source}）`).join("\n");
    const md = [
      `# ${detail?.title ?? analysis.title}`,
      "",
      "## 摘要",
      analysis.summary,
      "",
      "## 研究问题",
      analysis.research_question,
      "",
      "## 方法",
      analysis.method,
      "",
      "## 实验",
      typeof analysis.experiments === "string" ? analysis.experiments : JSON.stringify(analysis.experiments, null, 2),
      "",
      "## 结论",
      analysis.conclusion,
      "",
      "## 局限",
      analysis.limitations,
      "",
      "## 可进一步研究的问题",
      analysis.future,
      "",
      "## 引用来源",
      refs || "（无）",
      "",
    ].join("\n");
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "论文阅读笔记.md";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const list = q.trim() ? papers.data?.filter((p) => `${p.title} ${p.abstract} ${p.topics.join(" ")}`.toLowerCase().includes(q.toLowerCase())) : papers.data;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>论文阅读助手</h1>
          <p>选择论文，AI 自动拆解摘要、问题、方法、实验、结论、局限与延伸，并标注引用来源</p>
        </div>
        <input className="input" style={{ width: 240 }} placeholder="搜索论文…" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      {papers.error ? (
        <ErrorBanner message={papers.error} />
      ) : papers.loading ? (
        <Loading />
      ) : !list || list.length === 0 ? (
        <EmptyState text="暂无论文" />
      ) : (
        <div className="grid grid-2">
          {list.map((p) => (
            <Card key={p.id} title={p.title} extra={p.is_hot ? <span className="badge orange">热点</span> : undefined}>
              <p className="small muted">{p.abstract.slice(0, 120)}…</p>
              <div className="row wrap mb-8">
                <span className="badge gray">{p.venue} · {p.year}</span>
                <span className="badge gray">被引 {p.citations}</span>
                {p.status && <span className="badge purple">{{ reading: "阅读中", read: "已读", favorite: "已收藏" }[p.status] ?? p.status}</span>}
              </div>
              <div className="row space-between">
                <div className="small muted">{(p.authors || []).slice(0, 3).join(", ")}</div>
                <div className="row">
                  <button className="btn btn-sm" onClick={() => void openPaper(p, "text")}>原文</button>
                  <button className="btn btn-sm btn-primary" onClick={() => void openPaper(p, "ai")}>AI 阅读</button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        title={detail?.title ?? "论文阅读"}
        open={active != null}
        onClose={() => setActive(null)}
        footer={
          <div className="row">
            {active != null && (
              <>
                <button className="btn btn-sm" onClick={() => void setStatus("reading")}>标记阅读中</button>
                <button className="btn btn-sm" onClick={() => void setStatus("favorite")}>★ 收藏</button>
                <button className="btn btn-sm" onClick={() => void setStatus("read")}>标记已读</button>
                <button className="btn btn-sm" onClick={exportAnalysis}>⬇ 导出</button>
              </>
            )}
          </div>
        }
      >
        <div className="row mb-16" style={{ gap: 8 }}>
          <button
            className={`btn btn-sm ${tab === "ai" ? "btn-primary" : ""}`}
            onClick={() => setTab("ai")}
          >
            AI 阅读
          </button>
          <button
            className={`btn btn-sm ${tab === "text" ? "btn-primary" : ""}`}
            onClick={() => setTab("text")}
          >
            原文
          </button>
        </div>
        {tab === "text" ? (
          <div className="grid" style={{ maxHeight: "66vh", overflowY: "auto", paddingRight: 4 }}>
            <div>
              <div className="small muted">
                {(detail?.authors || []).join(", ")}
                <span className="badge gray" style={{ marginLeft: 8 }}>{detail?.venue} · {detail?.year}</span>
                <span className="badge gray" style={{ marginLeft: 6 }}>被引 {detail?.citations}</span>
              </div>
              {detail?.topics?.length ? (
                <div className="row wrap mt-8">
                  {detail.topics.map((t) => <span key={t} className="badge">{t}</span>)}
                </div>
              ) : null}
              <h3 className="mt-16">摘要</h3>
              <p className="small">{detail?.abstract}</p>
              <h3 className="mt-16">原文</h3>
              {detail?.content?.trim() ? (
                <div
                  className="small"
                  style={{
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    background: "var(--card-deep)",
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    padding: "12px 14px",
                    lineHeight: 1.8,
                  }}
                >
                  {detail.content}
                </div>
              ) : (
                <EmptyState text="该论文暂无全文内容，可在科研工作台上传 PDF 后阅读" />
              )}
            </div>
          </div>
        ) : loadingAnalysis ? (
          <div className="center"><span className="spinner" /> AI 正在阅读论文…</div>
        ) : analysis ? (
          <div className="grid" style={{ maxHeight: "66vh", overflowY: "auto", paddingRight: 4 }}>
            <div>
              <AiLabel provider={analysis.provider} />
              <span className="badge gray">{detail?.venue} · {detail?.year}</span>
              <h3 className="mt-8">摘要</h3>
              <RichText content={analysis.summary} />
            </div>
            <Section title="研究问题" content={analysis.research_question} />
            <Section title="方法" content={analysis.method} />
            <Section title="实验" content={analysis.experiments} />
            <Section title="结论" content={analysis.conclusion} />
            <Section title="局限性" content={analysis.limitations} />
            <Section title="可进一步研究的问题" content={analysis.future} />
            {analysis.knowledge_points.length > 0 && (
              <div>
                <h3>涉及知识点（可跳转知识库）</h3>
                <div className="row wrap">
                  {analysis.knowledge_points.map((k) => <span key={k} className="badge">{k}</span>)}
                </div>
              </div>
            )}
            {analysis.references.length > 0 && (
              <div>
                <h3>引用来源</h3>
                {analysis.references.map((r, i) => (
                  <div key={i} className="small" style={{ padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
                    <b>{r.title}</b>
                    <div className="muted">{r.source} · {r.course} · {r.chapter}</div>
                    <div className="muted">{r.snippet}</div>
                    {r.course && (
                      <Link to={`/search?q=${encodeURIComponent(r.course)}`} className="btn btn-sm mt-8">
                        回到课程知识
                      </Link>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <EmptyState text="分析失败，请重试" />
        )}
      </Modal>
    </div>
  );
}

function Section({ title, content }: { title: string; content: unknown }) {
  if (!content) return null;
  return (
    <div>
      <h3>{title}</h3>
      <RichText content={content} />
    </div>
  );
}
