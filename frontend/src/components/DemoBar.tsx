/** Demo Mode UI：一键演示入口、场景选择/快速主题输入、顶部状态条与快捷键。 */

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDemo, type DemoSessionState, type DemoStep } from "../demo";
import { Modal } from "./ui";

const ROLE_LABEL: Record<string, string> = {
  teacher: "教师",
  student: "学生",
  researcher: "研究",
};

function stepPath(session: DemoSessionState, step: DemoStep): string {
  return step.path.replace(":os", String(session.scenario.course));
}

// 快速主题 → 场景 / 步骤 匹配（供“一键输入场景内容”使用）
const SCENARIO_MATCH: Array<{ keys: string[]; scenario: string }> = [
  {
    keys: ["同步", "信号量", "生产者", "消费者", "死锁", "进程", "线程", "操作系统", "科研", "论文"],
    scenario: "teaching_learning_research",
  },
  { keys: ["备课", "作业", "学情", "批改", "教学", "调整", "课程设计"], scenario: "teaching_loop" },
  { keys: ["预习", "复习", "模拟", "测验", "错题", "学习", "讲堂", "答疑", "图谱"], scenario: "learning_loop" },
];
const STEP_MATCH: Record<string, Record<string, string>> = {
  teaching_learning_research: {
    诊断: "teacher_diagnose",
    备课: "teacher_plan",
    讲堂: "student_lecture",
    预习: "student_preview",
    图谱: "knowledge_graph",
    答疑: "student_tutor",
    代码: "student_code",
    作业: "student_code",
    个性化: "student_profile",
    复习: "student_review",
    模拟: "student_exam",
    前沿: "research_hotspots",
    论文: "research_paper",
  },
  teaching_loop: {
    备课: "teacher_plan",
    作业: "teacher_assignment",
    学情: "teacher_analytics",
    调整: "teacher_adjust",
  },
  learning_loop: {
    预习: "preview",
    讲堂: "lecture",
    图谱: "graph",
    作业: "homework",
    评测: "judge",
    诊断: "diagnose",
    复习: "review",
    模拟: "exam",
  },
};

export function DemoEntryButton() {
  const { scenarios, startAt, loading } = useDemo();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [quick, setQuick] = useState("");
  const [error, setError] = useState("");

  const quickStart = async (topic: string) => {
    const t = topic.trim();
    if (!t) return;
    setError("");
    try {
      const match = SCENARIO_MATCH.find((m) => m.keys.some((k) => t.includes(k)));
      const scenarioId = match?.scenario ?? "teaching_learning_research";
      const stepMap = STEP_MATCH[scenarioId] ?? {};
      const stepId = Object.entries(stepMap).find(([k]) => t.includes(k))?.[1];
      const s = await startAt(scenarioId, stepId);
      setOpen(false);
      const target =
        (stepId ? s.scenario.steps.find((st) => st.id === stepId) : undefined) ?? s.scenario.steps[0];
      navigate(target ? stepPath(s, target) : "/teach");
    } catch (e) {
      setError(e instanceof Error ? e.message : "演示启动失败，请检查后端服务是否已启动。");
    }
  };

  const launch = async (scenarioId: string) => {
    setError("");
    try {
      const s = await startAt(scenarioId);
      setOpen(false);
      const first = s.scenario.steps[0];
      navigate(first ? stepPath(s, first) : "/teach");
    } catch (e) {
      setError(e instanceof Error ? e.message : "演示启动失败，请检查后端服务是否已启动。");
    }
  };

  // 快捷键：Ctrl+Shift+D 打开/关闭演示选择器
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "d") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <button
        className="btn btn-sm"
        style={{ borderColor: "var(--warning)", color: "#9c5e0c", fontWeight: 600 }}
        onClick={() => setOpen(true)}
        disabled={loading}
        title="快捷键：Ctrl+Shift+D"
      >
        ▶ 一键演示
      </button>
      <Modal
        title="▶ 一键演示"
        open={open}
        onClose={() => setOpen(false)}
        footer={
          <div style={{ width: "100%" }}>
            {error && (
              <p className="badge red mb-8" style={{ margin: "0 0 8px" }}>
                {error}
              </p>
            )}
            <p className="small muted" style={{ margin: 0 }}>
              点击场景卡片或输入主题一键进入演示；当前为演示模式，数据为预置演示数据，不会影响真实账户。
              <br />
              快捷键：<b>Ctrl+Shift+D</b> 演示 · <b>Ctrl+Shift+→/←</b> 上/下一步 ·{" "}
              <b>Ctrl+Shift+1/2/3</b> 教师/学生/研究 · <b>Ctrl+Shift+R</b> 重置 ·{" "}
              <b>Ctrl+Shift+X</b> 退出
            </p>
          </div>
        }
      >
        <div className="field mb-16">
          <label>⚡ 快速输入演示主题</label>
          <div className="row" style={{ gap: 6 }}>
            <input
              className="input grow"
              value={quick}
              onChange={(e) => setQuick(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void quickStart(quick)}
              placeholder="输入主题快速开始，如：进程同步 / 生产者消费者 / 备课 / 考前模拟"
            />
            <button className="btn btn-primary" onClick={() => void quickStart(quick)} disabled={loading}>
              {loading ? "启动中…" : "一键开始"}
            </button>
          </div>
        </div>
        <div className="grid">
          {scenarios.map((sc) => (
            <div
              key={sc.id}
              className="card"
              style={{ cursor: "pointer" }}
              onClick={() => void launch(sc.id)}
            >
              <div className="row space-between">
                <b>{sc.name}</b>
                <span className="badge orange">约 3 分钟</span>
              </div>
              <p className="small muted mt-8">{sc.description}</p>
              <div className="row wrap mt-8">
                {sc.steps.slice(0, 5).map((s) => (
                  <span key={s.id} className="badge gray">
                    {s.label.replace(/^\d+\s*/, "")}
                  </span>
                ))}
                <span className="badge gray">…</span>
              </div>
            </div>
          ))}
          {scenarios.length === 0 && <div className="muted small">演示场景加载中…</div>}
        </div>
      </Modal>
    </>
  );
}

