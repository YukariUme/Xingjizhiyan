/** 账号登录 / 注册弹窗（真实账号体系，区别于一键演示角色）。 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { roleHome } from "../modes";
import type { User } from "../types";
import { Modal } from "./ui";

const IDENTITIES: Array<{ key: string; label: string; hint: string }> = [
  { key: "undergraduate", label: "本科生", hint: "学习 + 研究" },
  { key: "graduate", label: "研究生", hint: "学习 + 研究" },
  { key: "teacher", label: "教师", hint: "教学 + 学习 + 研究" },
];

export function AuthModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"login" | "register">("login");
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [regForm, setRegForm] = useState({
    username: "",
    displayName: "",
    password: "",
    confirm: "",
    identity: "undergraduate",
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const go = (user: User) => {
    onClose();
    navigate(roleHome(user.role));
  };

  const doLogin = async () => {
    if (!loginForm.username || !loginForm.password) {
      setErr("请输入用户名和密码");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const user = await login(loginForm.username, loginForm.password);
      go(user);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "登录失败");
    } finally {
      setBusy(false);
    }
  };

  const doRegister = async () => {
    if (!regForm.username || !regForm.displayName || !regForm.password) {
      setErr("请填写完整注册信息");
      return;
    }
    if (regForm.password !== regForm.confirm) {
      setErr("两次输入的密码不一致");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const user = await register(
        regForm.username,
        regForm.displayName,
        regForm.password,
        regForm.identity
      );
      go(user);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "注册失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="账号登录 / 注册"
      open={open}
      onClose={onClose}
      footer={
        tab === "login" ? (
          <button className="btn btn-primary" onClick={() => void doLogin()} disabled={busy}>
            {busy ? "登录中…" : "登录"}
          </button>
        ) : (
          <button className="btn btn-primary" onClick={() => void doRegister()} disabled={busy}>
            {busy ? "注册中…" : "注册并进入"}
          </button>
        )
      }
    >
      <div className="role-switch mb-16">
        <button className={tab === "login" ? "active" : ""} onClick={() => { setTab("login"); setErr(""); }}>
          登录
        </button>
        <button className={tab === "register" ? "active" : ""} onClick={() => { setTab("register"); setErr(""); }}>
          注册
        </button>
      </div>

      {tab === "login" ? (
        <div className="form-grid">
          <div className="field">
            <label>用户名</label>
            <input
              className="input"
              value={loginForm.username}
              onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
              placeholder="如：student1"
            />
          </div>
          <div className="field">
            <label>密码</label>
            <input
              type="password"
              className="input"
              value={loginForm.password}
              onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && void doLogin()}
            />
          </div>
        </div>
      ) : (
        <div className="form-grid">
          <div className="field">
            <label>用户名 *（至少 3 个字符）</label>
            <input
              className="input"
              value={regForm.username}
              onChange={(e) => setRegForm({ ...regForm, username: e.target.value })}
              placeholder="字母/数字/下划线"
            />
          </div>
          <div className="field">
            <label>姓名 *</label>
            <input
              className="input"
              value={regForm.displayName}
              onChange={(e) => setRegForm({ ...regForm, displayName: e.target.value })}
              placeholder="如：张三"
            />
          </div>
          <div className="field">
            <label>密码 *（至少 6 位）</label>
            <input
              type="password"
              className="input"
              value={regForm.password}
              onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
            />
          </div>
          <div className="field">
            <label>确认密码 *</label>
            <input
              type="password"
              className="input"
              value={regForm.confirm}
              onChange={(e) => setRegForm({ ...regForm, confirm: e.target.value })}
            />
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>身份</label>
            <div className="row wrap">
              {IDENTITIES.map((r) => (
                <div key={r.key} className="row" style={{ gap: 6 }}>
                  <button
                    className={`btn btn-sm ${regForm.identity === r.key ? "btn-primary" : ""}`}
                    onClick={() => setRegForm({ ...regForm, identity: r.key })}
                  >
                    {r.label}
                  </button>
                  <span className="small muted">{r.hint}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      {err && <div className="badge red mt-8">{err}</div>}
      <p className="small muted mt-16" style={{ marginBottom: 0 }}>
        演示账号：teacher1 / student1 / researcher1，密码均为 123456；也可以直接注册真实账号。
      </p>
    </Modal>
  );
}
