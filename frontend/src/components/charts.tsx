/** 轻量 SVG 图表组件（避免重型图表依赖）。 */

export function BarChart({
  data,
  height = 180,
  color = "#2f6fed",
  suffix = "%",
}: {
  data: Array<{ label: string; value: number }>;
  height?: number;
  color?: string;
  suffix?: string;
}) {
  const w = Math.max(320, data.length * 74);
  const max = Math.max(1, ...data.map((d) => d.value));
  const pad = { top: 18, right: 12, bottom: 46, left: 34 };
  const innerH = height - pad.top - pad.bottom;
  const barW = Math.min(42, (w - pad.left - pad.right) / data.length - 14);
  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={w} height={height} viewBox={`0 0 ${w} ${height}`}>
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line
              x1={pad.left}
              x2={w - pad.right}
              y1={pad.top + (innerH * (100 - v)) / 100}
              y2={pad.top + (innerH * (100 - v)) / 100}
              stroke="#edf0f5"
            />
            <text
              x={pad.left - 6}
              y={pad.top + (innerH * (100 - v)) / 100 + 3}
              fontSize="10"
              fill="#8a97a8"
              textAnchor="end"
            >
              {v}
            </text>
          </g>
        ))}
        {data.map((d, i) => {
          const x = pad.left + i * ((w - pad.left - pad.right) / data.length) + 7;
          const h = (d.value / max) * innerH;
          const y = pad.top + innerH - h;
          return (
            <g key={i}>
              <rect x={x} y={y} width={barW} height={Math.max(2, h)} rx={4} fill={color} />
              <text
                x={x + barW / 2}
                y={y - 5}
                fontSize="11"
                fontWeight="600"
                fill="#1d2733"
                textAnchor="middle"
              >
                {d.value}
                {suffix}
              </text>
              <text
                x={x + barW / 2}
                y={height - 12}
                fontSize="10.5"
                fill="#5b6b7d"
                textAnchor="middle"
              >
                {d.label.length > 9 ? `${d.label.slice(0, 9)}…` : d.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function LineChart({
  data,
  height = 200,
  color = "#7b5cff",
}: {
  data: Array<{ label: string; value: number }>;
  height?: number;
  color?: string;
}) {
  const w = Math.max(360, data.length * 56);
  const pad = { top: 18, right: 16, bottom: 34, left: 36 };
  const innerW = w - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const max = Math.max(1, ...data.map((d) => d.value));
  const pts = data.map((d, i) => ({
    x: pad.left + (data.length === 1 ? innerW / 2 : (i / (data.length - 1)) * innerW),
    y: pad.top + innerH - (d.value / max) * innerH,
    ...d,
  }));
  const path = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={w} height={height} viewBox={`0 0 ${w} ${height}`}>
        {[0, 0.5, 1].map((r) => (
          <line
            key={r}
            x1={pad.left}
            x2={w - pad.right}
            y1={pad.top + innerH * r}
            y2={pad.top + innerH * r}
            stroke="#edf0f5"
          />
        ))}
        {path && (
          <>
            <path d={path} fill="none" stroke={color} strokeWidth="2.5" />
            <path
              d={`${path} L${pts[pts.length - 1].x},${pad.top + innerH} L${pts[0].x},${pad.top + innerH} Z`}
              fill={color}
              opacity="0.08"
            />
          </>
        )}
        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="4" fill="#fff" stroke={color} strokeWidth="2" />
            <text x={p.x} y={p.y - 9} fontSize="10.5" fill="#5b6b7d" textAnchor="middle">
              {p.value}
            </text>
            <text x={p.x} y={height - 12} fontSize="10.5" fill="#8a97a8" textAnchor="middle">
              {p.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export function Donut({
  data,
  size = 180,
}: {
  data: Array<{ label: string; value: number; color: string }>;
  size?: number;
}) {
  const total = Math.max(1, data.reduce((s, d) => s + d.value, 0));
  const r = size / 2 - 16;
  const cx = size / 2;
  const cy = size / 2;
  let angle = -90;
  return (
    <div className="row" style={{ gap: 18 }}>
      <svg width={size} height={size}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#eef1f6" strokeWidth="20" />
        {data.map((d, i) => {
          if (d.value <= 0) return null;
          const frac = d.value / total;
          const start = angle;
          const end = angle + frac * 360;
          angle = end;
          const large = end - start > 180 ? 1 : 0;
          const x1 = cx + r * Math.cos((start * Math.PI) / 180);
          const y1 = cy + r * Math.sin((start * Math.PI) / 180);
          const x2 = cx + r * Math.cos((end * Math.PI) / 180);
          const y2 = cy + r * Math.sin((end * Math.PI) / 180);
          return (
            <path
              key={i}
              d={`M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`}
              fill="none"
              stroke={d.color}
              strokeWidth="20"
              strokeLinecap="round"
            />
          );
        })}
        <text x={cx} y={cy - 2} textAnchor="middle" fontSize="20" fontWeight="700" fill="#1d2733">
          {total}
        </text>
        <text x={cx} y={cy + 18} textAnchor="middle" fontSize="11" fill="#8a97a8">
          学生数
        </text>
      </svg>
      <div>
        {data.map((d, i) => (
          <div key={i} className="row" style={{ marginBottom: 6 }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: 3,
                background: d.color,
                display: "inline-block",
              }}
            />
            <span className="small" style={{ minWidth: 52 }}>
              {d.label}
            </span>
            <b>{d.value}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

