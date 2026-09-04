/** 全局搜索：RAG 检索知识库，展示切片与来源。 */

import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Card, EmptyState, Loading, useAsync } from "../components/ui";
import type { SearchResult } from "../types";

export default function SearchPage() {
  const [params] = useSearchParams();
  const q = params.get("q") ?? "";
  const { data, loading } = useAsync<SearchResult[]>(
    () => api.get(`/knowledge/search?q=${encodeURIComponent(q)}&top_k=8`),
    [q]
  );

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>全局知识检索</h1>
          <p>基于知识库 RAG 检索，结果为「{q}」相关切片（含来源与相似度）</p>
        </div>
      </div>
      {loading ? (
        <Loading />
      ) : !data || data.length === 0 ? (
        <EmptyState text="未检索到相关内容" />
      ) : (
        <div className="grid">
          {data.map((r, i) => (
            <Card key={i} title={`${i + 1}. ${r.document.title}`}>
              <div className="row wrap mb-8">
                <span className="badge">{r.document.course}</span>
                <span className="badge purple">{r.document.topic}</span>
                <span className="badge gray">{r.document.chapter}</span>
                <span className="badge gray">相似度 {(r.score * 100).toFixed(1)}%</span>
              </div>
              <p className="small" style={{ color: "var(--text-2)", margin: 0 }}>
                {r.chunk.text}
              </p>
              <div className="small muted mt-8">来源：{r.document.source || "平台知识库"}</div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

