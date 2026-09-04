/** 教师首页 Dashboard。 */

import { Link } from "react-router-dom";
import { api } from "../../api";
import { Card, ErrorBanner, Loading, Progress, StatCard, useAsync } from "../../components/ui";
import type { Activity, ClassAnalytics, Course, GradingItem } from "../../types";

export default function TeacherDashboard() {
  const courses = useAsync<Course[]>(() => api.get("/courses"));
  const worklist = useAsync<GradingItem[]>(() => api.get("/grading/worklist"));
  const firstCourse = courses.data?.[0]?.id;
  const analytics = useAsync<ClassAnalytics | null>(
    () => (firstCourse ? api.get(`/analytics/courses/${firstCourse}`) : Promise.resolve(null)),
    [firstCourse]
  );
  const activities = useAsync<Activity[]>(() => api.get("/activities?limit=8"));
  const reviews = useAsync<Array<{ id: number; title: string }>>(() => api.get("/knowledge/reviews?status=pending"));

  if (courses.loading || worklist.loading || activities.loading) return <Loading />;
  if (courses.error || worklist.error || activities.error || analytics.error) {
    return (
      <ErrorBanner
        message={courses.error || worklist.error || activities.error || analytics.error || ""}
      />
    );
  }

  const pending = worklist.data?.filter((w) => w.teacher_score === null) ?? [];
  const total = worklist.data?.length ?? 0;
  const acc = analytics.data;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>教师工作台</h1>
          <p>智能备课 → 发布作业 → AI 辅助批改 → 学情分析 → 调整教学</p>
        </div>
        <Link to="/teacher/lesson-plan" className="btn btn-primary">
          ✎ 智能备课
        </Link>
      </div>

      <div className="grid grid-4 mb-16">
        <StatCard label="当前课程" value={courses.data?.length ?? 0} hint="本学期开设" />
        <StatCard label="待批改作业" value={pending.length} hint={`批改台共 ${total} 条`} color={pending.length ? "var(--warning)" : undefined} />
        <StatCard label="班级平均正确率" value={acc ? `${acc.avg_accuracy}%` : "—"} hint={acc?.course_name} />
        <StatCard label="待审核资料" value={reviews.data?.length ?? 0} hint="学生申请加入课程共享" color={(reviews.data?.length ?? 0) ? "var(--warning)" : undefined} />
      </div>

      {(reviews.data?.length ?? 0) > 0 && (
        <div className="card mb-16">
          <div className="row space-between">
            <div>
              <b>本周有 {reviews.data?.length} 份学生资料申请进入共享知识空间</b>
              <div className="small muted">通过后成为 [A] 级共享资料，可被课程 RAG 使用</div>
            </div>
            <Link to="/teach/knowledge" className="btn btn-primary btn-sm">去审核</Link>
          </div>
        </div>
      )}

      <div className="grid grid-2">
        <Card
          title="当前课程"
          extra={<Link to="/teacher/courses" className="btn btn-sm">管理</Link>}
        >
          {courses.data?.map((c) => (
            <div key={c.id} className="row space-between" style={{ padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
              <div>
                <b>{c.name}</b>
                <div className="small muted">{c.code} · {c.semester}</div>
              </div>
              <div className="row">
                <span className="badge">{c.student_count} 学生</span>
                <span className="badge gray">{c.assignment_count} 作业</span>
              </div>
            </div>
          ))}
        </Card>

        <Card
          title="待批改作业"
          extra={<Link to="/teacher/assignments" className="btn btn-sm">全部作业</Link>}
        >
          {pending.length === 0 ? (
            <div className="empty">
              <div className="emoji">🎉</div>
              <div>没有待批改的作业</div>
            </div>
          ) : (
            pending.slice(0, 6).map((w) => (
              <div key={w.submission_id} className="row space-between" style={{ padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
                <div>
                  <b>{w.student_name}</b> · {w.question_title}
                  <div className="small muted">{w.assignment_title}</div>
                </div>
                <div className="row">
                  {w.ai_reviewed && <span className="badge orange">AI 已建议 {w.ai_suggestion_score} 分</span>}
                  <Link to={`/teacher/grading/${w.submission_id}`} className="btn btn-sm btn-primary">去批改</Link>
                </div>
              </div>
            ))
          )}
        </Card>
      </div>

      <div className="grid grid-2 mt-16">
        <Card
          title="高频错误知识点"
          extra={acc && <Link to="/teacher/analytics" className="btn btn-sm">详细学情</Link>}
        >
          {acc && acc.high_frequency_errors.length > 0 ? (
            acc.high_frequency_errors.slice(0, 6).map((k) => (
              <div key={k.knowledge_point_id} className="row space-between" style={{ padding: "8px 0" }}>
                <div>
                  <b>{k.name}</b>
                  <div className="small muted">{k.subject} · {k.attempts} 次尝试</div>
                </div>
                <div className="row" style={{ width: 180 }}>
                  <Progress value={k.accuracy} tone="auto" />
                  <span className="small">{k.accuracy}%</span>
                </div>
              </div>
            ))
          ) : (
            <div className="muted small">暂无错误知识点数据</div>
          )}
        </Card>

        <Card title="最近教学活动">
          {activities.data?.map((a) => (
            <div key={a.id} className="row space-between" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
              <span>{a.title}</span>
              <span className="small muted">
                {new Date(a.created_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
