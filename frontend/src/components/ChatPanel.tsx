/** AI 对话面板：消息 + 知识点标签 + 来源引用。 */

import { useState } from "react";
import { api } from "../api";
import type { ChatHistoryItem } from "../types";

export function ChatPanel({
  agent = "learning",
  initialHistory = [],
  onSend,
  placeholder = "输入你的问题，Enter 发送，Shift+Enter 换行",
  extraPayload,
  presets = [],
}: {
  agent?: string;
  initialHistory?: ChatHistoryItem[];
  onSend?: (message: string, reply: Record<string, unknown>) => void;
  placeholder?: string;
  extraPayload?: Record<string, unknown>;
  presets?: string[];
}) {
  const [messages, setMessages] = useState<ChatHistoryItem[]>(initialHistory);
  const [input, setInput] = useState("");
  const [imageData, setImageData] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const pickImage = (file: File | undefined) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setImageData(String(reader.result ?? null));
    reader.readAsDataURL(file);
  };

  const send = async (override?: string) => {
    const text = (override ?? input).trim();
    if ((!text && !imageData) || loading) return;
    if (!override) setInput("");
    const image = imageData;
    setImageData(null);
    setMessages((m) => [...m, { id: Date.now(), role: "user", content: text, knowledge_points: [], references: [], created_at: "" }]);
    setLoading(true);
    try {
      const payload =
        agent === "learning"
          ? { message: text, mode: "hint", history: messages.slice(-6).map((m) => ({ role: m.role, content: m.content })), ...extraPayload, image_base64: image ?? "" }
          : { message: text, ...extraPayload };
      const res = await api.post<Record<string, unknown>>(`/ai/assistant`, { agent, payload });
      const answer = String(res.answer || res.summary || "");
      const kps = (res.knowledge_points as string[]) || [];
      const refs = (res.references as string[]) || [];
      const grounded = res.grounded as boolean | undefined;
      setMessages((m) => [
        ...m,
        { id: Date.now(), role: "assistant", content: answer, knowledge_points: kps, references: refs, created_at: "", grounded },
      ]);
      onSend?.(text, res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "请求失败";
      setMessages((m) => [...m, { id: Date.now(), role: "assistant", content: `⚠️ ${msg}`, knowledge_points: [], references: [], created_at: "" }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="chat-box" style={{ minHeight: 260 }}>
        {messages.length === 0 && (
          <div className="empty">
            <div className="emoji">🤖</div>
            <div>开始和 AI 助手对话</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.content}
            {m.role === "assistant" && (m.knowledge_points.length > 0 || m.references.length > 0) && (
              <div className="meta">
                <div className="row" style={{ gap: 6, marginBottom: 4 }}>
                  <span className="badge purple">✦ AI 生成</span>
                  {m.grounded === true && <span className="badge green">✓ 基于知识库回答</span>}
                  {m.grounded === false && <span className="badge orange">模型自身知识（未命中知识库）</span>}
                  {m.grounded === undefined && m.references.length > 0 && <span className="badge green">✓ 基于知识库回答</span>}
                </div>
                {m.knowledge_points.length > 0 && (
                  <div>
                    <b>相关知识点：</b>
                    {m.knowledge_points.map((k) => (
                      <span key={k} className="tag" style={{ background: "#eef4ff", color: "#2f6fed" }}>
                        {k}
                      </span>
                    ))}
                  </div>
                )}
                {m.references.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    <b>来源引用：</b>
                    {m.references.map((r) => (
                      <span key={r} className="tag">
                        {r}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="msg assistant">
            <span className="spinner" /> 正在思考…
          </div>
        )}
      </div>
      {presets.length > 0 && (
        <div className="row wrap mt-8" style={{ gap: 6 }}>
          {presets.map((p) => (
            <button key={p} className="btn btn-sm" onClick={() => void send(p)}>
              {p}
            </button>
          ))}
        </div>
      )}
      <div className="chat-input mt-16">
        {imageData && (
          <div className="row" style={{ gap: 6 }}>
            <img src={imageData} alt="待发送图片" style={{ height: 64, borderRadius: 8, border: "1px solid var(--border)" }} />
            <button className="btn btn-sm" onClick={() => setImageData(null)}>移除</button>
          </div>
        )}
        <label className="btn btn-sm" style={{ cursor: "pointer" }} title="上传图片提问（教材页/PPT 截图/手写题/代码截图）">
          🖼 图片
          <input
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) => {
              pickImage(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </label>
        <textarea
          className="textarea"
          value={input}
          placeholder={placeholder}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
        />
        <button className="btn btn-primary" onClick={() => void send()} disabled={loading || (!input.trim() && !imageData)}>
          {loading ? "发送中" : "发送"}
        </button>
      </div>
    </div>
  );
}
