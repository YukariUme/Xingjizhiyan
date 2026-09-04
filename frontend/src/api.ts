/** API 客户端：统一携带 Token、错误处理。 */

const BASE = (import.meta.env.VITE_API_BASE as string) || "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem("jbgs_token");
}

export function setAuth(token: string, user: unknown): void {
  localStorage.setItem("jbgs_token", token);
  localStorage.setItem("jbgs_user", JSON.stringify(user));
}

export function clearAuth(): void {
  localStorage.removeItem("jbgs_token");
  localStorage.removeItem("jbgs_user");
}

let demoSessionId = "";

/** Demo Mode：设置当前演示会话，所有请求自动携带 X-Demo-Session 头。 */
export function setDemoSessionId(sessionId: string | null): void {
  demoSessionId = sessionId ?? "";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (demoSessionId) headers["X-Demo-Session"] = demoSessionId;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const resp = await fetch(`${BASE}${path}`, { ...options, headers });
  if (resp.status === 401) {
    clearAuth();
    window.location.href = "/";
    throw new ApiError(401, "登录已失效");
  }
  if (!resp.ok) {
    let detail = `请求失败（${resp.status}）`;
    try {
      const data = await resp.json();
      detail = data.detail || detail;
    } catch {
      /* 忽略解析失败 */
    }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
};
