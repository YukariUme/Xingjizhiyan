/** 科研工作台：研究方向、最近论文、推荐与收藏。 */

import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { Card, EmptyState, ErrorBanner, Loading, Modal, useAsync } from "../../components/ui";
import type { Workbench } from "../../types";

export default function ResearchWorkbench() {
  const wb = useAsync<Workbench>(() => api.get("/research/workbench"));
  const docs = useAsync<Array<{ id: number; title: string; source: string; created_at: string }>>(() => api.get("/research/documents"));
  const profile = useAsync<{
    reading_count: number;
    favorite_count: number;
    top_venues: Array<[string, number]>;
    recommended_papers: Array<{ id: number; title: string; year: number; venue: string }>;
  }>(() => api.get("/research/profile"));
  const [open, setOpen] = useState(false);
  const [docOpen, setDocOpen] = useState(false);
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docTitle, setDocTitle] = useState("");
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");

  const addTopic = async () => {
    if (!name.trim()) return;
    await api.post("/research/topics", { name, description: desc });
    setOpen(false);
    setName("");
    setDesc("");
    wb.refresh();
  };

  const uploadDoc = async () => {
    if (!docFile) return;
    const fd = new FormData();
    fd.append("file", docFile);
    fd.append("title", docTitle || docFile.name);
    try {
      await api.upload("/research/documents/upload", fd);
      setDocOpen(false);
      setDocFile(null);
      setDocTitle("");
      docs.refresh();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "上传失败");
    }
  };

  if (wb.loading) return <Loading />;
  if (wb.error) return <ErrorBanner message={wb.error} />;
  const d = wb.data;
  if (!d) return <EmptyState text="暂无数据" />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>科研工作台</h1>
          <p>论文阅读记录、推荐与收藏；数据仅自己可见</p>
        </div>
        <button className="btn btn-primary" onClick={() => setOpen(true)}>＋ 研究方向</button>
      </div>

      <div className="grid grid-3 mb-16">
        {d.topics.map((t) => (
          <Card key={t.id} title={t.name}>
            <p className="small muted">{t.description || "暂无描述"}</p>
          </Card>
        ))}
        {d.topics.length === 0 && (
          <Card title="我的研究方向">
            <div className="muted small">点击右上角添加研究方向</div>
          </Card>
        )}
      </div>

      {profile.data && (
        <div className="grid grid-4 mb-16">
          <Card>
            <div className="stat-card">
              <div className="stat-label">研究方向画像</div>
              <div className="stat-value">{profile.data.reading_count}</div>
              <div className="stat-hint">已读论文</div>
            </div>
          </Card>
          <Card>
            <div className="stat-card">
              <div className="stat-label">收藏</div>
              <div className="stat-value">{profile.data.favorite_count}</div>
            </div>
          </Card>
          <Card>
            <div className="stat-card">
              <div className="stat-label">关注期刊</div>
              <div className="stat-value" style={{ fontSize: 17 }}>
                {profile.data.top_venues.slice(0, 2).map(([v, n]) => (
                  <div key={v}>{v} × {n}</div>
                )) || "—"}
              </div>
            </div>
          </Card>
          <Card title="推荐继续阅读" extra={<Link to="/research/papers" className="btn btn-sm">论文库</Link>}>
            {(profile.data.recommended_papers || []).slice(0, 3).map((p) => (
              <div key={p.id} className="small" style={{ padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
                <b>{p.title.slice(0, 30)}</b>
                <div className="muted">{p.venue} · {p.year}</div>
              </div>
            ))}
          </Card>
        </div>
      )}

      <Card
        className="mb-16"
        title={`我的科研资料（${docs.data?.length ?? 0}）`}
        extra={<button className="btn btn-sm btn-primary" onClick={() => setDocOpen(true)}>⬆ 上传资料</button>}
      >
        {docs.data?.length ? (
          docs.data.map((d) => (
            <div key={d.id} className="row space-between" style={{ padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
              <div className="grow">
                <b className="small">{d.title}</b>
                <div className="small muted">{d.source} · {new Date(d.created_at).toLocaleDateString("zh-CN")}</div>
              </div>
              <span className="badge purple">私有</span>
            </div>
          ))
        ) : (
          <div className="muted small">暂无科研资料，上传论文 PDF 后可进入个人研究资料库</div>
        )}
      </Card>

      <div className="grid grid-2">
        <Card title="最近阅读" extra={<Link to="/research/papers" className="btn btn-sm">论文库</Link>}>
          {d.recent_papers.length === 0 ? (
            <EmptyState text="暂无阅读记录" />
          ) : (
            d.recent_papers.map((p) => (
              <div key={p.id} className="row space-between" style={{ padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
                <div className="grow">
                  <b>{p.title}</b>
                  <div className="small muted">{p.venue} · {p.year} · 进度 {p.progress}%</div>
                </div>
                <Link to={`/research/papers?paper=${p.id}`} className="btn btn-sm">阅读</Link>
              </div>
            ))
          )}
        </Card>
        <Card title="收藏论文">
          {d.favorite_papers.length === 0 ? (
            <EmptyState text="暂无收藏" />
          ) : (
            d.favorite_papers.map((p) => (
              <div key={p.id} className="row space-between" style={{ padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
                <span className="grow small"><b>{p.title}</b></span>
                <Link to={`/research/papers?paper=${p.id}`} className="btn btn-sm">打开</Link>
              </div>
            ))
          )}
        </Card>
      </div>

      <div className="mt-16">
        <Card title="推荐论文（热点）" extra={<Link to="/research/explore" className="btn btn-sm">前沿探索</Link>}>
          <div className="grid grid-2">
            {d.recommended_papers.map((p) => (
              <div key={p.id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <div className="grow">
                  <b className="small">{p.title}</b>
                  <div className="small muted">{p.venue} · {p.year} · 被引 {p.citations}</div>
                </div>
                <span className="badge orange">热点</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Modal
        title="添加研究方向"
        open={open}
        onClose={() => setOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={() => void addTopic()} disabled={!name.trim()}>保存</button>
          </>
        }
      >
        <div className="field">
          <label>方向名称 *</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="如：检索增强生成" />
        </div>
        <div className="field">
          <label>描述</label>
          <textarea className="textarea" value={desc} onChange={(e) => setDesc(e.target.value)} />
        </div>
      </Modal>

      <Modal
        title="上传科研资料"
        open={docOpen}
        onClose={() => setDocOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setDocOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={() => void uploadDoc()} disabled={!docFile}>上传</button>
          </>
        }
      >
        <div className="field">
          <label>选择文件（pdf / txt / md / epub）</label>
          <input
            type="file"
            accept=".txt,.md,.markdown,.pdf,.epub,.ppt,.pptx,.doc,.docx"
            className="input"
            onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <div className="field">
          <label>标题（留空使用文件名）</label>
          <input className="input" value={docTitle} onChange={(e) => setDocTitle(e.target.value)} />
        </div>
        <p className="small muted">默认仅自己可见（个人私有资料，不影响其他用户）。</p>
      </Modal>
    </div>
  );
}
