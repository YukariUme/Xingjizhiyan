/** 我的课程：课程卡片（进度 / 掌握度 / 当前章节 / 待办），点击进入课程空间。 */

import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { Card, EmptyState, Loading, Progress, useAsync } from "../../components/ui";

type LearningCourse = {
  id: number;
  name: string;
  code: string;
  semester: string;
  description: string;
  progress: number;
  mastery: number;
  current_chapter: { id: number; title: string } | null;
  pending_tasks: number;
  weak_points: string[];
  last_study: string | null;
};

export default function StudentCourses() {
  const navigate = useNavigate();
  const { data, loading, error } = useAsync<LearningCourse[]>(() => api.get("/curriculum/courses"));
  if (loading) return <Loading />;
  if (error) return <div className="badge red">{error}</div>;
  if (!data || data.length === 0) return <EmptyState text="暂无课程，等待教师邀请" />;
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>我的课程</h1>
          <p>点击任意课程进入独立学习空间：预习 → 讲堂 → 作业 → 复习 → 模拟</p>
        </div>
      </div>
      <div className="grid grid-3">
        {data.map((c) => (
          <Card
            key={c.id}
            title={c.name}
            extra={<span className="badge gray">{c.code}</span>}
          >
            <div className="small muted mb-8">{c.semester} · {c.description?.slice(0, 40)}</div>
            <div className="row space-between" style={{ padding: "4px 0" }}>
              <span className="small">课程进度</span>
              <div className="row" style={{ width: 130 }}>
                <Progress value={c.progress} tone="auto" />
                <span className="small">{c.progress}%</span>
              </div>
            </div>
            <div className="row space-between" style={{ padding: "4px 0" }}>
              <span className="small">综合掌握度</span>
              <div className="row" style={{ width: 130 }}>
                <Progress value={c.mastery} tone="auto" />
                <span className="small">{c.mastery}%</span>
              </div>
            </div>
            <div className="small muted mt-8">
              当前章节：{c.current_chapter?.title ?? "尚未开始"} · 待办 {c.pending_tasks}
            </div>
            {c.weak_points.length > 0 && (
              <div className="row wrap mt-8">
                {c.weak_points.map((w) => <span key={w} className="badge red">{w}</span>)}
              </div>
            )}
            <button className="btn btn-primary mt-16" onClick={() => navigate(`/learn/courses/${c.id}`)}>
              进入课程空间 →
            </button>
          </Card>
        ))}
      </div>
    </div>
  );
}

