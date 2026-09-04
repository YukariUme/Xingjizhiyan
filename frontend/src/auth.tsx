/** 登录态与角色切换。 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, clearAuth, getToken, setAuth } from "./api";
import type { LoginResult, Role, User } from "./types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<User>;
  register: (
    username: string,
    displayName: string,
    password: string,
    identity: string
  ) => Promise<User>;
  switchRole: (role: Role) => Promise<User>;
  applyExternalLogin: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem("jbgs_user");
    if (!raw) return null;
    try {
      return JSON.parse(raw) as User;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState<string | null>(() => getToken());

  useEffect(() => {
    if (!token) return;
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => {
        clearAuth();
        setUser(null);
        setToken(null);
      });
  }, [token]);

  const applyLogin = (result: LoginResult) => {
    setAuth(result.token, result.user);
    setToken(result.token);
    setUser(result.user);
    return result.user;
  };

  const login = async (username: string, password: string) => {
    const result = await api.post<LoginResult>("/auth/login", { username, password });
    return applyLogin(result);
  };

  const register = async (
    username: string,
    displayName: string,
    password: string,
    identity: string
  ) => {
    const result = await api.post<LoginResult>("/auth/register", {
      username,
      display_name: displayName,
      password,
      identity,
    });
    return applyLogin(result);
  };

  const switchRole = async (role: Role) => {
    const result = await api.get<LoginResult>(`/auth/demo/${role}`);
    return applyLogin(result);
  };

  const applyExternalLogin = (token: string, user: User) => {
    applyLogin({ token, user });
  };

  const logout = () => {
    clearAuth();
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, switchRole, applyExternalLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return ctx;
}
