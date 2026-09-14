/** 应用外壳：按“工作模式”渲染侧边栏导航 + 顶栏模式切换。 */

import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { MODE_META, allowedModes, modeLabel, type Mode } from "../modes";
import { ErrorBoundary } from "./ErrorBoundary";
import { DemoEntryButton, DemoStatusBar } from "./DemoBar";
import TutorBall from "./TutorBall";

const NAV: Record<Mode, Array<{ to: string; label: string; icon: string }>> = {
  teaching: [
    { to: "/teach", label: "首页", icon: "⌂" },
    { to: "/teach/courses", label: "我的课程", icon: "▤" },
    { to: "/teach/design", label: "AI 教学设计", icon: "✎" },
    { to: "/teach/diagnostics", label: "教学诊断", icon: "◔" },
    { to: "/teach/assignments", label: "作业与实验", icon: "☰" },
    { to: "/teach/question-bank", label: "题库管理", icon: "▣" },
    { to: "/teach/knowledge", label: "课程知识空间", icon: "◫" },
    { to: "/research", label: "研究空间", icon: "🔬" },
  ],
  learning: [
    { to: "/learn", label: "首页", icon: "⌂" },
    { to: "/learn/courses", label: "我的课程", icon: "▤" },
    { to: "/learn/center", label: "学习中心", icon: "◔" },
    { to: "/research", label: "研究空间", icon: "🔬" },
  ],
  research: [
    { to: "/research", label: "科研工作台", icon: "⌂" },
    { to: "/research/papers", label: "论文阅读", icon: "▤" },
    { to: "/research/frontier", label: "前沿探索", icon: "◔" },
    { to: "/learn", label: "学习空间", icon: "📚" },
  ],
};

export function Layout() {
  const { user, switchRole, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [search, setSearch] = useState("");
  const path = location.pathname;
  const mode: Mode = path.startsWith("/teach")
    ? "teaching"
    : path.startsWith("/research")
      ? "research"
      : "learning";
  const modes = allowedModes(user);
  const aiTarget =
    mode === "teaching" ? "/teach/design" : mode === "research" ? "/research/frontier" : "/learn/tutor";
  const aiLabel = MODE_META[mode].label === "教学" ? "教学设计" : MODE_META[mode].label === "研究" ? "前沿探索" : "学科导师";

  const goSearch = () => {
    if (search.trim()) navigate(`/search?q=${encodeURIComponent(search.trim())}`);
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">
            <span className="logo-mark">星</span>
            星计知研
          </div>
          <div className="sub">{MODE_META[mode].label}模式 · 教学研一体化</div>
        </div>
        <div className="nav-group">{MODE_META[mode].label}工作区</div>
        <nav>
          {NAV[mode].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              end={item.to === MODE_META[mode].home}
            >
              <span style={{ width: 18, textAlign: "center" }}>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="foot">课程知识空间 · RAG · Agent · 学情分析</div>
      </aside>
      <div className="main">
        <DemoStatusBar />
        <header className="topbar">
          <div className="search-box">
            <span className="icon">🔍</span>
            <input
              className="input"
              placeholder="搜索知识点 / 讲义 / 论文…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && goSearch()}
            />
          </div>
          <div className="role-switch" role="group" aria-label="工作模式切换">
            {modes.map((m) => (
              <button
                key={m}
                className={m === mode ? "active" : ""}
                onClick={() => navigate(MODE_META[m].home)}
              >
                {MODE_META[m].label}
              </button>
            ))}
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => navigate(aiTarget)}>
            ✦ AI · {aiLabel}
          </button>
          <DemoEntryButton />
          <div className="user-chip" title={user?.bio ?? ""}>
            <span className={`avatar ${user?.role ?? "student"}`}>
              {(user?.display_name ?? "访客").slice(0, 1)}
            </span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.2 }}>
                {user?.display_name ?? "未登录"}
              </div>
              <div className="small muted">
                {modeLabel(user)} · {user?.title ?? ""}
              </div>
            </div>
            {user && (
              <button className="btn btn-sm" onClick={logout} title="退出登录">
                退出
              </button>
            )}
            {!user && (
              <button
                className="btn btn-sm"
                onClick={() => void switchRole(MODE_META[mode].demoUser as "teacher").then(() => navigate(MODE_META[mode].home))}
              >
                登录
              </button>
            )}
          </div>
        </header>
        <div className="content">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </div>
      </div>
      <TutorBall />
    </div>
  );
}
