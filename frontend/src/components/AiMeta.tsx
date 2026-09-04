/** AI 生成内容统一标识：AI 标签 + 提供方 + 参考来源（含 [S]/[A]/[P] 等级与页码）。 */

export interface AiReference {
  title?: string;
  source?: string;
  course?: string;
  chapter?: string;
  source_level?: string;
  page?: string;
  snippet?: string;
}

export function AiLabel({ provider }: { provider?: string }) {
  return <span className="badge purple">✦ AI 生成{provider ? ` · ${provider}` : ""}</span>;
}

export function ReferenceList({
  references,
  title = "参考来源",
}: {
  references?: AiReference[];
  title?: string;
}) {
  if (!references || references.length === 0) return null;
  return (
    <div className="mt-8" style={{ borderTop: "1px dashed var(--border)", paddingTop: 8 }}>
      <div className="small" style={{ fontWeight: 600 }}>{title}</div>
      {references.map((r, i) => (
        <div key={i} className="small muted" style={{ padding: "4px 0" }}>
          <span className="badge gray">[{r.source_level ?? "S"}]</span> {r.title}
          {r.page ? ` · 第 ${r.page} 页` : ""}
          {r.source ? ` · ${r.source}` : ""}
          {r.chapter ? ` · ${r.chapter}` : ""}
        </div>
      ))}
    </div>
  );
}

export function AiMeta({ provider, references }: { provider?: string; references?: AiReference[] }) {
  return (
    <div className="mt-8">
      <AiLabel provider={provider} />
      <ReferenceList references={references} />
    </div>
  );
}

