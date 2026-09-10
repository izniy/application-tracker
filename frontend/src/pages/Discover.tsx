import DOMPurify from "dompurify";
import { Bookmark, ExternalLink, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, fmtRel } from "../lib/api";
import type { DiscoveredJob } from "../lib/types";

export default function Discover() {
  const [jobs, setJobs] = useState<DiscoveredJob[]>([]);
  const [min, setMin] = useState(60);
  const [expanded, setExpanded] = useState<number | null>(null);
  const load = () => api.jobs(min).then(setJobs);
  useEffect(() => { load(); }, [min]);

  const save = async (j: DiscoveredJob) => { await api.saveDiscovered(j.id); load(); };
  const dismiss = async (j: DiscoveredJob) => { await api.dismissJob(j.id); load(); };

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Discover</h1>
          <p className="text-dim text-sm">Roles found overnight and scored against your profile and what you've already applied to.</p>
        </div>
        <label className="text-sm text-dim flex items-center gap-3">
          Show matches above
          <input type="range" min={0} max={95} step={5} value={min} onChange={(e) => setMin(Number(e.target.value))} className="accent-signal" />
          <span className="text-ink w-6">{min}</span>
        </label>
      </header>

      {jobs.length === 0 && (
        <div className="panel p-8 text-center text-dim">No matches at this threshold yet. Lower the slider, or run "Find new jobs now" from Today.</div>
      )}

      <ul className="grid md:grid-cols-2 gap-3">
        {jobs.map((j) => (
          <li key={j.id} className={`panel p-4 flex flex-col gap-3 ${j.verdict === "saved" ? "border-mint/40" : ""}`}>
            <div className="flex items-start gap-3">
              <Score value={j.match_score} />
              <div className="min-w-0 flex-1">
                <div className="font-medium truncate">{j.role}</div>
                <div className="text-sm text-dim truncate">{j.company}{j.location ? ` · ${j.location}` : ""}</div>
              </div>
            </div>
            {j.match_reason && <p className="text-sm text-dim">{j.match_reason}</p>}
            {expanded === j.id && j.description && (
              <div className="text-sm text-dim max-h-64 overflow-y-auto border-t border-line pt-3" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(j.description) }} />
            )}
            <div className="flex items-center gap-2 mt-auto text-xs text-dim">
              <span>{j.source} · {fmtRel(j.found_at)}</span>
              <span className="flex-1" />
              {j.description && <button className="btn-quiet !p-1" onClick={() => setExpanded(expanded === j.id ? null : j.id)}>{expanded === j.id ? "Less" : "Details"}</button>}
              <a className="btn-quiet !p-1" href={j.url} target="_blank" rel="noreferrer" aria-label="Open posting"><ExternalLink size={16} /></a>
              {j.verdict !== "saved" && <button className="btn-ghost !py-1 !px-2" onClick={() => save(j)}><Bookmark size={14} /> Save to pipeline</button>}
              <button className="btn-quiet !p-1" onClick={() => dismiss(j)} aria-label="Not interested"><X size={16} /></button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Score({ value }: { value: number | null }) {
  const v = value ?? 0;
  const color = v >= 80 ? "text-mint border-mint/50" : v >= 60 ? "text-signal border-signal/50" : "text-dim border-line";
  return <div className={`h-11 w-11 shrink-0 rounded-full border grid place-items-center font-display text-sm ${color}`}>{value == null ? "–" : Math.round(v)}</div>;
}
