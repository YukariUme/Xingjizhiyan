/** 作业详情：提交矩阵（学生 × 题目）。 */

import { Link, useParams } from "react-router-dom";
import { api } from "../../api";
import { Card, EmptyState, Loading, statusBadge, useAsync } from "../../components/ui";
import { verdictClass, verdictLabel } from "../verdict";
import type { Assignment } from "../../types";

interface MatrixRow {
  submission_id: number;
  assignment_id: number;
  question_id: number;
  student_id: number;
  student_name: string;
  qtype: string;
  status: string;
  verdict: string | null;
  passed_tests: number | null;
  total_tests: number | null;
  ai_suggestion_score: number | null;
  teacher_score: number | null;
  created_at: string;
}

export default function TeacherAssignmentDetail() {
  const { id } = useParams();
  const assignment = useAsync<Assignment>(() => api.get<Assignment>(`/assignments/${id}`), [id]);
  const rows = useAsync<MatrixRow[]>(() => api.get(`/assignments/${id}/submissions`), [id]);

  if (assignment.loading || rows.loading) return <Loading />;
  const a = assignment.data;
  if (!a) return <EmptyState text="作业不存在" />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{a.title}</h1>
          <p>{a.course_name} · 截止 {new Date(a.due_at).toLocaleString("zh-CN")} · 已提交 {a.submitted_count}/{a.student_count}</p>
        </div>
        <Link to="/teacher/assignments" className="btn">← 返回</Link>
      </div>

      <div className="grid mb-16">
        {a.questions.map((q) => (
          <Card key={q.id} title={`${q.qtype === "programming" ? "编程题" : q.qtype === "report" ? "实验报告" : "简答题"} · ${q.title}`} extra={<span className="badge gray">{q.max_score} 分</span>}>
            <p className="small muted">{q.description}</p>
          </Card>
        ))}
      </div>

      <Card title="学生提交情况">
        {!rows.data || rows.data.length === 0 ? (
          <EmptyState text="还没有学生提交" />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>学生</th>
                  <th>题目</th>
                  <th>类型</th>
                  <th>状态</th>
                  <th>评测 / AI 建议</th>
                  <th>最终成绩</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {rows.data.map((r) => (
                  <tr key={r.submission_id}>
                    <td><b>{r.student_name}</b></td>
                    <td>{a.questions.find((q) => q.id === r.question_id)?.title ?? `题目 #${r.question_id}`}</td>
                    <td>
                      <span className="badge gray">
                        {r.qtype === "programming" ? "编程" : r.qtype === "report" ? "实验" : "简答"}
                      </span>
                    </td>
                    <td>{statusBadge(r.status)}</td>
                    <td>
                      {r.verdict ? (
                        <span className={`badge ${verdictClass(r.verdict)}`}>
                          {verdictLabel(r.verdict)} · {r.passed_tests}/{r.total_tests}
                        </span>
                      ) : r.ai_suggestion_score != null ? (
                        <span className="badge orange">AI 建议 {r.ai_suggestion_score}</span>
                      ) : (
                        <span className="muted small">—</span>
                      )}
                    </td>
                    <td>{r.teacher_score != null ? <b>{r.teacher_score}</b> : <span className="muted small">待定</span>}</td>
                    <td>
                      {r.qtype !== "programming" ? (
                        <Link to={`/teacher/grading/${r.submission_id}`} className="btn btn-sm btn-primary">批改</Link>
                      ) : (
                        <Link to={`/teacher/grading/${r.submission_id}`} className="btn btn-sm">查看</Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
