/** 全局 AI 导师：右下角悬浮球，点击展开对话面板，支持语音输入与朗读。 */

import { useEffect, useRef, useState } from "react";
import { api } from "../api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  references?: string[];
}

function pickZhVoice(): SpeechSynthesisVoice | null {
  if (!("speechSynthesis" in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  return (
    voices.find((v) => v.lang?.toLowerCase() === "zh-cn") ??
    voices.find((v) => v.lang?.toLowerCase().startsWith("zh")) ??
    null
  );
}

export default function TutorBall() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);
  const [speakingKey, setSpeakingKey] = useState<number | null>(null);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (open && "speechSynthesis" in window) {
      window.speechSynthesis.getVoices();
    }
  }, [open]);

  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, open]);

  const send = async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.post<{ answer: string; references?: string[] }>("/learning/tutor", {
        message: msg,
        mode: "detail",
        history: messages.slice(-6).map((m) => ({ role: m.role, content: m.content })),
      });
      setMessages((m) => [...m, { role: "assistant", content: res.answer, references: res.references ?? [] }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: e instanceof Error ? e.message : "回答失败，请稍后重试。" },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const startVoice = () => {
    const SR = (window as unknown as { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown });
    const Ctor = (SR.SpeechRecognition ?? SR.webkitSpeechRecognition) as
      | (new () => {
          lang: string;
          interimResults: boolean;
          maxAlternatives: number;
          start: () => void;
          onresult: ((e: { results: Array<Array<{ transcript: string }>> }) => void) | null;
          onerror: (() => void) | null;
          onend: (() => void) | null;
        })
      | undefined;
    if (!Ctor) {
      setInput((v) => (v ? v : "（当前浏览器不支持语音输入，请直接输入文字）"));
      return;
    }
    const rec = new Ctor();
    rec.lang = "zh-CN";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    setListening(true);
    rec.onresult = (e) => {
      const t = e.results?.[0]?.[0]?.transcript ?? "";
      if (t) setInput(t);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    rec.start();
  };

  useEffect(() => {
    return () => {
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    };
  }, []);

  const toggleSpeak = (text: string, key: number) => {
    if (!("speechSynthesis" in window)) return;
    if (speakingKey === key) {
      window.speechSynthesis.cancel();
      setSpeakingKey(null);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "zh-CN";
    const voice = pickZhVoice();
    if (voice) utterance.voice = voice;
    utterance.onend = () => setSpeakingKey((k) => (k === key ? null : k));
    setSpeakingKey(key);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="tutor-ball-root">
      {open && (
        <div className="tutor-panel">
          <div className="tutor-panel-head">
            <div className="row">
              <span className="tutor-orb">🤖</span>
              <div>
                <b>AI 学科导师</b>
                <div className="small muted">随时问我，支持语音</div>
              </div>
            </div>
            <button className="close-btn" onClick={() => setOpen(false)}>✕</button>
          </div>

          <div className="tutor-body" ref={bodyRef}>
            {messages.length === 0 ? (
              <div className="tutor-welcome">
                <div className="emoji">🧑‍🏫</div>
                <div className="small muted">有问题直接问我，也可以点麦克风用语音输入。</div>
              </div>
            ) : (
              messages.map((m, i) => (
                <div key={i} className={`tutor-msg ${m.role}`}>
                  <p>{m.content}</p>
                  {m.role === "assistant" && m.references?.length ? (
                    <div className="tutor-refs">
                      <span className="small muted">参考来源：</span>
                      {m.references.map((r, j) => (
                        <span key={j} className="badge gray">{r}</span>
                      ))}
                    </div>
                  ) : null}
                  {m.role === "assistant" && (
                    <button className="tutor-speak" onClick={() => toggleSpeak(m.content, i)} title={speakingKey === i ? "停止播放" : "朗读"}>
                      {speakingKey === i ? "⏹" : "🔊"}
                    </button>
                  )}
                </div>
              ))
            )}
            {busy && <div className="small muted tutor-typing">正在思考…</div>}
          </div>

          <div className="tutor-input">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入你的问题…"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <button className={`tutor-mic ${listening ? "listening" : ""}`} onClick={startVoice} title="语音输入">
              {listening ? "●" : "🎤"}
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => void send()} disabled={busy || !input.trim()}>
              发送
            </button>
          </div>
        </div>
      )}

      <button className="tutor-ball" onClick={() => setOpen((v) => !v)} title={open ? "收起 AI 导师" : "打开 AI 导师"}>
        <span className="tutor-ball-emoji">🤖</span>
        <span className="tutor-ball-pulse" aria-hidden="true" />
      </button>
    </div>
  );
}
