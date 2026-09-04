/** 科研前沿热点：多元方向按钮 + 代表论文（会议/期刊 + arXiv 实时更新，<5s 返回）。 */

import { useEffect, useState } from "react";
import { api } from "../../api";
import { Card, Loading } from "../../components/ui";
import type { HotspotData, HotspotDirection, HotspotPaper } from "../../types";

const FETCH_TIMEOUT_MS = 5000;

export default function ResearchExplore() {
  const [directions, setDirections] = useState<HotspotDirection[]>([]);
  const [current, setCurrent] = useState("");
  const [data, setData] = useState<HotspotData | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [err, setErr] = useState("");

  // 方向列表（内置静态数据，秒回）
  useEffect(() => {
    let alive = true;
    api
      .get<HotspotDirection[]>("/research/hotspots/directions")
      .then((ds) => {
        if (!alive || ds.length === 0) return;
        setDirections(ds);
        setCurrent((c) => c || ds[0].id);
      })
      .catch((e) => alive && setErr(e instanceof Error ? e.message : "方向加载失败"));
    return () => {
      alive = false;
    };
  }, []);

  const load = async (directionId: string, silent = false) => {
    if (!directionId) return;
    setCurrent(directionId);
    setErr("");
    if (!silent) setLoading(true);
    else setRefreshing(true);
    const timer = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("请求超时（>5s），已显示本地精选论文。")), FETCH_TIMEOUT_MS)
    );
    try {
      const res = await Promise.race([
        api.get<HotspotData>(`/research/hotspots?direction=${encodeURIComponent(directionId)}`),
        timer,
      ]);
      setData(res);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "热点加载失败");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (current) void load(current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current]);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>科研前沿热点</h1>
          <p>选择方向，查看最新研究热点与国际会议/期刊代表论文；热点数据定时从 arXiv 自动刷新</p>
        </div>
      </div>

      <Card className="mb-16">
        <div className="row wrap" style={{ gap: 8 }}>
          {directions.map((d) => (
            <button
              key={d.id}
              className={`btn btn-sm ${d.id === current ? "btn-primary" : ""}`}
              onClick={() => void load(d.id)}
            >
              {d.label}
            </button>
          ))}
          {directions.length === 0 && <span className="muted small">方向加载中…</span>}
        </div>
        {err && <div className="badge red mt-8">{err}</div>}
      </Card>

      {loading && !data ? (
        <Loading text="正在加载热点论文…" />
      ) : data ? (
        <>
          <Card className="mb-16" title={data.direction.name}>
            <p className="small" style={{ color: "var(--text-2)" }}>
              {data.direction.description}
            </p>
            <div className="row wrap mt-8" style={{ gap: 6 }}>
              {data.direction.venues.map((v) => (
                <span key={v} className="badge purple">{v}</span>
              ))}
              <span className="badge gray">数据更新于 {data.updated_at}</span>
              <span className="badge gray">每 {data.refresh_hours} 小时自动刷新</span>
              <button className="btn btn-sm" disabled={refreshing} onClick={() => void load(current, true)}>
                {refreshing ? "刷新中…" : "⟳ 立即刷新"}
              </button>
            </div>
          </Card>

          <div className="grid grid-2">
            {data.papers.map((p, i) => (
              <PaperCard key={i} paper={p} />
            ))}
          </div>

          <p className="small muted mt-16" style={{ textAlign: "center" }}>
            来源：arXiv 最新提交（API 实时拉取）+ 精选国际会议/期刊代表论文。
            点击论文卡片可在 arXiv / 会议官网 / 出版社网站查看原文。
          </p>
        </>
      ) : (
        <Card>
          <div className="empty">
            <div className="emoji">🔭</div>
            <div>选择一个研究方向，追踪最新科研热点</div>
          </div>
        </Card>
      )}
    </div>
  );
}

function PaperCard({ paper }: { paper: HotspotPaper }) {
  const link = paper.url || "https://arxiv.org";
  return (
    <Card>
      <a
        href={link}
        target="_blank"
        rel="noopener noreferrer"
        style={{ textDecoration: "none", color: "inherit" }}
      >
        <div className="row space-between" style={{ gap: 8 }}>
          <span className={`badge ${paper.source === "arxiv" ? "green" : "purple"}`}>{paper.tag}</span>
          {paper.year > 0 && <span className="badge gray">{paper.year}</span>}
        </div>
        <h3 className="mt-8" style={{ fontSize: 15, lineHeight: 1.45 }}>
          {paper.title}
        </h3>
        <div className="small muted" style={{ marginTop: 6 }}>
          {paper.authors.length > 0 ? paper.authors.join(" · ") : "—"}
        </div>
        <div className="small mt-8" style={{ color: "var(--primary)" }}>
          {paper.venue} · 查看论文 ↗
        </div>
        {paper.summary && (
          <p className="small mt-8" style={{ color: "var(--text-2)", marginBottom: 0 }}>
            {paper.summary}
          </p>
        )}
      </a>
    </Card>
  );
}
