/** AI 辅助批改：AI 建议分 → 教师审核 → 确认最终成绩。 */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api";
import { Card, EmptyState, Loading, useAsync } from "../../components/ui";
import type { SubmissionDetail } from "../../types";

export default function TeacherGrading() {
  const { submissionId } = useParams();
  const detail = useAsync<SubmissionDetail>(() => api.get(`/submissions/${submissionId}`), [submissionId]);
  const [finalScore, setFinalScore] = useState<number | "">("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const triggerAI = async () => {
    setBusy(true);
    setNotice("");
    try {
      await api.post(`/submissions/${submissionId}/ai-review`, {});
      setNotice("AI 建议已刷新");
      window.location.reload();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "AI 批改失败");
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    setBusy(true);
    setNotice("");
    try {
      const score = Number(finalScore);
      if (Number.isNaN(score)) {
        setNotice("请输入有效分数");
        return;
      }
      await api.post(`/submissions/${submissionId}/grade`, { final_score: score, comment });
      setNotice("✅ 成绩已确认，学生端现在可见正式成绩");
      window.location.reload();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "确认失败");
    } finally {
      setBusy(false);
    }
  };

  if (detail.loading) return <Loading />;
  const d = detail.data;
  if (!d) return <EmptyState text="提交不存在" />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>批改：{d.question_title}</h1>
          <p>{d.assignment_title} · 学生 {d.student_name} · 满分 {d.max_score}</p>
        </div>
        <Link to={`/teacher/assignments/${d.assignment_id}`} className="btn">← 返回作业</Link>
      </div>

      <div className="grid grid-2" style={{ alignItems: "start" }}>
        <div>
          <Card title="题目要求">
            <p className="small" style={{ whiteSpace: "pre-wrap" }}>{d.question_description}</p>
            {d.test_cases.length > 0 && (
              <div className="mt-8">
                <div className="small muted mb-8">测试点：</div>
                {d.test_cases.map((t) => (
                  <div key={t.id} className="small" style={{ padding: "3px 0" }}>• {t.name}</div>
                ))}
              </div>
            )}
          </Card>

          <Card title={d.qtype === "programming" ? "学生代码" : "学生答案"} className="mt-16">
            {d.code ? (
              <>
                <div className="code-block" style={{ maxHeight: 420, overflow: "auto" }}>{d.code.source_code}</div>
                <div className="row wrap mt-8">
                  <span className={`badge ${d.code.verdict === "accepted" ? "green" : "red"}`}>
                    {d.code.verdict === "accepted" ? "AC" : d.code.verdict === "compile_error" ? "编译错误" : "未通过"} · {d.code.passed_tests}/{d.code.total_tests}
                  </span>
                  <span className="badge gray">耗时 {d.code.runtime_ms}ms</span>
                  {d.code.error_message && <span className="badge orange">{d.code.error_message}</span>}
                </div>
                {d.code.judge_report.length > 0 && (
                  <div className="table-wrap mt-8">
                    <table className="table">
                      <thead>
                        <tr><th>测试点</th><th>结果</th><th>说明</th></tr>
                      </thead>
                      <tbody>
                        {d.code.judge_report.map((t) => (
                          <tr key={t.id}>
                            <td>{t.name}</td>
                            <td><span className={`badge ${t.passed ? "green" : "red"}`}>{t.passed ? "通过" : "未通过"}</span></td>
                            <td className="small">{t.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            ) : (
              <p className="small" style={{ whiteSpace: "pre-wrap" }}>{d.subjective?.content}</p>
            )}
          </Card>
        </div>

        <div>
          <Card
            title="AI 辅助批改（仅供参考）"
            extra={<button className="btn btn-sm" onClick={() => void triggerAI()} disabled={busy}>⟳ 重新分析</button>}
          >
            {d.subjective && d.subjective.ai_suggestion_score != null ? (
              <>
                <div className="row mb-8">
                  <span className="stat-value" style={{ fontSize: 32, fontWeight: 700 }}>{d.subjective.ai_suggestion_score}</span>
                  <span className="muted small">/ {d.max_score} 分（AI 建议）</span>
                </div>
                <h3>评分理由</h3>
                <p className="small">{d.subjective.ai_reasoning}</p>
                {d.subjective.ai_knowledge_points.length > 0 && (
                  <>
                    <h3>涉及知识点</h3>
                    <div className="row wrap">
                      {d.subjective.ai_knowledge_points.map((k) => <span key={k} className="badge">{k}</span>)}
                    </div>
                  </>
                )}
                {d.subjective.ai_error_analysis && (
                  <>
                    <h3>错误与不足</h3>
                    <p className="small" style={{ whiteSpace: "pre-wrap" }}>{d.subjective.ai_error_analysis}</p>
                  </>
                )}
                {d.subjective.ai_improvement && (
                  <>
                    <h3>改进建议</h3>
                    <p className="small">{d.subjective.ai_improvement}</p>
                  </>
                )}
              </>
            ) : (
              <div className="empty">
                <div className="emoji">🤖</div>
                <div>{d.qtype === "programming" ? "编程题已自动评测，可直接确认成绩" : "点击「重新分析」生成 AI 建议"}</div>
              </div>
            )}
          </Card>

          <Card title="教师确认最终成绩" className="mt-16">
            <div className="form-grid">
              <div className="field">
                <label>最终分数 *（以教师确认为准）</label>
                <input type="number" className="input" value={finalScore}
                  onChange={(e) => setFinalScore(e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder={d.subjective?.ai_suggestion_score?.toString() ?? "0-10"} max={d.max_score} min={0} />
              </div>
              <div className="field">
                <label>评语</label>
                <input className="input" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="给学生的评语" />
              </div>
            </div>
            {d.status === "graded" && d.subjective?.teacher_score != null && (
              <div className="badge green mb-8">当前已确认成绩：{d.subjective.teacher_score} 分</div>
            )}
            {notice && <div className="mb-8" style={{ color: "var(--success)" }}>{notice}</div>}
            <button className="btn btn-primary" onClick={() => void confirm()} disabled={busy || finalScore === ""}>
              {busy ? "处理中…" : "✓ 确认最终成绩"}
            </button>
            <p className="small muted mt-8">AI 不决定最终成绩；学生只有在您确认后才会看到正式分数。</p>
          </Card>
        </div>
      </div>
    </div>
  );
}

