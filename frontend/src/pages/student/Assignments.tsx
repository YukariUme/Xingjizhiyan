/** 作业中心：待完成 / 已完成。 */

import { Link } from "react-router-dom";
import { api } from "../../api";
import { Card, EmptyState, Loading, useAsync } from "../../components/ui";
import type { Assignment, MySubmission } from "../../types";

export default function StudentAssignments() {
  const assignments = useAsync<Assignment[]>(() => api.get("/assignments"));
  const submissions = useAsync<MySubmission[]>(() => api.get("/me/submissions"));
  if (assignments.loading) return <Loading />;

  const subMap = new Map(submissions.data?.map((s) => [s.question_id, s]) ?? []);
  const countDone = (a: Assignment) => a.questions.filter((q) => subMap.has(q.id)).length;
  const countGraded = (a: Assignment) =>
    a.questions.filter((q) => {
      const s = subMap.get(q.id);
      return s && (s.teacher_reviewed || s.verdict === "accepted");
    }).length;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>作业中心</h1>
          <p>编程题在线评测 · 简答题 AI 建议批改（教师确认后显示正式成绩）</p>
        </div>
      </div>
      {!assignments.data || assignments.data.length === 0 ? (
        <EmptyState text="暂无作业" />
      ) : (
        <div className="grid grid-2">
          {assignments.data.map((a) => (
            <Card key={a.id} title={a.title} extra={<span className="badge gray">{a.course_name}</span>}>
              <p className="small muted">{a.description}</p>
              <div className="row wrap mb-8">
                {a.questions.map((q) => {
                  const s = subMap.get(q.id);
                  return (
                    <span key={q.id} className={`badge ${s ? (s.teacher_reviewed || s.verdict === "accepted" ? "green" : "orange") : "gray"}`}>
                      {q.qtype === "programming" ? "编程" : q.qtype === "report" ? "实验" : "简答"} ·{" "}
                      {s ? (s.teacher_reviewed || s.verdict === "accepted" ? "已完成" : s.status === "under_review" ? "待教师确认" : "已提交") : "未完成"}
                    </span>
                  );
                })}
              </div>
              <div className="row space-between">
                <div className="small muted">
                  截止 {new Date(a.due_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })} · 完成 {countDone(a)}/{a.questions.length}
                </div>
                <Link to={`/student/assignments/${a.id}`} className="btn btn-sm btn-primary">进入作业</Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

