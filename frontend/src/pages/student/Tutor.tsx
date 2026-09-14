/** AI 学科导师：提示/详细模式，附带知识点与来源引用。 */

import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import { ChatPanel } from "../../components/ChatPanel";
import { Card, useAsync } from "../../components/ui";
import type { ChatHistoryItem, StudentProfile } from "../../types";

const SCOPES = [
  { key: "official", label: "课程官方资料" },
  { key: "shared", label: "教师审核/共享资料" },
  { key: "personal", label: "我的个人资料" },
  { key: "extended", label: "扩展知识" },
];

function suggestMode(profile: StudentProfile | null, history: ChatHistoryItem[]): "hint" | "detail" {
  const repeatedTopicCount = history.reduce<Record<string, number>>((acc, item) => {
    (item.knowledge_points ?? []).forEach((point) => {
      acc[point] = (acc[point] ?? 0) + 1;
    });
    return acc;
  }, {});
  const repeatedCount = Math.max(0, ...Object.values(repeatedTopicCount));
  if (!profile) return "hint";
  if (profile.avg_mastery < 65) return "hint";
  if (profile.weak_points.length >= 3) return "hint";
  if (repeatedCount >= 2) return "hint";
  if (history.length < 3) return "hint";
  return "detail";
}

export default function StudentTutor() {
  const history = useAsync<ChatHistoryItem[]>(() => api.get("/learning/history?agent_type=learning"));
  const profile = useAsync<StudentProfile>(() => api.get("/analytics/me"));
  const courses = useAsync<Array<{ id: number; name: string }>>(() => api.get("/curriculum/courses"));
  const [mode, setMode] = useState<"hint" | "detail">("hint");
  const [modeTouched, setModeTouched] = useState(false);
  const [courseId, setCourseId] = useState<number | undefined>(undefined);
  const [scope, setScope] = useState("official");
  const [historyVersion, setHistoryVersion] = useState(0);

  const repeatedTopicCount = useMemo(() => {
    return (history.data ?? []).reduce<Record<string, number>>((acc, item) => {
      (item.knowledge_points ?? []).forEach((point) => {
        acc[point] = (acc[point] ?? 0) + 1;
      });
      return acc;
    }, {});
  }, [history.data]);
  const topRepeatedTopic = Object.entries(repeatedTopicCount).sort((a, b) => b[1] - a[1])[0];

  useEffect(() => {
    if (!modeTouched) {
      setMode(suggestMode(profile.data, history.data ?? []));
    }
  }, [profile.data, history.data, modeTouched]);

  useEffect(() => {
    if (courseId === undefined && (courses.data?.length ?? 0) === 1) {
      setCourseId(courses.data?.[0].id);
    }
  }, [courses.data, courseId]);

  const clearHistory = async () => {
    if (!window.confirm("确认清空 AI 学科导师的全部对话历史？")) return;
    try {
      await api.delete("/learning/history");
      history.refresh();
      setHistoryVersion((v) => v + 1);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "清空失败");
    }
  };

  const profileHint = profile.data
    ? profile.data.avg_mastery < 65
      ? "系统建议先用提示模式，把最近的薄弱点拆开问。"
      : topRepeatedTopic && topRepeatedTopic[1] >= 2
        ? `系统判断你最近反复问「${topRepeatedTopic[0]}」，先从提示模式拆解卡点更合适。`
        : "系统建议可以直接切到详细解析，追求更完整的理解。"
    : "系统会根据你的学习画像自动调整默认模式。";

  return (
    <div className="page" style={{ maxWidth: 880 }}>
      <div className="page-header">
        <div>
          <h1>AI 学科导师</h1>
          <p>计算机专业问题答疑：提示模式引导思考，详细模式逐步解析；回答附带知识点与来源引用</p>
        </div>
        <div className="role-switch">
          <button className={mode === "hint" ? "active" : ""} onClick={() => { setMode("hint"); setModeTouched(true); }}>提示模式</button>
          <button className={mode === "detail" ? "active" : ""} onClick={() => { setMode("detail"); setModeTouched(true); }}>详细解析</button>
        </div>
        <button className="btn btn-sm" onClick={() => void clearHistory()}>清空历史</button>
      </div>
      <div className="card mb-16">
        <div className="row wrap" style={{ gap: 8 }}>
          <select className="select" style={{ width: 230 }} value={courseId ?? ""} onChange={(e) => setCourseId(e.target.value ? Number(e.target.value) : undefined)}>
            <option value="">不限课程（全局）</option>
            {(courses.data ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <select className="select" style={{ width: 210 }} value={scope} onChange={(e) => setScope(e.target.value)}>
            {SCOPES.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
          <span className="small muted">回答将优先使用所选范围的课程知识空间</span>
        </div>
      </div>
      <div className="card mb-16">
        <div className="small muted">{profileHint} 目前已保存 {history.data?.length ?? 0} 条历史对话。</div>
      </div>
      <div className="card">
        <ChatPanel
          key={historyVersion}
          agent="learning"
          initialHistory={history.data ?? []}
          extraPayload={{ mode, course_id: courseId, scope, recent_topic: topRepeatedTopic?.[0] ?? "" }}
          placeholder="例如：如何理解动态规划的状态转移方程？"
          presets={[
            "为什么生产者和消费者都需要使用信号量？",
            "P/V 操作顺序颠倒会发生什么？",
            "死锁产生的四个必要条件是什么？",
            "进程和线程的区别是什么？",
          ]}
        />
      </div>
      <p className="small muted mt-8">
        💡 提示模式不会直接给出完整答案，鼓励先自主思考；AI 的回答可追溯至知识库讲义来源。
      </p>
    </div>
  );
}