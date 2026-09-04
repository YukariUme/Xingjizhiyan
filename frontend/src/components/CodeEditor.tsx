/** 轻量代码编辑器：行号 + 等宽文本域。 */

export function CodeEditor({
  value,
  onChange,
  language = "python",
  minHeight = 220,
  readOnly = false,
}: {
  value: string;
  onChange?: (v: string) => void;
  language?: string;
  minHeight?: number;
  readOnly?: boolean;
}) {
  const lines = Math.max(1, value.split("\n").length);
  return (
    <div className="code-editor">
      <div className="line-nums" aria-hidden>
        {Array.from({ length: lines }, (_, i) => i + 1).join("\n")}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        spellCheck={false}
        readOnly={readOnly}
        style={{ minHeight }}
        aria-label={`代码编辑器（${language}）`}
      />
    </div>
  );
}

