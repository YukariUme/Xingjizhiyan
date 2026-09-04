/** 学习中心：我的个人学习控制台（画像 / 今日任务 / 个性化计划 / 薄弱点 / 记录）。 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { BarChart } from "../../components/charts";
import { Card, EmptyState, Loading, Progress, useAsync } from "../../components/ui";
import type { StudentProfile } from "../../types";

type Task = {
  id: number;
  title: string;
  reason: string;
  task_type: string;
  course_id: number | null;
  knowledge_point_id: number | null;
  due_at: string | null;
  status: string;
};

type Plan = { id: number; title: string; reason: string; content: Array<{ order: number; title: string; detail: string }> };

type LearningCourse = { id: number; name: string; progress: number; mastery: number; pending_tasks: number };

export default function StudentLearning() {
  const navigate = useNavigate();
  const [examDate, setExamDate] = useState("");
  const profile = useAsync<StudentProfile>(() => api.get("/analytics/me"));
  const courses = useAsync<LearningCourse[]>(() => api.get("/curriculum/courses"));
  const tasks = useAsync<Task[]>(() => api.get("/curriculum/tasks"));
  const plan = useAsync<Plan>(() => api.get("/curriculum/plan"));
  const wrongbook = useAsync<{
    total_wrong: number;
    by_knowledge_point: Array<{ knowledge_point_id: number; name: string; count: number; qtypes: string[] }>;
    samples: Array<{ title: string; analysis: string }>;
  }>(() => api.get("/curriculum/wrongbook"));
  const sprint = useAsync<{
    days_left: number | null;
    plan: Array<{ day: number; task: string; detail: string; action: string }>;
  } | null>(
    () => (examDate ? api.get(`/curriculum/sprint?exam_date=${examDate}`) : Promise.resolve(null)),
    [examDate],
  );

  const generateTasks = async () => {
    await api.post("/curriculum/tasks/generate", {});
    tasks.refresh();
  };
  const complete = async (id: number) => {
    await api.post(`/curriculum/tasks/${id}/complete`, {});
    tasks.refresh();
  };
  const regeneratePlan = async () => {
    await api.post("/curriculum/plan/generate", {});
    plan.refresh();
  };

  if (profile.loading) return <Loading />;
  const p = profile.data;
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>我的学习控制台</h1>
          <p>我的综合掌握度：{p?.avg_mastery ?? 0}% · 今日任务与个性化计划均基于真实学习数据生成</p>
        </div>
        <button className="btn btn-primary" onClick={() => void generateTasks()}>⟳ 生成今日任务</button>
      </div>

      <div className="grid grid-2 mb-16">
        <Card
          title="今日任务"
          extra={<span className="badge orange">{tasks.data?.filter((t) => t.status === "todo").length ?? 0} 待办</span>}
        >
          {!tasks.data || tasks.data.filter((t) => t.status === "todo").length === 0 ? (
            <EmptyState emoji="✅" text="今天没有待办任务，点击右上角生成" />
          ) : (
            tasks.data.filter((t) => t.status === "todo").slice(0, 6).map((t) => (
              <div key={t.id} className="row space-between" style={{ padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
                <div className="grow">
                  <b>{t.title}</b>
                  <div className="small muted">{t.reason}</div>
                </div>
                <button className="btn btn-sm btn-primary" onClick={() => void complete(t.id)}>完成</button>
              </div>
            ))
          )}
        </Card>

        <Card
          title="个性化学习计划"
          extra={<button className="btn btn-sm" onClick={() => void regeneratePlan()}>重新生成</button>}
        >
          {plan.data ? (
            <>
              <p className="small muted">{plan.data.reason}</p>
              {plan.data.content.map((s) => (
                <div key={s.order} className="small" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                  <b>{s.order}. {s.title}</b>
                  <div className="muted">{s.detail}</div>
                </div>
              ))}
            </>
          ) : (
            <EmptyState text="暂无计划" />
          )}
        </Card>
      </div>

      <div className="grid grid-2 mb-16">
        <Card title="知识点掌握画像">
          {!p || p.knowledge.length === 0 ? (
            <EmptyState text="暂无画像数据，先完成作业/测验" />
          ) : (
            <BarChart
              data={p.knowledge.slice(0, 12).map((k) => ({ label: k.knowledge_point, value: k.mastery }))}
              height={220}
            />
          )}
        </Card>
        <Card title="薄弱知识点（含证据）">
          {!p || p.knowledge.filter((k) => k.mastery < 60).length === 0 ? (
            <div className="badge green">无明显薄弱点</div>
          ) : (
            p.knowledge.filter((k) => k.mastery < 60).map((k) => (
              <div key={k.knowledge_point_id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <div>
                  <b>{k.knowledge_point}</b>
                  <div className="small muted">{k.subject} · {k.attempts} 次作答 · {k.errors} 次错误</div>
                </div>
                <div className="row" style={{ width: 140 }}>
                  <Progress value={k.mastery} tone="auto" />
                  <span className="small">{k.mastery}%</span>
                </div>
              </div>
            ))
          )}
        </Card>
      </div>

      <div className="grid grid-2 mb-16">
        <Card
          title={`错题本（${wrongbook.data?.total_wrong ?? 0} 道）`}
          extra={<button className="btn btn-sm" onClick={wrongbook.refresh}>⟳ 刷新</button>}
        >
          {!wrongbook.data || wrongbook.data.by_knowledge_point.length === 0 ? (
            <EmptyState emoji="🎉" text="暂无错题，继续保持" />
          ) : (
            <>
              {wrongbook.data.by_knowledge_point.map((k) => (
                <div key={k.knowledge_point_id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <b>{k.name}</b>
                    <div className="small muted">题型：{k.qtypes.join(" / ") || "—"}</div>
                  </div>
                  <span className="badge red">{k.count} 次错误</span>
                </div>
              ))}
              {wrongbook.data.samples.slice(0, 3).map((s, i) => (
                <div key={i} className="small mt-8" style={{ padding: "6px 0", borderTop: "1px dashed var(--border)" }}>
                  <b>{s.title}</b>
                  <div className="muted">{s.analysis}</div>
                </div>
              ))}
            </>
          )}
        </Card>

        <Card
          title="考前冲刺计划"
          extra={<input type="date" className="input" style={{ width: 150 }} value={examDate} onChange={(e) => setExamDate(e.target.value)} />}
        >
          {!examDate ? (
            <EmptyState text="选择考试日期，生成倒计时冲刺计划" />
          ) : !sprint.data ? (
            <Loading />
          ) : sprint.data.plan.length === 0 ? (
            <div className="badge green">无薄弱知识点，无需冲刺</div>
          ) : (
            <>
              <p className="small muted">距考试 {sprint.data.days_left ?? "?"} 天 · 共 {sprint.data.plan.length} 天计划</p>
              {sprint.data.plan.map((s) => (
                <div key={s.day} className="row" style={{ alignItems: "flex-start", padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
                  <span className="badge purple">Day {s.day}</span>
                  <div className="grow small">
                    <b>{s.task}</b>
                    <div className="muted">{s.detail}</div>
                    <div className="muted">行动：{s.action}</div>
                  </div>
                </div>
              ))}
            </>
          )}
        </Card>
      </div>

      <div className="grid grid-2">
        <Card title="当前课程掌握度" extra={<button className="btn btn-sm" onClick={() => navigate("/learn/courses")}>我的课程</button>}>
          {(courses.data ?? []).map((c) => (
            <div key={c.id} className="row space-between" style={{ padding: "8px 0" }} onClick={() => navigate(`/learn/courses/${c.id}`)}>
              <div className="grow" style={{ cursor: "pointer" }}>
                <b>{c.name}</b>
                <div className="small muted">进度 {c.progress}% · 待办 {c.pending_tasks}</div>
              </div>
              <div className="row" style={{ width: 130 }}>
                <Progress value={c.mastery} tone="auto" />
                <span className="small">{c.mastery}%</span>
              </div>
            </div>
          ))}
        </Card>
        <Card title="AI 学习规划师" extra={<button className="btn btn-sm" onClick={() => navigate("/learn/tutor")}>去问导师</button>}>
          <p className="small muted">
            规划师会结合你的作业表现、评测结果、测验与答疑记录，解释“为什么推荐这个知识点”，
            并生成可执行的今日任务与复习计划。
          </p>
          <button className="btn btn-primary" onClick={() => navigate("/learn/tutor")}>✉ 开始对话</button>
        </Card>
      </div>
    </div>
  );
}