const AI_STAGES = ["正在检索课程知识库…", "正在分析班级学情…", "正在生成演示内容…"];

export function DemoStatusBar() {
  const { session, next, prev, gotoStep, switchRole, reset, exit } = useDemo();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<{ msg: string; tick: number } | null>(null);
  const handlersRef = useRef<{
    doNext: () => void;
    doPrev: () => void;
    doSwitchRole: (role: "teacher" | "student" | "researcher") => void;
    doReset: () => void;
    doExit: () => void;
  }>({
    doNext: () => {},
    doPrev: () => {},
    doSwitchRole: () => {},
    doReset: () => {},
    doExit: () => {},
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!e.ctrlKey || !e.shiftKey) return;
      const k = e.key.toLowerCase();
      if (k === "arrowright") {
        e.preventDefault();
        void handlersRef.current.doNext();
      } else if (k === "arrowleft") {
        e.preventDefault();
        void handlersRef.current.doPrev();
      } else if (k === "1") {
        e.preventDefault();
        void handlersRef.current.doSwitchRole("teacher");
      } else if (k === "2") {
        e.preventDefault();
        void handlersRef.current.doSwitchRole("student");
      } else if (k === "3") {
        e.preventDefault();
        void handlersRef.current.doSwitchRole("researcher");
      } else if (k === "r") {
        e.preventDefault();
        void handlersRef.current.doReset();
      } else if (k === "x") {
        e.preventDefault();
        void handlersRef.current.doExit();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  if (!session) return null;
  const steps = session.scenario.steps;
  const currentIdx = steps.findIndex((s) => s.id === session.current_step);
  const go = (s: DemoStep) => navigate(stepPath(session, s));

  const runStaged = async (fn: () => Promise<void>) => {
    let i = 0;
    setBusy({ msg: AI_STAGES[0], tick: 0 });
    const timer = window.setInterval(() => {
      i += 1;
      setBusy({ msg: AI_STAGES[i % AI_STAGES.length], tick: i });
    }, 420);
    try {
      await Promise.all([fn(), new Promise((r) => setTimeout(r, 900))]);
    } finally {
      window.clearInterval(timer);
      setBusy(null);
    }
  };

  const doNext = () =>
    runStaged(async () => {
      const s = await next();
      if (!s) return;
      const step = s.scenario.steps.find((x) => x.id === s.current_step);
      if (step) go(step);
    });

  const doPrev = () =>
    runStaged(async () => {
      const s = await prev();
      if (!s) return;
      const step = s.scenario.steps.find((x) => x.id === s.current_step);
      if (step) go(step);
    });

  const doGotoStep = (s: DemoStep) =>
    runStaged(async () => {
      await gotoStep(s.id);
      go(s);
    });

  const doSwitchRole = (role: "teacher" | "student" | "researcher") =>
    runStaged(async () => {
      await switchRole(role);
      navigate(role === "teacher" ? "/teach" : role === "student" ? "/learn" : "/research");
    });

  const doReset = () =>
    runStaged(async () => {
      if (!window.confirm("将恢复 Demo 初始状态，确定继续吗？")) return;
      await reset();
      const first = session.scenario.steps[0];
      navigate(first ? stepPath(session, first) : "/teach");
    });

  const doExit = async () => {
    if (!window.confirm("退出演示并恢复你的真实账户？")) return;
    await exit();
    navigate("/");
  };

  // 快捷键：Ctrl+Shift+→/← 步骤 · 1/2/3 角色 · R 重置 · X 退出
  handlersRef.current = { doNext, doPrev, doSwitchRole, doReset, doExit };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "7px 24px",
        background: "linear-gradient(90deg, #b26b16, #c77b16)",
        color: "#fffaf0",
        fontSize: 13,
        flexWrap: "wrap",
      }}
    >
      <b style={{ letterSpacing: "0.08em" }}>DEMO MODE</b>
      <span style={{ opacity: 0.9 }}>
        {session.scenario.name} · 当前角色：{ROLE_LABEL[session.current_role] ?? session.current_role}
      </span>
      {busy && (
        <span
          style={{
            position: "fixed",
            top: 58,
            right: 24,
            zIndex: 200,
            background: "rgba(38,54,51,0.94)",
            color: "#fffaf0",
            borderRadius: 999,
            padding: "6px 16px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
          }}
        >
          ⏳ {busy.msg}
        </span>
      )}
      <div className="row" style={{ gap: 4, flex: 1, flexWrap: "wrap" }}>
        {steps.map((s, i) => (
          <button
            key={s.id}
            onClick={() => void doGotoStep(s)}
            style={{
              border: "none",
              background: i === currentIdx ? "#fffaf0" : "rgba(255,250,240,0.22)",
              color: i === currentIdx ? "#9c5e0c" : "#fffaf0",
              borderRadius: 999,
              padding: "3px 10px",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: i === currentIdx ? 700 : 500,
            }}
          >
            {s.label}
          </button>
        ))}
      </div>
      <button className="btn btn-sm" style={{ background: "transparent", borderColor: "#fffaf0", color: "#fffaf0" }} onClick={() => void doPrev()}>
        ← 上一步
      </button>
      <button className="btn btn-sm" style={{ background: "#fffaf0", color: "#9c5e0c" }} onClick={() => void doNext()}>
        下一步 →
      </button>
      <button className="btn btn-sm" style={{ background: "transparent", borderColor: "#fffaf0", color: "#fffaf0" }} onClick={() => void doSwitchRole("student")}>
        切换学生
      </button>
      <button className="btn btn-sm" style={{ background: "transparent", borderColor: "#fffaf0", color: "#fffaf0" }} onClick={() => void doSwitchRole("teacher")}>
        切换教师
      </button>
      <button className="btn btn-sm" style={{ background: "transparent", borderColor: "#fffaf0", color: "#fffaf0" }} onClick={() => void doSwitchRole("researcher")}>
        研究
      </button>
      <button className="btn btn-sm" style={{ background: "transparent", borderColor: "#fffaf0", color: "#fffaf0" }} onClick={() => void doReset()}>
        ⟲ 重置演示
      </button>
      <button className="btn btn-sm" style={{ background: "rgba(184,74,50,0.85)", borderColor: "#fffaf0", color: "#fffaf0" }} onClick={() => void doExit()}>
        退出演示
      </button>
      <span style={{ opacity: 0.65, fontSize: 11 }} title="Ctrl+Shift+→/← 步骤 · 1/2/3 角色 · R 重置 · X 退出">
        快捷键：→/← 步骤 · 1/2/3 角色
      </span>
    </div>
  );
}
