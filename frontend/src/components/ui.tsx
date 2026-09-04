/** 通用 UI 组件集合。 */

import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

export function Card({
  title,
  extra,
  children,
  className = "",
}: {
  title?: ReactNode;
  extra?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`card ${className}`}>
      {(title || extra) && (
        <div className="card-title">
          <h3>{title}</h3>
          {extra}
        </div>
      )}
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  color,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  color?: string;
}) {
  return (
    <div className="card stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={color ? { color } : undefined}>
        {value}
      </div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}

export function Badge({
  children,
  tone = "blue",
}: {
  children: ReactNode;
  tone?: "blue" | "green" | "red" | "orange" | "purple" | "gray";
}) {
  const cls = {
    blue: "",
    green: "badge-green",
    red: "badge-red",
    orange: "badge-orange",
    purple: "badge-purple",
    gray: "badge-gray",
  }[tone];
  return <span className={`badge ${cls}`}>{children}</span>;
}

export function verdictBadge(verdict: string | null | undefined): ReactNode {
  if (!verdict) return <Badge tone="gray">未评测</Badge>;
  if (verdict === "accepted") return <Badge tone="green">AC</Badge>;
  if (verdict === "compile_error") return <Badge tone="orange">编译错误</Badge>;
  return <Badge tone="red">未通过</Badge>;
}

export function statusBadge(status: string): ReactNode {
  if (status === "graded") return <Badge tone="green">已批改</Badge>;
  if (status === "under_review") return <Badge tone="orange">待教师确认</Badge>;
  return <Badge tone="gray">已提交</Badge>;
}

/** 把任意值安全转成纯文本（对象/数组递归展开），避免直接把对象渲染成 React 子节点。 */
export function toDisplayText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    return value
      .map((v) => toDisplayText(v))
      .filter((x) => x)
      .join("\n");
  }
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => {
        const t = toDisplayText(v);
        return t ? `${k}：${t}` : k;
      })
      .join("\n");
  }
  return String(value);
}

function scalarEntries(value: Record<string, unknown>): Array<[string, string]> {
  return Object.entries(value)
    .map(([k, v]) => [k, toDisplayText(v)] as [string, string])
    .filter(([, v]) => v);
}

/**
 * 安全渲染 AI 返回内容：字符串→段落；纯对象→键值表；
 * 对象数组（如论文实验表格）→ 表格；其他嵌套结构→文本。
 * 防止 LLM 把某个字段返回成对象时前端直接崩溃。
 */
export function RichText({
  content,
  className = "small",
}: {
  content: unknown;
  className?: string;
}) {
  if (content == null || content === "") return null;

  // 对象数组 → 统一键的表格（论文“实验”字段常见：组别/人数/干预方式/指标/结果）
  if (
    Array.isArray(content) &&
    content.length > 0 &&
    content.every((x) => x != null && typeof x === "object" && !Array.isArray(x))
  ) {
    const rows = content as Array<Record<string, unknown>>;
    const columns: string[] = [];
    for (const row of rows) {
      for (const key of Object.keys(row)) {
        if (!columns.includes(key)) columns.push(key);
      }
    }
    return (
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {columns.map((c) => (
                  <td key={c} className="small">
                    {toDisplayText(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // 纯对象 → 键值表
  if (typeof content === "object" && !Array.isArray(content)) {
    const entries = scalarEntries(content as Record<string, unknown>);
    if (entries.length > 0) {
      return (
        <div className="table-wrap">
          <table className="table">
            <tbody>
              {entries.map(([k, v]) => (
                <tr key={k}>
                  <th style={{ whiteSpace: "nowrap" }}>{k}</th>
                  <td className="small">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
  }

  const text = toDisplayText(content);
  if (!text) return null;
  return (
    <p className={className} style={{ whiteSpace: "pre-wrap" }}>
      {text}
    </p>
  );
}

export function Progress({
  value,
  max = 100,
  tone,
}: {
  value: number;
  max?: number;
  tone?: "auto" | "green" | "orange" | "red";
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  let cls = "";
  if (tone === "auto") {
    cls = pct >= 80 ? "green" : pct >= 60 ? "orange" : "red";
  } else if (tone) {
    cls = tone;
  }
  return (
    <div className={`progress ${cls}`}>
      <div style={{ width: `${pct}%` }} />
    </div>
  );
}

export function EmptyState({
  emoji = "🗂️",
  text,
}: {
  emoji?: string;
  text: string;
}) {
  return (
    <div className="empty">
      <div className="emoji">{emoji}</div>
      <div>{text}</div>
    </div>
  );
}

export function Loading({ text = "加载中…" }: { text?: string }) {
  return (
    <div className="center">
      <span className="spinner" />
      {text}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div
      className="card mb-16"
      style={{ borderColor: "rgba(184,74,50,0.5)", color: "var(--danger)" }}
    >
      ⚠️ {message}
    </div>
  );
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    fn()
      .then((d) => {
        if (alive) setData(d);
      })
      .catch((e: Error) => {
        if (alive) setError(e.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, version]);

  const refresh = () => setVersion((v) => v + 1);
  return { data, error, loading, setData, setLoading, refresh };
}

export function Modal({
  title,
  open,
  onClose,
  children,
  footer,
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  if (!open) return null;
  return (
    createPortal(
      <div className="modal-mask" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-head">
            <h3>{title}</h3>
            <button className="close-btn" onClick={onClose}>
              ✕
            </button>
          </div>
          {children}
          {footer && <div className="modal-foot">{footer}</div>}
        </div>
      </div>,
      document.body
    )
  );
}

export function Tabs({
  items,
  active,
  onChange,
}: {
  items: Array<{ key: string; label: string }>;
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className="row wrap" style={{ gap: 6, marginBottom: 16 }}>
      {items.map((it) => (
        <button
          key={it.key}
          className={`btn btn-sm ${active === it.key ? "btn-primary" : ""}`}
          onClick={() => onChange(it.key)}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}
