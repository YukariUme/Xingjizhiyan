/** 轻量代码编辑器：行号 + 等宽文本域。 */

export function CodeEditor({
  value,
  onChange,
  language = "python",
  minHeight = 220,
  readOnly = false,
  highlightLines = [],
}: {
  value: string;
  onChange?: (v: string) => void;
  language?: string;
  minHeight?: number;
  readOnly?: boolean;
  highlightLines?: number[];
}) {
  const lines = Math.max(1, value.split("\n").length);
  return (
    <div className="code-editor">
      <div className="line-nums" aria-hidden>
        {Array.from({ length: lines }, (_, i) => {
          const n = i + 1;
          return (
            <div key={n} className={`line-num ${highlightLines.includes(n) ? "hl" : ""}`}>
              {n}
            </div>
          );
        })}
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
