/** 工作流执行过程可视化：步骤时间线 + 状态 + 输入输出留痕。 */

import { useState } from "react";
import type { WorkflowRun } from "../types";
import { Badge } from "./ui";

const STATUS_META: Record<string, { icon: string; tone: "blue" | "green" | "red" | "orange" | "gray"; text: string }> = {
  running: { icon: "◌", tone: "blue", text: "执行中" },
  success: { icon: "✓", tone: "green", text: "完成" },
  failed: { icon: "✕", tone: "red", text: "失败" },
  awaiting_approval: { icon: "⏳", tone: "orange", text: "待审批" },
  skipped: { icon: "–", tone: "gray", text: "跳过" },
};

function StepRow({
  label,
  status,
  input,
  output,
  error,
  finishedAt,
  startedAt,
  last,
}: {
  label: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error: string;
  finishedAt: string | null;
  startedAt: string;
  last: boolean;
}) {
  const [open, setOpen] = useState(false);
  const meta = STATUS_META[status] ?? STATUS_META.skipped;
  const duration =
    finishedAt && startedAt
      ? Math.max(0, (new Date(finishedAt).getTime() - new Date(startedAt).getTime()) / 1000)
      : null;
  const hasDetail = Object.keys(input).length > 0 || Object.keys(output).length > 0 || error;

  return (
    <div style={{ display: "flex", gap: 12 }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div
          style={{
            width: 26,
            height: 26,
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 13,
            fontWeight: 700,
            flexShrink: 0,
            background:
              status === "success"
                ? "#e6f7f1"
                : status === "failed"
                  ? "#fdecec"
                  : status === "awaiting_approval"
                    ? "#fef3e2"
                    : "#eef1f6",
            color:
              status === "success"
                ? "var(--success)"
                : status === "failed"
                  ? "var(--danger)"
                  : status === "awaiting_approval"
                    ? "#b26b00"
                    : "var(--text-3)",
          }}
        >
          {meta.icon}
        </div>
        {!last && <div style={{ width: 2, flex: 1, minHeight: 18, background: "var(--border)" }} />}
      </div>
      <div className="grow" style={{ paddingBottom: 16 }}>
        <div className="row space-between">
          <div className="row">
            <b>{label}</b>
            <Badge tone={meta.tone}>{meta.text}</Badge>
            {duration != null && <span className="small muted">{duration.toFixed(1)}s</span>}
          </div>
          {hasDetail && (
            <button className="btn btn-sm" onClick={() => setOpen(!open)}>
              {open ? "收起" : "详情"}
            </button>
          )}
        </div>
        {error && <div className="small mt-8" style={{ color: "var(--danger)" }}>✕ {error}</div>}
        {open && (
          <div className="mt-8">
            {Object.keys(output).length > 0 && (
              <pre className="code-block" style={{ fontSize: 12, maxHeight: 220, overflow: "auto" }}>
                {JSON.stringify(output, null, 2).slice(0, 1800)}
              </pre>
            )}
            {Object.keys(input).length > 0 && Object.keys(output).length === 0 && (
              <pre className="code-block" style={{ fontSize: 12, maxHeight: 180, overflow: "auto" }}>
                {JSON.stringify(input, null, 2).slice(0, 1200)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function WorkflowSteps({ run }: { run: WorkflowRun }) {
  return (
    <div>
      {run.steps.map((s, i) => (
        <StepRow
          key={s.id}
          label={s.label}
          status={s.status}
          input={s.input}
          output={s.output}
          error={s.error}
          startedAt={s.started_at}
          finishedAt={s.finished_at}
          last={i === run.steps.length - 1}
        />
      ))}
    </div>
  );
}

