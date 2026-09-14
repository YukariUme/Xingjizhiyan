/** 作业详情：编程题在线编辑/评测/诊断，简答题提交。 */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api";
import { CodeEditor } from "../../components/CodeEditor";
import { Card, EmptyState, Loading, Tabs, statusBadge, useAsync } from "../../components/ui";
import { verdictClass, verdictLabel } from "../verdict";
import type { Assignment, DiagnosisResult, MySubmission, Question, SubmissionDetail, TestCase } from "../../types";

const CODE_LANGUAGES = [
  { key: "python", label: "Python" },
  { key: "java", label: "Java" },
  { key: "cpp", label: "C++" },
  { key: "c", label: "C" },
];

const DEFAULT_TEMPLATES: Record<string, string> = {
  python: "def solution(...):\n    # TODO\n    pass\n",
  java: "public class Main {\n    public static void main(String[] args) {\n        // TODO\n    }\n}\n",
  cpp: "#include <iostream>\nusing namespace std;\n\nint main() {\n    // TODO\n    return 0;\n}\n",
  c: "#include <stdio.h>\n\nint main() {\n    // TODO\n    return 0;\n}\n",
};

function QuestionView({ assignmentId, courseId, question, submission }: {
  assignmentId: number;
  courseId: number;
  question: Question;
  submission: MySubmission | undefined;
}) {
  const [code, setCode] = useState(question.code_template);
  const [language, setLanguage] = useState(
    ["python", "java", "cpp", "c"].includes(question.language) ? question.language : "python"
  );
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<SubmissionDetail | null>(null);
  const [judge, setJudge] = useState<{ verdict: string; passed_tests: number; total_tests: number; runtime_ms: number; error_message: string; judge_report: TestCase[] } | null>(null);
  const [diagnosis, setDiagnosis] = useState<DiagnosisResult | null>(null);
  const [mode, setMode] = useState<"hint" | "detail">("hint");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const loadDetail = async () => {
    if (!submission) return;
    try {
      const d = await api.get<SubmissionDetail>(`/submissions/${submission.submission_id}`);
      setResult(d);
      if (d.code) {
        setJudge({
          verdict: d.code.verdict,
          passed_tests: d.code.passed_tests,
          total_tests: d.code.total_tests,
          runtime_ms: d.code.runtime_ms,
          error_message: d.code.error_message,
          judge_report: d.code.judge_report,
        });
        setCode(d.code.source_code ?? "");
      }
      if (d.subjective) setAnswer(d.subjective.content);
    } catch {
      /* 忽略 */
    }
  };

  const submitCode = async () => {
    setBusy(true);
    setNotice("");
    setDiagnosis(null);
    try {
      const res = await api.post<{ verdict: string; passed_tests: number; total_tests: number; runtime_ms: number; error_message: string; judge_report: TestCase[]; workflow_run_id?: number; diagnosis?: DiagnosisResult }>(
        `/assignments/${assignmentId}/questions/${question.id}/submit`,
        { source_code: code, language }
      );
      setJudge(res);
      if (res.diagnosis && res.diagnosis.error_reason) {
        setDiagnosis(res.diagnosis);
      }
      if (res.verdict !== "accepted") {
        setNotice("评测未通过，可以点击「AI 错误诊断」获取分析");
      } else {
        setNotice("✅ 全部测试点通过");
      }
      void loadDetail();
      if (res.workflow_run_id) {
        setNotice((n) => `${n}（工作流 #${res.workflow_run_id} 已记录）`);
      }
      void api.post("/curriculum/records", {
        action: "homework",
        course_id: courseId,
        detail: { assignment_id: assignmentId, question_id: question.id, qtype: question.qtype, verdict: res.verdict },
      });
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "提交失败");
    } finally {
      setBusy(false);
    }
  };

  const submitSubjective = async () => {
    if (!answer.trim()) {
      setNotice("请先填写答案");
      return;
    }
    setBusy(true);
    setNotice("");
    try {
      const res = await api.post<{ submission_id: number; status: string; ai_suggestion_score: number | null }>(
        `/assignments/${assignmentId}/questions/${question.id}/submit`,
        { content: answer }
      );
      setNotice(
        res.status === "under_review"
          ? `已提交，AI 已给出建议 ${res.ai_suggestion_score} 分，等待教师确认正式成绩`
          : "已提交，等待批改"
      );
      void loadDetail();
      void api.post("/curriculum/records", {
        action: "homework",
        course_id: courseId,
        detail: { assignment_id: assignmentId, question_id: question.id, qtype: question.qtype, status: res.status },
      });
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "提交失败");
    } finally {
      setBusy(false);
    }
  };

  const diagnose = async () => {
    if (!judge) return;
    setBusy(true);
    try {
      const res = await api.post<DiagnosisResult>("/learning/diagnose", {
        question_title: question.title,
        question_description: question.description,
        source_code: code,
        language,
        judge_report: judge.judge_report,
        error_message: judge.error_message,
        mode,
      });
      setDiagnosis(res);
      void api.post("/curriculum/records", {
        action: "qa",
        course_id: courseId,
        detail: { assignment_id: assignmentId, question_id: question.id, mode },
      });
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "诊断失败");
    } finally {
      setBusy(false);
    }
  };

  const finalScore = result?.subjective?.teacher_score ?? (judge && judge.verdict === "accepted" ? question.max_score : judge ? (judge.passed_tests / Math.max(1, judge.total_tests)) * question.max_score : null);

  return (
    <Card
      title={`${question.qtype === "programming" ? "编程题" : question.qtype === "report" ? "实验报告" : "简答题"} · ${question.title}`}
      extra={
        <div className="row">
          <span className="badge gray">{question.max_score} 分</span>
          {submission && statusBadge(submission.status)}
        </div>
      }
    >
      <p className="small" style={{ whiteSpace: "pre-wrap" }}>{question.description}</p>

      {question.qtype === "programming" ? (
        <>
          <div className="row mb-8">
            <select
              className="select"
              style={{ width: 170 }}
              value={language}
              onChange={(e) => {
                const next = e.target.value;
                if (next === language) return;
                const keepCode = code.trim() && code !== (DEFAULT_TEMPLATES[language] ?? "");
                setLanguage(next);
                if (!keepCode) setCode(DEFAULT_TEMPLATES[next] ?? "");
              }}
              aria-label="选择编程语言"
            >
              {CODE_LANGUAGES.map((l) => (
                <option key={l.key} value={l.key}>
                  {l.label}
                </option>
              ))}
            </select>
            <span className="small muted">支持 C / C++ / Java / Python，切换语言会替换为对应模板</span>
          </div>
          <CodeEditor
            value={code}
            onChange={setCode}
            language={language}
            highlightLines={(diagnosis?.line_anchors ?? []).map((a) => a.line)}
          />
          <div className="row mt-8">
            <button className="btn btn-primary" onClick={() => void submitCode()} disabled={busy || !code.trim()}>
              {busy ? "评测中…" : "提交评测"}
            </button>
            {judge && judge.verdict !== "accepted" && (
              <>
                <select className="select" style={{ width: 130 }} value={mode} onChange={(e) => setMode(e.target.value as "hint" | "detail")}>
                  <option value="hint">提示模式</option>
                  <option value="detail">详细解析</option>
                </select>
                <button className="btn" onClick={() => void diagnose()} disabled={busy}>AI 错误诊断</button>
              </>
            )}
          </div>
          {notice && <div className="small mt-8" style={{ color: "var(--text-2)" }}>{notice}</div>}

          {judge && (
            <div className="card mt-16" style={{ background: "#f8fafd" }}>
              <div className="row wrap mb-8">
                <span className={`badge ${verdictClass(judge.verdict)}`}>
                  {verdictLabel(judge.verdict)}
                </span>
                <span className="badge gray">通过 {judge.passed_tests}/{judge.total_tests}</span>
                <span className="badge gray">耗时 {judge.runtime_ms}ms</span>
                {finalScore != null && <span className="badge purple">得分 {finalScore.toFixed(1)}</span>}
              </div>
              {judge.error_message && <div className="small mb-8" style={{ color: "var(--danger)" }}>{judge.error_message}</div>}
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>测试点</th>
                      <th>结果</th>
                      <th>输入</th>
                      <th>期望输出</th>
                      <th>实际输出</th>
                    </tr>
                  </thead>
                  <tbody>
                    {judge.judge_report.map((t, i) => (
                      <tr key={t.test_id ?? t.id ?? i}>
                        <td className="small">{t.name}</td>
                        <td><span className={`badge ${t.passed ? "green" : "red"}`}>{t.passed ? "通过" : "未通过"}</span></td>
                        <td className="mono small">{t.input || "—"}</td>
                        <td className="mono small">{t.expected || "—"}</td>
                        <td className={`mono small ${t.passed ? "" : "judge-diff"}`}>
                          <div>{t.actual || "—"}</div>
                          {!t.passed && t.message && <div className="muted" style={{ fontSize: 11 }}>{t.message}</div>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {diagnosis && (
            <div className="card mt-16">
              <div className="card-title">
                <h3>AI 错误诊断（{diagnosis.mode === "hint" ? "提示模式" : "详细解析"}）</h3>
                <span className="badge orange">基于知识库</span>
              </div>
              <h3>错误原因</h3>
              <p className="small">{diagnosis.error_reason}</p>
              {diagnosis.line_anchors && diagnosis.line_anchors.length > 0 && (
                <>
                  <h3>代码行定位</h3>
                  {diagnosis.line_anchors.map((a) => (
                    <div key={a.line} className="small" style={{ padding: "4px 0" }}>
                      <span className="badge red">第 {a.line} 行</span> {a.note}
                    </div>
                  ))}
                </>
              )}
              <div className="row wrap">
                {diagnosis.knowledge_points.map((k) => <span key={k} className="badge">{k}</span>)}
              </div>
              <h3>分析思路</h3>
              {diagnosis.thinking.map((t, i) => <div key={i} className="small" style={{ padding: "3px 0" }}>{i + 1}. {t}</div>)}
              <h3>学习建议</h3>
              {diagnosis.advice.map((a, i) => <div key={i} className="small" style={{ padding: "3px 0" }}>• {a}</div>)}
              {diagnosis.suggestion && <div className="small muted mt-8" style={{ color: "var(--warning)" }}>💡 {diagnosis.suggestion}</div>}
            </div>
          )}
        </>
      ) : (
        <>
          <textarea
            className="textarea"
            style={{ minHeight: 150 }}
            placeholder={question.qtype === "report" ? "粘贴实验报告内容…" : "输入你的答案…"}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          <div className="row mt-8">
            <button className="btn btn-primary" onClick={() => void submitSubjective()} disabled={busy}>
              {busy ? "提交中…" : "提交答案"}
            </button>
          </div>
          {notice && <div className="small mt-8" style={{ color: "var(--text-2)" }}>{notice}</div>}
          {result?.subjective && (
            <div className="card mt-16" style={{ background: "#f8fafd" }}>
              <div className="row wrap mb-8">
                {result.subjective.ai_suggestion_score != null && (
                  <span className="badge orange">AI 建议 {result.subjective.ai_suggestion_score} 分（仅供参考）</span>
                )}
                {result.subjective.teacher_score != null ? (
                  <span className="badge green">教师确认成绩：{result.subjective.teacher_score} 分</span>
                ) : (
                  <span className="badge gray">正式成绩待教师确认</span>
                )}
              </div>
              {result.subjective.teacher_comment && (
                <div className="small mb-8"><b>教师评语：</b>{result.subjective.teacher_comment}</div>
              )}
              {result.subjective.ai_improvement && (
                <div className="small"><b>改进建议：</b>{result.subjective.ai_improvement}</div>
              )}
            </div>
          )}
        </>
      )}
    </Card>
  );
}

export default function StudentAssignmentDetail() {
  const { id } = useParams();
  const assignment = useAsync<Assignment>(() => api.get<Assignment>(`/assignments/${id}`), [id]);
  const submissions = useAsync<MySubmission[]>(() => api.get("/me/submissions"), []);
  const [activeQuestion, setActiveQuestion] = useState<number | null>(null);

  if (assignment.loading || submissions.loading) return <Loading />;
  const a = assignment.data;
  if (!a) return <EmptyState text="作业不存在" />;
  const active = activeQuestion ?? a.questions[0]?.id;
  const q = a.questions.find((x) => x.id === active) ?? a.questions[0];
  if (!q) return <EmptyState text="作业没有题目" />;
  const sub = submissions.data?.find((s) => s.question_id === q.id);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{a.title}</h1>
          <p>{a.course_name} · 截止 {new Date(a.due_at).toLocaleString("zh-CN")}</p>
        </div>
        <Link to="/student/assignments" className="btn">← 返回作业中心</Link>
      </div>
      <Tabs
        items={a.questions.map((qq) => ({
          key: String(qq.id),
          label: `${qq.qtype === "programming" ? "编程" : qq.qtype === "report" ? "实验" : "简答"} · ${qq.title.slice(0, 10)}`,
        }))}
        active={String(active)}
        onChange={(k) => setActiveQuestion(Number(k))}
      />
      <QuestionView key={q.id} assignmentId={a.id} courseId={a.course_id} question={q} submission={sub} />
    </div>
  );
}


