/** 学生首页。 */

import { Link } from "react-router-dom";
import { api } from "../../api";
import { Card, Loading, Progress, StatCard, useAsync } from "../../components/ui";
import type { Activity, Assignment, CourseInvitation, MySubmission, Recommendation, StudentProfile } from "../../types";

export default function StudentHome() {
  const assignments = useAsync<Assignment[]>(() => api.get("/assignments"));
  const submissions = useAsync<MySubmission[]>(() => api.get("/me/submissions"));
  const profile = useAsync<StudentProfile>(() => api.get("/analytics/me"));
  const recs = useAsync<Recommendation[]>(() => api.get("/learning/recommendations"));
  const activities = useAsync<Activity[]>(() => api.get("/activities?limit=8"));
  const invitations = useAsync<CourseInvitation[]>(() => api.get("/course-invitations"));

  if (assignments.loading || submissions.loading) return <Loading />;
  const pending = assignments.data?.length ?? 0;
  const done = submissions.data?.filter((s) => s.teacher_reviewed || s.verdict === "accepted").length ?? 0;
  const recentScores = submissions.data?.filter((s) => s.score != null).slice(0, 5) ?? [];
  const weak = profile.data?.weak_points ?? [];
  const respond = async (inv: CourseInvitation, action: "accept" | "decline") => {
    try {
      await api.post(`/course-invitations/${inv.id}/${action}`, {});
      invitations.refresh();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "操作失败");
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>我的学习空间</h1>
          <p>学习 → 作业 → 自动评测 → 错误诊断 → 个性化路径，AI 全程陪伴</p>
        </div>
        <Link to="/learn/tutor" className="btn btn-primary">✉ 问 AI 导师</Link>
      </div>

      <div className="grid grid-4 mb-16">
        <StatCard label="待完成作业" value={pending} hint="已发布" />
        <StatCard label="已完成任务" value={done} hint="含已确认成绩" />
        <StatCard label="薄弱知识点" value={weak.length} hint="掌握度低于 60%" color={weak.length ? "var(--warning)" : "var(--success)"} />
        <StatCard label="平均掌握度" value={`${profile.data?.avg_mastery ?? 0}%`} hint="基于知识画像" />
      </div>

      {(invitations.data?.length ?? 0) > 0 && (
        <div className="grid mb-16">
          <Card title="课程邀请（待你确认）">
            {invitations.data?.map((inv) => (
              <div key={inv.id} className="row space-between" style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                <div>
                  <b>{inv.course_name}</b>
                  <div className="small muted">
                    {inv.course_code} · {inv.semester} · 邀请人 {inv.teacher_name}
                  </div>
                </div>
                <div className="row">
                  <button className="btn btn-sm btn-primary" onClick={() => void respond(inv, "accept")}>
                    接受
                  </button>
                  <button className="btn btn-sm" onClick={() => void respond(inv, "decline")}>
                    拒绝
                  </button>
                </div>
              </div>
            ))}
          </Card>
        </div>
      )}

      <div className="grid grid-2">
        <Card title="最近成绩" extra={<Link to="/learn/assignments" className="btn btn-sm">作业中心</Link>}>
          {recentScores.length === 0 ? (
            <div className="muted small">暂无正式成绩（教师确认后可见）</div>
          ) : (
            recentScores.map((s) => (
              <div key={s.submission_id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <span>{s.question_title}</span>
                <b style={{ color: "var(--success)" }}>{s.score} 分</b>
              </div>
            ))
          )}
        </Card>

        <Card title="薄弱知识点" extra={<Link to="/learn/center" className="btn btn-sm">学习中心</Link>}>
          {weak.length === 0 ? (
            <div className="empty">
              <div className="emoji">🎉</div>
              <div>没有明显薄弱知识点</div>
            </div>
          ) : (
            (profile.data?.knowledge.filter((k) => k.mastery < 60) ?? []).slice(0, 5).map((k) => (
              <div key={k.knowledge_point_id} className="row space-between" style={{ padding: "8px 0" }}>
                <div>
                  <b>{k.knowledge_point}</b>
                  <div className="small muted">{k.subject} · {k.attempts} 次作答</div>
                </div>
                <div className="row" style={{ width: 160 }}>
                  <Progress value={k.mastery} tone="auto" />
                  <span className="small">{k.mastery}%</span>
                </div>
              </div>
            ))
          )}
        </Card>
      </div>

      <div className="grid grid-2 mt-16">
        <Card title="个性化学习推荐" extra={<Link to="/learn/center" className="btn btn-sm">查看全部</Link>}>
          {(recs.data ?? []).slice(0, 5).map((r) => (
            <div key={r.id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <div>
                <b>{r.resource_title}</b>
                <div className="small muted">{r.reason}</div>
              </div>
              <span className="badge purple">
                {{ chapter: "复习", exercise: "练习", experiment: "实验", paper: "论文", next: "进阶" }[r.resource_type] ?? r.resource_type}
              </span>
            </div>
          ))}
        </Card>

        <Card title="最近动态">
          {activities.data?.map((a) => (
            <div key={a.id} className="small" style={{ padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
              {a.title}
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
