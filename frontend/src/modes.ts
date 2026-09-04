/** 工作模式：身份与模式分离。顶部切换的是“当前工作模式”。 */

import type { Role, User } from "./types";

export type Mode = "teaching" | "learning" | "research";

export const MODE_META: Record<
  Mode,
  { label: string; home: string; icon: string; desc: string; demoUser: string }
> = {
  teaching: {
    label: "教学",
    home: "/teach",
    icon: "🎓",
    desc: "课程设计、资源生成、教学诊断",
    demoUser: "teacher",
  },
  learning: {
    label: "学习",
    home: "/learn",
    icon: "📚",
    desc: "课程学习、作业实验、复习模拟",
    demoUser: "student",
  },
  research: {
    label: "研究",
    home: "/research",
    icon: "🔬",
    desc: "论文阅读、前沿探索、科研资料",
    demoUser: "researcher",
  },
};

/** 身份 → 默认主模式首页（兼容旧登录跳转） */
export function roleHome(role: Role): string {
  if (role === "teacher") return "/teach";
  if (role === "researcher") return "/research";
  return "/learn";
}

/** 用户可进入的工作模式 */
export function allowedModes(user: User | null): Mode[] {
  if (!user) return ["teaching", "learning", "research"];
  const modes = (user.modes ?? []) as Mode[];
  if (modes.length > 0) return modes;
  if (user.role === "teacher") return ["teaching", "learning", "research"];
  if (user.role === "researcher") return ["research", "learning"];
  return ["learning", "research"];
}

export function modeLabel(user: User | null): string {
  if (!user) return "访客";
  const identity = user.identity ?? user.role;
  if (identity === "teacher") return "教师";
  if (identity === "graduate") return "研究生";
  if (identity === "researcher") return "研究生";
  return "本科生";
}

