/** 工作流中心：定义启动、执行可视化、运行记录。 */

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { WorkflowSteps } from "../components/WorkflowSteps";
import { Card, EmptyState, ErrorBanner, Loading, useAsync } from "../components/ui";
import type { WorkflowDef, WorkflowRun } from "../types";

const FIELDS: Record<string, Array<{ key: string; label: string; placeholder?: string }>> = {
  lesson_plan: [
    { key: "course", label: "课程", placeholder: "数据结构" },
    { key: "chapter", label: "章节", placeholder: "第 4 章 树" },
    { key: "topic", label: "教学主题", placeholder: "二叉树遍历" },
    { key: "grade", label: "学生年级", placeholder: "大二" },
    { key: "objective", label: "教学目标（可选）", placeholder: "掌握三种遍历方式" },
  ],
  research_review: [{ key: "topic", label: "研究主题", placeholder: "RAG / 代码大模型 / 智能教学" }],
};

export default function Workflows() {
  const [params] = useSearchParams();
  const { user } = useAuth();
  const defs = useAsync<WorkflowDef[]>(() => api.get("/workflows"));
  const runs = useAsync<WorkflowRun[]>(() => api.get("/workflows/runs?limit=20"));
  const presetRun = params.get("run");
  const [activeDef, setActiveDef] = useState<string | null>(null);
  const [payload, setPayload] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [current, setCurrent] = useState<WorkflowRun | null>(null);
  const [viewed, setViewed] = useState<WorkflowRun | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (presetRun) {
      api
        .get<WorkflowRun>(`/workflows/runs/${presetRun}`)
        .then((run) => {
          setViewed(run);
          setCurrent(run);
        })
        .catch(() => undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presetRun]);

  const pickDef = (id: string) => {
    setActiveDef(id);
    setPayload({});
    setErr("");
  };

  const launch = async () => {
    if (!activeDef) return;
    setBusy(true);
    setErr("");
    try {
      const run = await api.post<WorkflowRun>(`/workflows/${activeDef}/run`, payload);
      setCurrent(run);
      setViewed(run);
      runs.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "运行失败");
    } finally {
      setBusy(false);
    }
  };

  const loadRun = async (id: number) => {
    const run = await api.get<WorkflowRun>(`/workflows/runs/${id}`);
    setViewed(run);
    setCurrent(run);
  };

  if (defs.loading) return <Loading />;
  if (defs.error) return <ErrorBanner message={defs.error} />;
  const definition = defs.data?.find((d) => d.id === activeDef);
  const shown = viewed ?? current;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>工作流中心</h1>
          <p>多步骤 + 条件分支 + 人工审批的智能编排，每步输入输出留痕，全程可追溯</p>
        </div>
      </div>

      <div className="grid grid-3 mb-16">
        {defs.data?.map((d) => (
          <Card key={d.id} title={d.name} extra={<span className={`badge ${activeDef === d.id ? "green" : "gray"}`}>{d.steps.length} 步</span>}>
            <p className="small muted" style={{ minHeight: 44 }}>{d.description}</p>
            <div className="row wrap mb-8">
              {d.steps.map((s) => (
                <span key={s.id} className="tag">
                  {s.type === "branch" ? "分支" : s.type === "approval" ? "人工审批" : s.tool.split(".")[1]}
                </span>
              ))}
            </div>
            <button className="btn btn-sm btn-primary" onClick={() => pickDef(d.id)}>
              {activeDef === d.id ? "已选择" : "选择并运行"}
            </button>
          </Card>
        ))}
      </div>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div>
          {definition && (
            <Card title={`启动：${definition.name}`}>
              {definition.id === "assignment_loop" ? (
                <p className="small muted">
                  该工作流由学生提交作业自动触发（编程题自动评测 / 简答题 AI 建议 + 教师审批），
                  无需手动启动；可在下方运行记录中查看。
                </p>
              ) : (
                (FIELDS[definition.id] ?? []).map((f) => (
                  <div className="field" key={f.key}>
                    <label>{f.label}</label>
                    <input className="input" placeholder={f.placeholder} value={payload[f.key] ?? ""}
                      onChange={(e) => setPayload({ ...payload, [f.key]: e.target.value })} />
                  </div>
                ))
              )}
              {definition.id !== "assignment_loop" && (
                <button className="btn btn-primary" onClick={() => void launch()} disabled={busy}>
                  {busy ? "执行中…" : "▶ 运行工作流"}
                </button>
              )}
              {err && <div className="badge red mt-8">{err}</div>}
            </Card>
          )}

          <Card title="运行记录" className="mt-16">
            {runs.loading ? (
              <Loading />
            ) : !runs.data || runs.data.length === 0 ? (
              <EmptyState text="还没有工作流运行记录" />
            ) : (
              <div>
                {runs.data.slice(0, 10).map((r) => (
                  <div key={r.id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)", cursor: "pointer" }}
                    onClick={() => void loadRun(r.id)}>
                    <div className="grow">
                      <b>#{r.id} {r.name}</b>
                      <div className="small muted">
                        {new Date(r.created_at).toLocaleString("zh-CN")} · {String(r.input.topic ?? r.input.title ?? "")}
                      </div>
                    </div>
                    <span className={`badge ${r.status === "success" ? "green" : r.status === "failed" ? "red" : r.status === "awaiting_approval" ? "orange" : ""}`}>
                      {{ success: "成功", failed: "失败", awaiting_approval: "待审批", running: "执行中" }[r.status] ?? r.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div>
          {shown ? (
            <Card
              title={`执行记录 #${shown.id} · ${shown.name}`}
              extra={
                <span className={`badge ${shown.status === "success" ? "green" : shown.status === "failed" ? "red" : shown.status === "awaiting_approval" ? "orange" : ""}`}>
                  {{ success: "已完成", failed: "失败", awaiting_approval: "等待教师确认", running: "执行中" }[shown.status] ?? shown.status}
                </span>
              }
            >
              <div className="small muted mb-16">
                发起时间 {new Date(shown.created_at).toLocaleString("zh-CN")} ·{" "}
                {user ? `${user.display_name}（${user.role === "teacher" ? "教师" : user.role === "student" ? "学生" : "科研"}）` : ""}
              </div>
              <WorkflowSteps run={shown} />
            </Card>
          ) : (
            <Card>
              <div className="empty">
                <div className="emoji">⚙️</div>
                <div>选择左侧工作流启动，或点击运行记录查看执行过程</div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
