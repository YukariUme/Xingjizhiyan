/** 学生首页：编辑式布局，轻卡片 + 渐变点缀。 */

import { Link, useNavigate } from "react-router-dom";
import { api } from "../../api";
import { Loading, Progress, useAsync } from "../../components/ui";
import type { Activity, Assignment, CourseInvitation, MySubmission, Recommendation, StudentProfile } from "../../types";

interface MyCourse {
  id: number;
  name: string;
  progress: number;
  mastery: number;
  current_chapter: { id: number; title: string } | null;
  pending_tasks: number;
  weak_points: string[];
}

const ROLE_LABEL: Record<string, string> = { teacher: "教师", student: "学生", researcher: "科研" };
const RES_TYPE: Record<string, string> = {
  chapter: "复习",
  exercise: "练习",
  experiment: "实验",
  paper: "论文",
  next: "进阶",
};

function fmtTime(iso: string): string {
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export default function StudentHome() {
  const navigate = useNavigate();
  const courses = useAsync<MyCourse[]>(() => api.get("/curriculum/courses"));
  const assignments = useAsync<Assignment[]>(() => api.get("/assignments"));
  const submissions = useAsync<MySubmission[]>(() => api.get("/me/submissions"));
  const profile = useAsync<StudentProfile>(() => api.get("/analytics/me"));
  const recs = useAsync<Recommendation[]>(() => api.get("/learning/recommendations"));
  const activities = useAsync<Activity[]>(() => api.get("/activities?limit=8"));
  const invitations = useAsync<CourseInvitation[]>(() => api.get("/course-invitations"));

  if (assignments.loading || submissions.loading) return <Loading />;

  const pending = assignments.data?.length ?? 0;
  const recentScores = submissions.data?.filter((s) => s.score != null).slice(0, 5) ?? [];
  const weak = profile.data?.weak_points ?? [];
  const weakItems = (profile.data?.knowledge ?? []).filter((k) => k.mastery < 60).slice(0, 5);
  const avgMastery = profile.data?.avg_mastery ?? 0;
  const firstCourse = courses.data?.[0];

  const respond = async (inv: CourseInvitation, action: "accept" | "decline") => {
    try {
      await api.post(`/course-invitations/${inv.id}/${action}`, {});
      invitations.refresh();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "操作失败");
    }
  };

  return (
    <div className="page home-page">
      <section className="home-hero">
        <div className="home-hero-copy">
          <span className="home-kicker">星计知研 · 学习空间</span>
          <h1>把今天该学的，一步讲清楚</h1>
          <p>从知识点到动图、代码与练习，AI 陪你把薄弱点逐个补上。</p>
        </div>
        <button
          className="home-cta"
          onClick={() => navigate(firstCourse ? `/learn/courses/${firstCourse.id}` : "/learn/courses")}
        >
          继续学习 →
        </button>
      </section>

      <section className="home-metrics">
        <div className="home-metric"><b>{pending}</b><span>待完成作业</span></div>
        <div className="home-metric"><b>{avgMastery}%</b><span>平均掌握度</span></div>
        <div className="home-metric"><b>{weak.length}</b><span>薄弱知识点</span></div>
        <div className="home-metric"><b>{invitations.data?.length ?? 0}</b><span>待处理邀请</span></div>
      </section>

      {(invitations.data?.length ?? 0) > 0 && (
        <section className="home-invites">
          <h2 className="home-section-title">课程邀请</h2>
          {invitations.data?.map((inv) => (
            <div className="home-item" key={inv.id}>
              <div className="grow">
                <b>{inv.course_name}</b>
                <div className="small muted">{inv.course_code} · {inv.semester} · 邀请人 {inv.teacher_name}</div>
              </div>
              <div className="row">
                <button className="btn btn-sm btn-primary" onClick={() => void respond(inv, "accept")}>接受</button>
                <button className="btn btn-sm" onClick={() => void respond(inv, "decline")}>拒绝</button>
              </div>
            </div>
          ))}
        </section>
      )}

      <div className="home-grid">
        <div>
          <section className="home-section">
            <h2 className="home-section-title">我的课程</h2>
            {courses.data?.length ? (
              courses.data.slice(0, 4).map((c) => (
                <div className="home-course" key={c.id}>
                  <div className="row space-between">
                    <div>
                      <Link className="home-course-name" to={`/learn/courses/${c.id}`}>{c.name}</Link>
                      <div className="small muted">{c.current_chapter?.title ?? "尚未开始"}</div>
                    </div>
                    <span className="small muted">{c.mastery}%</span>
                  </div>
                  <div className="home-progress"><span style={{ width: `${c.progress}%` }} /></div>
                </div>
              ))
            ) : (
              <div className="muted small">还没有课程，去“我的课程”加入吧。</div>
            )}
          </section>

          <section className="home-section">
            <h2 className="home-section-title">最近成绩</h2>
            {recentScores.length === 0 ? (
              <div className="muted small">暂无正式成绩（教师确认后可见）</div>
            ) : (
              recentScores.map((s) => (
                <div className="home-item" key={s.submission_id}>
                  <span>{s.question_title}</span>
                  <b style={{ color: "var(--success)" }}>{s.score} 分</b>
                </div>
              ))
            )}
          </section>
        </div>

        <div>
          <section className="home-section">
            <h2 className="home-section-title">下一步建议</h2>
            {(recs.data ?? []).slice(0, 5).map((r) => (
              <div className="home-item" key={r.id}>
                <div className="grow">
                  <b>{r.resource_title}</b>
                  <div className="small muted">{r.reason}</div>
                </div>
                <span className="home-tag">{RES_TYPE[r.resource_type] ?? r.resource_type}</span>
              </div>
            ))}
          </section>

          <section className="home-section">
            <h2 className="home-section-title">薄弱知识点</h2>
            {weakItems.length === 0 ? (
              <div className="home-ok">没有明显薄弱点，保持节奏。</div>
            ) : (
              weakItems.map((k) => (
                <div className="home-item" key={k.knowledge_point_id}>
                  <div className="grow">
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
          </section>
        </div>
      </div>

      <section className="home-section">
        <h2 className="home-section-title">最近动态</h2>
        <div className="home-timeline">
          {activities.data?.map((a) => (
            <div className="home-activity" key={a.id}>
              <span className="home-role">{ROLE_LABEL[a.role] ?? a.role}</span>
              <span className="grow">{a.title}</span>
              <span className="small muted">{fmtTime(a.created_at)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
