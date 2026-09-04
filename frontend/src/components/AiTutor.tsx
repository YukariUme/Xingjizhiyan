/** AI 助教：替代教师授课——从零细讲 + 追问，可多选课程资料并定义主/背景资料。 */

import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { ChatPanel } from "./ChatPanel";
import { Card } from "./ui";

interface Doc {
  id: number;
  title: string;
  type: string;
  source: string;
}

interface ChapterOpt {
  key: string;
  label: string;
}

export default function AiTutor({
  courseId,
  courseName,
  chapters,
}: {
  courseId: number;
  courseName: string;
  chapters: ChapterOpt[];
}) {
  const [chapterId, setChapterId] = useState("");
  const [style, setStyle] = useState<"hint" | "deep">("deep");
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [primaryId, setPrimaryId] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .get<Doc[]>(`/knowledge/documents?course=${encodeURIComponent(courseName)}`)
      .then((d) => alive && setDocs(d))
      .catch(() => alive && setDocs([]));
    return () => {
      alive = false;
    };
  }, [courseName]);

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        if (primaryId === id) setPrimaryId(null);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const setPrimary = (id: number) => {
    setPrimaryId(id);
    setSelected((prev) => new Set([...prev, id]));
  };

  const secondaryIds = useMemo(
    () => [...selected].filter((id) => id !== primaryId),
    [selected, primaryId]
  );

  return (
    <div className="grid">
      <Card title="选择本次授课资料（可多选）">
        <p className="small muted">
          勾选要使用的资料，并指定一份<b>主资料</b>（本次讲解主要围绕它）；其余勾选项作为<b>背景资料</b>补充上下文。
        </p>
        {docs.length === 0 ? (
          <div className="small muted">该课程暂无资料，请先到「课程资料」上传 PPT/教材。</div>
        ) : (
          <div className="grid mt-8">
            {docs.map((d) => (
              <div key={d.id} className="row space-between" style={{ padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
                <label className="row" style={{ gap: 8, cursor: "pointer", flex: 1 }}>
                  <input type="checkbox" checked={selected.has(d.id)} onChange={() => toggle(d.id)} />
                  <span>
                    <b>{d.title}</b>
                    <span className="small muted"> · {d.type} · {d.source}</span>
                  </span>
                </label>
                <button
                  className={`btn btn-sm ${primaryId === d.id ? "btn-primary" : ""}`}
                  onClick={() => setPrimary(d.id)}
                  disabled={!selected.has(d.id)}
                >
                  {primaryId === d.id ? "● 主资料" : "设为主资料"}
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="row wrap mt-8" style={{ gap: 8 }}>
          <select className="select" style={{ width: 260 }} value={chapterId} onChange={(e) => setChapterId(e.target.value)}>
            <option value="">不限章节（全局讲解）</option>
            {chapters.map((c) => (
              <option key={c.key} value={c.key}>{c.label}</option>
            ))}
          </select>
          <span className="small muted">默认从零开始细讲，适合没听清课堂的学生</span>
        </div>
      </Card>

      <Card
        title="与 AI 助教对话"
        extra={
          <div className="role-switch" role="group" aria-label="回答风格">
            <button className={style === "hint" ? "active" : ""} onClick={() => setStyle("hint")}>
              提示模式
            </button>
            <button className={style === "deep" ? "active" : ""} onClick={() => setStyle("deep")}>
              深度回答
            </button>
          </div>
        }
      >
        <ChatPanel
          agent="learning"
          extraPayload={{
            mode: style,
            teaching: style === "deep",
            course_id: courseId,
            chapter_id: chapterId ? Number(chapterId) : undefined,
            primary_document_ids: primaryId ? [primaryId] : [],
            secondary_document_ids: secondaryIds,
            scope: "official",
          }}
          presets={[
            "请从零开始讲这个知识点",
            "这个知识点为什么重要？",
            "举一个具体例子并逐步解释",
            "我还没听懂，换个方式再讲一遍",
          ]}
        />
      </Card>
    </div>
  );
}
