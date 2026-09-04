/** 作业管理：列表 + 新建作业（编程题 / 简答题 / 实验报告）。 */

import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { Card, EmptyState, Loading, Modal, useAsync } from "../../components/ui";
import type { Assignment, Course } from "../../types";

interface QuestionForm {
  qtype: string;
  title: string;
  description: string;
  language: string;
  code_template: string;
  max_score: number;
  test_cases: Array<{
    id: number;
    name: string;
    mode: "io" | "static";
    input: string;
    output: string;
    check: string;
    value: string;
    hint: string;
  }>;
  knowledge_point_ids: number[];
}

export default function TeacherAssignments() {
  const { data, loading, setData } = useAsync<Assignment[]>(() => api.get("/assignments"));
  const courses = useAsync<Course[]>(() => api.get("/courses"));
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", course_id: 0, due_at: "" });
  const [questions, setQuestions] = useState<QuestionForm[]>([]);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const addQuestion = (qtype: string) => {
    setQuestions((q) => [
      ...q,
      {
        qtype,
        title: "",
        description: "",
        language: "python",
        code_template: "",
        max_score: 10,
        test_cases: [{ id: 1, name: "示例 1", mode: "io", input: "", output: "", check: "contains", value: "", hint: "" }],
        knowledge_point_ids: [],
      },
    ]);
  };

  const patchQuestion = (idx: number, patch: Partial<QuestionForm>) => {
    setQuestions((q) => q.map((item, i) => (i === idx ? { ...item, ...patch } : item)));
  };

  const create = async () => {
    setErr("");
    if (!form.title.trim() || !form.course_id || questions.length === 0) {
      setErr("请填写作业标题、选择课程并至少添加一道题目");
      return;
    }
    setSaving(true);
    try {
      const created = await api.post<Assignment>("/assignments", {
        ...form,
        due_at: form.due_at || new Date(Date.now() + 7 * 86400000).toISOString(),
        questions,
      });
      setData([created, ...(data ?? [])]);
      setOpen(false);
      setForm({ title: "", description: "", course_id: 0, due_at: "" });
      setQuestions([]);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "创建失败");
    } finally {
      setSaving(false);
    }
  };

  if (loading || courses.loading) return <Loading />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>作业管理</h1>
          <p>发布编程题（自动评测）、简答题（AI 建议批改 + 教师确认）与实验报告</p>
        </div>
        <button className="btn btn-primary" onClick={() => setOpen(true)}>＋ 新建作业</button>
      </div>

      {!data || data.length === 0 ? (
        <EmptyState text="还没有作业，点击右上角新建" />
      ) : (
        <div className="grid grid-2">
          {data.map((a) => (
            <Card key={a.id} title={a.title} extra={<span className="badge gray">{a.course_name}</span>}>
              <p className="small muted" style={{ minHeight: 40 }}>{a.description}</p>
              <div className="row wrap mb-8">
                {a.questions.map((q) => (
                  <span key={q.id} className={`badge ${q.qtype === "programming" ? "purple" : q.qtype === "report" ? "orange" : ""}`}>
                    {q.qtype === "programming" ? "编程" : q.qtype === "report" ? "实验" : "简答"} · {q.title.slice(0, 12)}
                  </span>
                ))}
              </div>
              <div className="row space-between">
                <div className="small muted">
                  截止 {new Date(a.due_at).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit" })} · 已提交 {a.submitted_count}/{a.student_count}
                </div>
                <Link to={`/teacher/assignments/${a.id}`} className="btn btn-sm btn-primary">查看提交</Link>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        title="新建作业"
        open={open}
        onClose={() => setOpen(false)}
        footer={
          <>
            <button className="btn" onClick={() => setOpen(false)}>取消</button>
            <button className="btn btn-primary" onClick={() => void create()} disabled={saving}>
              {saving ? "发布中…" : "发布作业"}
            </button>
          </>
        }
      >
        <div className="form-grid">
          <div className="field">
            <label>作业标题 *</label>
            <input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="如：数据结构 · 作业一" />
          </div>
          <div className="field">
            <label>所属课程 *</label>
            <select className="select" value={form.course_id} onChange={(e) => setForm({ ...form, course_id: Number(e.target.value) })}>
              <option value={0}>选择课程</option>
              {courses.data?.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>作业说明</label>
            <textarea className="textarea" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="field">
            <label>截止时间</label>
            <input type="datetime-local" className="input" value={form.due_at.slice(0, 16)} onChange={(e) => setForm({ ...form, due_at: new Date(e.target.value).toISOString() })} />
          </div>
        </div>

        <div className="row mb-8" style={{ gap: 8 }}>
          <button className="btn btn-sm" onClick={() => addQuestion("programming")}>＋ 编程题</button>
          <button className="btn btn-sm" onClick={() => addQuestion("subjective")}>＋ 简答题</button>
          <button className="btn btn-sm" onClick={() => addQuestion("report")}>＋ 实验报告</button>
        </div>

        {questions.map((q, idx) => (
          <Card key={idx} className="mb-8" title={`题目 ${idx + 1} · ${q.qtype === "programming" ? "编程题" : q.qtype === "report" ? "实验报告" : "简答题"}`}
            extra={<button className="btn btn-sm btn-danger" onClick={() => setQuestions((qs) => qs.filter((_, i) => i !== idx))}>删除</button>}
          >
            <div className="form-grid">
              <div className="field">
                <label>题目标题 *</label>
                <input className="input" value={q.title} onChange={(e) => patchQuestion(idx, { title: e.target.value })} />
              </div>
              <div className="field">
                <label>满分</label>
                <input type="number" className="input" value={q.max_score} onChange={(e) => patchQuestion(idx, { max_score: Number(e.target.value) })} />
              </div>
              <div className="field" style={{ gridColumn: "1 / -1" }}>
                <label>题目描述 *</label>
                <textarea className="textarea" value={q.description} onChange={(e) => patchQuestion(idx, { description: e.target.value })} />
              </div>
            </div>
            {q.qtype === "programming" && (
              <>
                <div className="field">
                  <label>代码模板（学生初始代码）</label>
                  <textarea className="textarea code-block" style={{ minHeight: 80, color: "#dce6f5" }} value={q.code_template}
                    onChange={(e) => patchQuestion(idx, { code_template: e.target.value })}
                    placeholder={"def solution(...):\n    # TODO\n    pass"} />
                </div>
                <div className="field">
                  <label>编程语言</label>
                  <select className="select" value={q.language} onChange={(e) => patchQuestion(idx, { language: e.target.value })}>
                    <option value="python">Python</option>
                    <option value="java">Java</option>
                    <option value="c">C</option>
                    <option value="cpp">C++</option>
                  </select>
                </div>
                <div className="field" style={{ gridColumn: "1 / -1" }}>
                  <label>测试点</label>
                  {q.test_cases.map((tc, ti) => (
                    <div key={ti} className="card mb-8" style={{ background: "#f8fafd", padding: 10 }}>
                      <div className="row wrap mb-8" style={{ gap: 6 }}>
                        <input className="input" style={{ width: 150 }} placeholder="名称" value={tc.name}
                          onChange={(e) => patchQuestion(idx, { test_cases: q.test_cases.map((t, i) => (i === ti ? { ...t, name: e.target.value } : t)) })} />
                        <select className="select" style={{ width: 140 }} value={tc.mode}
                          onChange={(e) => patchQuestion(idx, { test_cases: q.test_cases.map((t, i) => (i === ti ? { ...t, mode: e.target.value as "io" | "static" } : t)) })}>
                          <option value="io">标准输入输出</option>
                          <option value="static">静态检查</option>
                        </select>
                        <button className="btn btn-sm btn-danger" onClick={() => patchQuestion(idx, { test_cases: q.test_cases.filter((_, i) => i !== ti) })}>✕</button>
                      </div>
                      {tc.mode === "io" ? (
                        <div className="row wrap" style={{ gap: 6 }}>
                          <textarea className="textarea code-block" style={{ minHeight: 70, flex: 1 }} placeholder="标准输入（stdin）" value={tc.input}
                            onChange={(e) => patchQuestion(idx, { test_cases: q.test_cases.map((t, i) => (i === ti ? { ...t, input: e.target.value } : t)) })} />
                          <textarea className="textarea code-block" style={{ minHeight: 70, flex: 1 }} placeholder="期望输出（stdout）" value={tc.output}
                            onChange={(e) => patchQuestion(idx, { test_cases: q.test_cases.map((t, i) => (i === ti ? { ...t, output: e.target.value } : t)) })} />
                        </div>
                      ) : (
                        <div className="row wrap" style={{ gap: 6 }}>
                          <select className="select" style={{ width: 110 }} value={tc.check}
                            onChange={(e) => patchQuestion(idx, { test_cases: q.test_cases.map((t, i) => (i === ti ? { ...t, check: e.target.value } : t)) })}>
                            <option value="contains">包含</option>
                            <option value="not_contains">不包含</option>
                          </select>
                          <input className="input grow" placeholder="代码片段关键字" value={tc.value}
                            onChange={(e) => patchQuestion(idx, { test_cases: q.test_cases.map((t, i) => (i === ti ? { ...t, value: e.target.value } : t)) })} />
                          <input className="input" style={{ width: 220 }} placeholder="提示" value={tc.hint}
                            onChange={(e) => patchQuestion(idx, { test_cases: q.test_cases.map((t, i) => (i === ti ? { ...t, hint: e.target.value } : t)) })} />
                        </div>
                      )}
                    </div>
                  ))}
                  <button className="btn btn-sm" onClick={() => patchQuestion(idx, { test_cases: [...q.test_cases, { id: q.test_cases.length + 1, name: `测试点 ${q.test_cases.length + 1}`, mode: "io", input: "", output: "", check: "contains", value: "", hint: "" }] })}>
                    ＋ 测试点
                  </button>
                </div>
              </>
            )}
          </Card>
        ))}
        {err && <div className="badge red mb-8">{err}</div>}
      </Modal>
    </div>
  );
}
