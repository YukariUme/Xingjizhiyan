/** 题库管理：教师按课程维护多题型题目（单选/多选/判断/简答/代码/SQL/综合分析）。 */

import { useState } from "react";
import { api } from "../../api";
import { Card, EmptyState, ErrorBanner, Loading, Modal, useAsync } from "../../components/ui";
import type { Course } from "../../types";

type BankQuestion = {
  id: number;
  qtype: string;
  title: string;
  options: string[];
  answer: Record<string, unknown>;
  analysis: string;
  knowledge_point_ids: number[];
  max_score: number;
};

const QTYPES = [
  ["single", "单选"],
  ["multiple", "多选"],
  ["judge", "判断"],
  ["short", "简答"],
  ["code", "代码"],
  ["sql", "SQL"],
  ["analysis", "综合分析"],
] as const;

const QTYPE_LABEL: Record<string, string> = Object.fromEntries(QTYPES);

export default function TeacherQuestionBank() {
  const courses = useAsync<Course[]>(() => api.get("/courses"));
  const [courseId, setCourseId] = useState<number | null>(null);
  const questions = useAsync<BankQuestion[]>(
    () => (courseId ? api.get(`/curriculum/question-bank?course_id=${courseId}`) : Promise.resolve([])),
    [courseId],
  );
  const [editing, setEditing] = useState<Partial<BankQuestion> | null>(null);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const save = async () => {
    if (!courseId || !editing?.title?.trim()) {
      setErr("请填写题目");
      return;
    }
    setSaving(true);
    setErr("");
    try {
      const payload = {
        course_id: courseId,
        qtype: editing.qtype ?? "single",
        title: editing.title,
        options: (editing.options ?? []).filter(Boolean),
        answer: editing.answer ?? {},
        analysis: editing.analysis ?? "",
        knowledge_point_ids: editing.knowledge_point_ids ?? [],
        max_score: Number(editing.max_score ?? 5),
      };
      if (editing.id) {
        await api.put(`/curriculum/question-bank/${editing.id}`, payload);
      } else {
        await api.post("/curriculum/question-bank", payload);
      }
      setEditing(null);
      questions.refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (q: BankQuestion) => {
    if (!window.confirm(`确认删除题目《${q.title.slice(0, 30)}》？`)) return;
    await api.delete(`/curriculum/question-bank/${q.id}`);
    questions.refresh();
  };

  if (courses.loading) return <Loading />;
  if (courses.error) return <ErrorBanner message={courses.error} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>题库管理</h1>
          <p>按课程维护单选/多选/判断/简答/代码/SQL/综合分析题目，章节测验、模拟考试与错题重测共用题库</p>
        </div>
        <select
          className="select"
          style={{ width: 240 }}
          value={courseId ?? ""}
          onChange={(e) => setCourseId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">选择课程…</option>
          {(courses.data ?? []).map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <button className="btn btn-primary" disabled={!courseId} onClick={() => setEditing({ qtype: "single", options: [], max_score: 5 })}>
          ＋ 建题
        </button>
      </div>
      {err && <div className="badge red mb-16">{err}</div>}

      {!courseId ? (
        <EmptyState text="请先选择课程" />
      ) : questions.loading ? (
        <Loading />
      ) : !questions.data || questions.data.length === 0 ? (
        <EmptyState text="题库为空，点击“＋ 建题”添加第一道题" />
      ) : (
        <div className="grid">
          {questions.data.map((q) => (
            <Card
              key={q.id}
              title={`${q.title}（${QTYPE_LABEL[q.qtype] ?? q.qtype} · ${q.max_score}分）`}
              extra={
                <div className="row">
                  <button className="btn btn-sm" onClick={() => setEditing(q)}>编辑</button>
                  <button className="btn btn-sm btn-danger" onClick={() => void remove(q)}>删除</button>
                </div>
              }
            >
              <p className="small muted">{q.analysis}</p>
              {q.options.length > 0 && (
                <div className="row wrap mt-8">
                  {q.options.map((o, i) => (
                    <span key={i} className="badge gray">{o}</span>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      <Modal
        title={editing?.id ? "编辑题目" : "新建题目"}
        open={!!editing}
        onClose={() => setEditing(null)}
        footer={
          <>
            <button className="btn" onClick={() => setEditing(null)}>取消</button>
            <button className="btn btn-primary" onClick={() => void save()} disabled={saving}>
              {saving ? "保存中…" : "保存"}
            </button>
          </>
        }
      >
        {editing && (
          <div className="grid">
            <div className="field">
              <label>题型</label>
              <select className="select" value={editing.qtype} onChange={(e) => setEditing({ ...editing, qtype: e.target.value })}>
                {QTYPES.map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>题干</label>
              <textarea className="textarea" value={editing.title ?? ""} onChange={(e) => setEditing({ ...editing, title: e.target.value })} />
            </div>
            <div className="field">
              <label>选项（每行一个，可留空）</label>
              <textarea
                className="textarea"
                value={(editing.options ?? []).join("\n")}
                onChange={(e) => setEditing({ ...editing, options: e.target.value.split("\n") })}
              />
            </div>
            <div className="field">
              <label>答案（JSON，如 {"{"}"index": 0{"}"} / {"{"}"value": true{"}"} / {"{"}"text": "..."{"}"}）</label>
              <input className="input" value={JSON.stringify(editing.answer ?? {})} onChange={(e) => {
                try {
                  setEditing({ ...editing, answer: JSON.parse(e.target.value) });
                } catch {
                  /* 输入中 */
                }
              }} />
            </div>
            <div className="field">
              <label>解析</label>
              <textarea className="textarea" value={editing.analysis ?? ""} onChange={(e) => setEditing({ ...editing, analysis: e.target.value })} />
            </div>
            <div className="field">
              <label>分值</label>
              <input className="input" type="number" value={editing.max_score ?? 5} onChange={(e) => setEditing({ ...editing, max_score: Number(e.target.value) })} />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
