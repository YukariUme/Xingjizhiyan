/** Demo Mode 状态管理：会话、步骤、角色、重置与退出（真实页面复用现有路由）。 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, clearAuth, getToken, setAuth, setDemoSessionId } from "./api";
import { useAuth } from "./auth";
import type { User } from "./types";

export interface DemoStep {
  id: string;
  label: string;
  path: string;
}

export interface DemoScenarioInfo {
  id: string;
  name: string;
  description: string;
  course: string | number;
  course_name?: string;
  steps: DemoStep[];
}

export interface DemoSessionState {
  session_id: string;
  scenario: DemoScenarioInfo;
  current_step: string;
  current_role: string;
  role_user: { id: number; display_name: string; title: string };
  state_version: number;
}

interface DemoContextValue {
  active: boolean;
  loading: boolean;
  session: DemoSessionState | null;
  scenarios: DemoScenarioInfo[];
  start: (scenarioId: string) => Promise<DemoSessionState>;
  startAt: (scenarioId: string, stepId?: string) => Promise<DemoSessionState>;
  next: () => Promise<DemoSessionState | null>;
  prev: () => Promise<DemoSessionState | null>;
  gotoStep: (stepId: string) => Promise<DemoSessionState | null>;
  switchRole: (role: "teacher" | "student" | "researcher") => Promise<void>;
  reset: () => Promise<void>;
  exit: () => Promise<void>;
}

const DemoContext = createContext<DemoContextValue | null>(null);

const DEMO_KEY = "jbgs_demo_session";
const BACKUP_KEY = "jbgs_demo_backup";

export function DemoProvider({ children }: { children: ReactNode }) {
  const { applyExternalLogin } = useAuth();
  const [session, setSession] = useState<DemoSessionState | null>(null);
  const [scenarios, setScenarios] = useState<DemoScenarioInfo[]>([]);
  const [loading, setLoading] = useState(false);

  // 恢复上次演示会话（刷新页面后仍处于 Demo）
  useEffect(() => {
    const sid = localStorage.getItem(DEMO_KEY);
    if (!sid) return;
    api
      .get<DemoSessionState>(`/demo/session/${sid}`)
      .then((s) => {
        setSession(s);
        setDemoSessionId(s.session_id);
      })
      .catch(() => {
        localStorage.removeItem(DEMO_KEY);
        setDemoSessionId(null);
      });
  }, []);

  const persist = (s: DemoSessionState) => {
    localStorage.setItem(DEMO_KEY, s.session_id);
    setDemoSessionId(s.session_id);
    setSession(s);
  };

  const loginAs = async (role: string) => {
    const res = await api.post<{ token: string; user: User }>("/demo/login", { role });
    applyExternalLogin(res.token, res.user);
  };

  const start = useCallback(
    async (scenarioId: string) => {
      return startAt(scenarioId);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const startAt = useCallback(async (scenarioId: string, stepId?: string) => {
    setLoading(true);
    try {
      // 备份当前真实登录态
      const token = getToken();
      const raw = localStorage.getItem("jbgs_user");
      if (token && raw) localStorage.setItem(BACKUP_KEY, JSON.stringify({ token, user: raw }));
      const s = await api.post<DemoSessionState>("/demo/start", { scenario_id: scenarioId });
      persist(s);
      let target = s;
      if (stepId && s.scenario.steps.some((st) => st.id === stepId)) {
        target = await api.post<DemoSessionState>(`/demo/session/${s.session_id}/step`, {
          step_id: stepId,
        });
        persist(target);
      }
      await loginAs(target.current_role);
      return target;
    } finally {
      setLoading(false);
    }
  }, []);

  const next = useCallback(async () => {
    if (!session) return session;
    const s = await api.post<DemoSessionState>(`/demo/session/${session.session_id}/step`, {
      direction: "next",
    });
    persist(s);
    return s;
  }, [session]);

  const prev = useCallback(async () => {
    if (!session) return session;
    const s = await api.post<DemoSessionState>(`/demo/session/${session.session_id}/step`, {
      direction: "prev",
    });
    persist(s);
    return s;
  }, [session]);

  const gotoStep = useCallback(
    async (stepId: string) => {
      if (!session) return null;
      const s = await api.post<DemoSessionState>(`/demo/session/${session.session_id}/step`, {
        step_id: stepId,
      });
      persist(s);
      return s;
    },
    [session]
  );

  const switchRole = useCallback(
    async (role: "teacher" | "student" | "researcher") => {
      if (!session) return;
      const s = await api.post<DemoSessionState>(`/demo/session/${session.session_id}/role`, { role });
      persist(s);
      await loginAs(role);
    },
    [session]
  );

  const reset = useCallback(async () => {
    if (!session) return;
    const s = await api.post<DemoSessionState>(`/demo/session/${session.session_id}/reset`, {});
    persist(s);
    await loginAs(s.current_role);
  }, [session]);

  const exit = useCallback(async () => {
    const sid = session?.session_id ?? localStorage.getItem(DEMO_KEY);
    if (sid) {
      api.post(`/demo/session/${sid}/exit`, {}).catch(() => undefined);
    }
    setDemoSessionId(null);
    localStorage.removeItem(DEMO_KEY);
    const backup = localStorage.getItem(BACKUP_KEY);
    localStorage.removeItem(BACKUP_KEY);
    if (backup) {
      try {
        const { token, user } = JSON.parse(backup) as { token: string; user: string };
        const parsed = JSON.parse(user) as User;
        setAuth(token, parsed);
        applyExternalLogin(token, parsed);
      } catch {
        clearAuth();
      }
    } else {
      clearAuth();
    }
    setSession(null);
  }, [session, applyExternalLogin]);

  // 预取场景列表
  useEffect(() => {
    api
      .get<DemoScenarioInfo[]>("/demo/scenarios")
      .then(setScenarios)
      .catch(() => undefined);
  }, []);

  const value = useMemo<DemoContextValue>(
    () => ({
      active: !!session,
      loading,
      session,
      scenarios,
      start,
      startAt,
      next,
      prev,
      gotoStep,
      switchRole,
      reset,
      exit,
    }),
    [session, loading, scenarios, start, startAt, next, prev, gotoStep, switchRole, reset, exit]
  );

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo(): DemoContextValue {
  const ctx = useContext(DemoContext);
  if (!ctx) throw new Error("useDemo 必须在 DemoProvider 内使用");
  return ctx;
}
