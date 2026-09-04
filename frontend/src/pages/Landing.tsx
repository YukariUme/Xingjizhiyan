/** 平台首页：以“工作模式”为入口，突出教学—学习—研究一体化。 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { AuthModal } from "../components/AuthModal";
import { MODE_META, allowedModes, type Mode } from "../modes";
import type { Activity } from "../types";

const ENTRIES: Array<{
  mode: Mode;
  title: string;
  desc: string;
  features: string[];
  color: string;
}> = [
  {
    mode: "teaching",
    title: "教学 · 助教",
    desc: "AI 教学设计、教学诊断与课程知识空间，让教师围绕课程精准施教。",
    features: ["AI 教学设计", "教学诊断", "作业与实验", "课程知识空间"],
    color: "teacher",
  },
  {
    mode: "learning",
    title: "学习 · 助学",
    desc: "以课程为单位的预习、讲堂、作业、复习、模拟与个性化提升闭环。",
    features: ["课程学习空间", "AI 课程讲堂", "作业与实验", "复习与模拟"],
    color: "student",
  },
  {
    mode: "research",
    title: "研究 · 助研",
    desc: "本科生、研究生、教师通用的论文阅读、对比与前沿探索空间。",
    features: ["论文阅读", "论文对比", "前沿探索", "课程↔科研互跳"],
    color: "research",
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const { user, switchRole } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);
  const [activities, setActivities] = useState<Activity[]>([]);

  useEffect(() => {
    api
      .get<Activity[]>("/activities?limit=8")
      .then(setActivities)
      .catch(() => setActivities([]));
  }, []);

  const enter = (mode: Mode) => {
    const target = MODE_META[mode].home;
    if (!user) {
      void switchRole(MODE_META[mode].demoUser as "teacher").then(() => navigate(target));
      return;
    }
    if (allowedModes(user).includes(mode)) {
      navigate(target);
    } else {
      window.alert(`当前身份（${user.display_name}）无法进入「${MODE_META[mode].label}」模式`);
    }
  };

  return (
    <div className="landing" style={{ position: "relative" }}>
      <div style={{ position: "absolute", top: 18, right: 24, zIndex: 10 }}>
        {user ? (
          <button className="btn" onClick={() => navigate(MODE_META[allowedModes(user)[0] ?? "learning"].home)}>
            {user.display_name} · 进入平台 →
          </button>
        ) : (
          <button className="btn" onClick={() => setAuthOpen(true)}>
            账号登录 / 注册
          </button>
        )}
      </div>
      <div className="hero">
        <span className="kicker">面向高校计算机学科的垂类大模型创新应用</span>
        <h1>星计知研 · 教学研一体化智能平台</h1>
        <p>
          让每一门计算机课程拥有自己的 AI 学习与教学空间：课程知识空间为底座，
          教学、学习、研究共享同一个专业知识底座，形成完整闭环。
        </p>
      </div>

      <div className="entry-grid">
        {ENTRIES.map((e) => (
          <div key={e.mode} className="entry-card" onClick={() => enter(e.mode)}>
            <div className={`icon ${e.color}`}>{MODE_META[e.mode].icon}</div>
            <h3>{e.title}</h3>
            <p>{e.desc}</p>
            <div className="features">
              {e.features.map((f) => (
                <span key={f} className="tag">
                  {f}
                </span>
              ))}
            </div>
            <div style={{ marginTop: 16, color: "var(--primary)", fontWeight: 600, fontSize: 13 }}>
              {user && allowedModes(user).includes(e.mode)
                ? `进入${MODE_META[e.mode].label}模式 →`
                : user
                  ? "当前身份不可进入"
                  : "点击进入 →"}
            </div>
          </div>
        ))}
      </div>

      <div className="flow-line">
        <div className="steps">
          {["教学", "学习", "学习数据", "学情分析", "知识巩固", "科研探索"].map((s, i) => (
            <div key={s} style={{ display: "contents" }}>
              <span className="step">{s}</span>
              {i < 5 && <span className="arrow">→</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="flow-line">
        <div className="card">
          <div className="card-title">
            <h3>平台最近动态</h3>
            <button className="btn btn-sm" onClick={() => navigate("/role")}>
              立即体验 →
            </button>
          </div>
          {activities.length === 0 ? (
            <div className="muted small">暂无动态</div>
          ) : (
            activities.map((a) => (
              <div key={a.id} className="row space-between" style={{ padding: "7px 0", borderBottom: "1px solid var(--border)" }}>
                <span>{a.title}</span>
                <span className="small muted">
                  {{ teacher: "教师", student: "学生", researcher: "科研" }[a.role] ?? a.role}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
    </div>
  );
}

