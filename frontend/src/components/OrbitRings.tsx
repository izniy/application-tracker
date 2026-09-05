/** The one memorable element: applications rendered as bodies on concentric orbits,
 *  one ring per active stage. Draws itself once on load; sweeps slowly after. */
import { STATUS_LABEL, type Status } from "../lib/types";

const RINGS: { status: Status; r: number; color: string }[] = [
  { status: "applied", r: 60, color: "#E8EEF9" },
  { status: "online_assessment", r: 95, color: "#FFB547" },
  { status: "interviewing", r: 130, color: "#5EE7FF" },
  { status: "offer", r: 165, color: "#4ADE80" },
];

export default function OrbitRings({ counts }: { counts: Record<Status, number> }) {
  const size = 360;
  const c = size / 2;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[360px] mx-auto" role="img" aria-label="Applications by stage">
      <defs>
        <radialGradient id="core">
          <stop offset="0%" stopColor="#5EE7FF" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#5EE7FF" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx={c} cy={c} r={22} fill="url(#core)" />
      <circle cx={c} cy={c} r={4} fill="#5EE7FF" />
      <line x1={c} y1={c} x2={c} y2={c - 170} stroke="#5EE7FF" strokeOpacity="0.25" className="sweep" />
      {RINGS.map(({ status, r, color }, i) => {
        const n = counts[status] ?? 0;
        return (
          <g key={status}>
            <circle cx={c} cy={c} r={r} fill="none" stroke="#1F2A45" strokeWidth="1" className="draw" style={{ animationDelay: `${i * 0.15}s` }} />
            {Array.from({ length: Math.min(n, 24) }).map((_, k) => {
              const a = (k / Math.min(n, 24)) * Math.PI * 2 - Math.PI / 2 + i * 0.4;
              return <circle key={k} cx={c + r * Math.cos(a)} cy={c + r * Math.sin(a)} r={n > 12 ? 3 : 4.5} fill={color} />;
            })}
            <text x={c + (r + 8) * Math.SQRT1_2} y={c - (r + 8) * Math.SQRT1_2} fontSize="10" fill="#7C8AA6" className="font-body">
              {STATUS_LABEL[status]} {n}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
