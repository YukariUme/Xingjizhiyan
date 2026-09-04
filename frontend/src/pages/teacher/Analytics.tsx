/** 班级学情分析：正确率、高频错误、能力分布与薄弱点。 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { BarChart, Donut } from "../../components/charts";
import { Card, EmptyState, Loading, StatCard, useAsync } from "../../components/ui";
import { AiLabel, ReferenceList } from "../../components/AiMeta";
import type { ClassAnalytics, Course } from "../../types";

export default function TeacherAnalytics() {
  const navigate = useNavigate();
  const courses = useAsync<Course[]>(() => api.get("/courses"));
  const [courseId, setCourseId] = useState<number | null>(null);
  const effectiveId = courseId ?? courses.data?.[0]?.id;
  const analytics = useAsync<ClassAnalytics | null>(
    () => (effectiveId ? api.get(`/analytics/courses/${effectiveId}`) : Promise.resolve(null)),
    [effectiveId]
  );
  const [diagnosis, setDiagnosis] = useState<{
    findings: Array<{ issue: string; evidence: string; reason: string }>;
    suggestions: Array<{ title: string; detail: string }>;
    next_lesson: string[];
    materials: string[];
    provider?: string;
    references?: Array<{ title: string; source: string; source_level: string; page: string }>;
  } | null>(null);
  const [diagBusy, setDiagBusy] = useState(false);

  const runDiagnosis = async () => {
    if (!effectiveId) return;
    setDiagBusy(true);
    try {
      const res = await api.post<{ diagnosis: typeof diagnosis }>(`/analytics/courses/${effectiveId}/diagnose`, {});
      setDiagnosis(res.diagnosis);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "诊断失败");
    } finally {
      setDiagBusy(false);
    }
  };

  const adopt = () => {
    if (!diagnosis || !acc) return;
    const text = diagnosis.suggestions.map((s) => s.title).join("；");
    navigate(`/teach/design?course=${encodeURIComponent(acc.course_name)}&suggestion=${encodeURIComponent(text)}`);
  };

  if (courses.loading) return <Loading />;
  const acc = analytics.data;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>班级学情分析</h1>
          <p>基于编程评测与批改结果，自动识别班级薄弱知识点，反哺教学调整</p>
        </div>
        <select className="select" style={{ width: 200 }} value={effectiveId ?? ""}
          onChange={(e) => setCourseId(Number(e.target.value))}>
          {courses.data?.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {analytics.loading ? (
        <Loading />
      ) : !acc ? (
        <EmptyState text="暂无学情数据" />
      ) : (
        <>
          <div className="grid grid-4 mb-16">
            <StatCard label="班级人数" value={acc.total_students} />
            <StatCard label="提交总数" value={acc.submission_count} hint={`${acc.assignment_count} 份作业`} />
            <StatCard label="平均正确率" value={`${acc.avg_accuracy}%`} color={acc.avg_accuracy >= 70 ? "var(--success)" : "var(--warning)"} />
            <StatCard label="已批改" value={`${acc.graded_count}`} />
          </div>

          <div className="grid grid-2 mb-16">
            <Card title="各知识点正确率">
              {acc.knowledge_accuracy.length === 0 ? (
                <EmptyState text="暂无知识点评测数据" />
              ) : (
                <BarChart
                  data={acc.knowledge_accuracy.map((k) => ({ label: k.name, value: k.accuracy }))}
                  height={220}
                />
              )}
            </Card>
            <Card title="学生能力分布">
              <Donut
                data={acc.ability_distribution.map((d) => ({
                  label: d.band,
                  value: d.count,
                  color:
                    d.band === "90-100"
                      ? "#0f9d6e"
                      : d.band === "80-89"
                        ? "#3aa06d"
                        : d.band === "70-79"
                          ? "#f5a524"
                          : d.band === "60-69"
                            ? "#e8763a"
                            : "#e5484d",
                }))}
              />
            </Card>
          </div>

          <div className="grid grid-2">
            <Card title="高频错误知识点（需要重点讲解）">
              {acc.high_frequency_errors.length === 0 ? (
                <EmptyState text="暂无高频错误" />
              ) : (
                acc.high_frequency_errors.map((k, i) => (
                  <div key={k.knowledge_point_id} className="row space-between" style={{ padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
                    <div className="row">
                      <span className="badge red">#{i + 1}</span>
                      <div>
                        <b>{k.name}</b>
                        <div className="small muted">{k.attempts} 次作答 · 正确率 {k.accuracy}%</div>
                      </div>
                    </div>
                    <span className="badge orange">建议重点讲解</span>
                  </div>
                ))
              )}
            </Card>
            <Card title="班级薄弱知识点清单">
              {acc.weak_points.length === 0 ? (
                <div className="badge green">班级无明显薄弱点</div>
              ) : (
                acc.weak_points.map((w) => (
                  <div key={w} className="row" style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                    <span className="badge red">薄弱</span>
                    <b>{w}</b>
                  </div>
                ))
              )}
              <p className="small muted mt-8">
                教学建议：针对薄弱知识点调整下节课重点、布置专项练习，并在下一轮作业中复测。
              </p>
            </Card>
          </div>

          <Card
            className="mt-16"
            title="AI 教学诊断（数据 → 诊断 → 教学建议）"
            extra={<button className="btn btn-primary" onClick={() => void runDiagnosis()} disabled={diagBusy}>{diagBusy ? "诊断中…" : "生成诊断"}</button>}
          >
            {!diagnosis ? (
              <div className="empty">
                <div className="emoji">🧑‍⚕️</div>
                <div>点击“生成诊断”，AI 将基于班级学情回答：哪里有问题？为什么？建议怎么调整？</div>
              </div>
            ) : (
              <div className="grid grid-2">
                <div>
                  <h3>发现的问题</h3>
                  {diagnosis.findings.map((f, i) => (
                    <div key={i} className="small" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                      <b>{f.issue}</b>
                      <div className="muted">证据：{f.evidence}</div>
                      <div className="muted">可能原因：{f.reason}</div>
                    </div>
                  ))}
                </div>
                <div>
                  <h3>教学建议</h3>
                  {diagnosis.suggestions.map((s, i) => (
                    <div key={i} className="small" style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                      <b>{s.title}</b>
                      <div className="muted">{s.detail}</div>
                    </div>
                  ))}
                  <h3>下一节课重点</h3>
                  {diagnosis.next_lesson.map((n, i) => <span key={i} className="badge red" style={{ margin: "0 6px 6px 0" }}>{n}</span>)}
                  <h3>推荐材料</h3>
                  {diagnosis.materials.map((m, i) => <span key={i} className="badge gray" style={{ margin: "0 6px 6px 0" }}>{m}</span>)}
                  <button className="btn btn-primary mt-16" onClick={adopt}>采用建议 → AI 教学设计</button>
                  <div className="mt-16">
                    <AiLabel provider={diagnosis.provider} />
                    <ReferenceList references={diagnosis.references} />
                  </div>
                </div>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
