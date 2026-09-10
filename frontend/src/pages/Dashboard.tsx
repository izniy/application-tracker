import { ArrowRight, Mail, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import OrbitRings from "../components/OrbitRings";

import { api, fmtDate, fmtRel } from "../lib/api";
import type { Dashboard as D } from "../lib/types";

/** Plain-language status line. Concrete beats motivational-poster. */
function headline(d: D): string {
  const c = d.counts_by_status;
  const parts: string[] = [];
  if (c.interviewing) parts.push(`${c.interviewing} interview${c.interviewing > 1 ? "s" : ""} in flight`);
  if (c.online_assessment) parts.push(`${c.online_assessment} assessment${c.online_assessment > 1 ? "s" : ""} to complete`);
  if (c.offer) parts.push(`${c.offer} offer${c.offer > 1 ? "s" : ""} on the table`);
  if (parts.length === 0 && c.applied) return `${c.applied} application${c.applied > 1 ? "s" : ""} out. The next reply could be today.`;
  if (parts.length === 0) return "Nothing in orbit yet. Add your first application or let Discover find one.";
  return parts.join(", ") + ".";
}

export default function Dashboard() {
  const [d, setD] = useState<D | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const alive = useRef(true);
  const load = () => api.dashboard().then(setD);
  useEffect(() => {
    alive.current = true;
    load();
    return () => { alive.current = false; };
  }, []);

  // Poll until the triggered run actually finishes — scans can take minutes.
  const run = async (job: "email_scan" | "job_scan") => {
    setRunning(job);
    const started = Date.now();
    await api.runJob(job);
    while (alive.current && Date.now() - started < 30 * 60_000) {
      await new Promise((r) => setTimeout(r, 5000));
      const latest = (await api.runs()).find((x) => x.job === job);
      if (latest?.finished_at && new Date(latest.finished_at).getTime() >= started) break;
      load(); // partial results (per-batch commits) show up as they land
    }
    if (alive.current) { load(); setRunning(null); }
  };

  if (!d) return <p className="text-dim">Loading…</p>;
  const today = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  return (
    <div className="space-y-8">
      <header className="grid md:grid-cols-[1fr_360px] gap-8 items-center">
        <div>
          <p className="text-dim text-sm">{today}</p>
          <h1 className="text-3xl md:text-4xl font-semibold leading-tight mt-2 max-w-xl">{headline(d)}</h1>
          <div className="flex flex-wrap gap-6 mt-6 text-sm">
            <Stat label="Active" value={d.active} />
            <Stat label="Response rate" value={`${d.response_rate}%`} />
            <Stat label="Unread signals" value={d.unread_alerts} accent={d.unread_alerts > 0} />
          </div>
          <div className="flex flex-wrap gap-2 mt-6">
            <button className="btn-ghost" onClick={() => run("email_scan")} disabled={!d.email_connected || !!running}>
              <Mail size={16} /> {running === "email_scan" ? "Checking inbox…" : "Check inbox now"}
            </button>
            <button className="btn-ghost" onClick={() => run("job_scan")} disabled={!d.profile_ready || !!running}>
              <RefreshCw size={16} /> {running === "job_scan" ? "Searching…" : "Find new jobs now"}
            </button>
          </div>
          {(!d.email_connected || !d.profile_ready) && (
            <p className="text-sm text-dim mt-4">
              {!d.profile_ready && <><Link className="text-signal" to="/profile">Finish your profile</Link> so Discover knows what to look for. </>}
              {!d.email_connected && <><Link className="text-signal" to="/settings">Connect Gmail</Link> to get interview and assessment alerts automatically.</>}
            </p>
          )}
        </div>
        <OrbitRings counts={d.counts_by_status} />
      </header>

      <div className="grid md:grid-cols-3 gap-4">
        <Panel title="Due soon" to="/pipeline">
          {d.due_soon.length === 0 && <Empty>No deadlines on the radar.</Empty>}
          {d.due_soon.map((a) => (
            <Row key={a.id} top={a.company} sub={a.next_action ?? "Action due"} right={fmtDate(a.next_action_at)} />
          ))}
        </Panel>
        <Panel title="Latest signals" to="/signals">
          {d.recent_alerts.length === 0 && <Empty>Quiet inbox. Signals appear here after the morning check.</Empty>}
          {d.recent_alerts.map((a) => (
            <Row key={a.id} top={a.title} sub={a.body ?? ""} right={fmtRel(a.created_at)} dot={!a.read} />
          ))}
        </Panel>
        <Panel title="Best matches this week" to="/discover">
          {d.top_matches.length === 0 && <Empty>Discover runs each morning once your profile is ready.</Empty>}
          {d.top_matches.map((j) => (
            <Row key={j.id} top={`${j.role}`} sub={j.company} right={j.match_score != null ? `${Math.round(j.match_score)}` : ""} />
          ))}
        </Panel>
      </div>

      <footer className="text-xs text-dim flex flex-wrap gap-x-6 gap-y-1">
        <span>Inbox checked {fmtRel(d.last_runs.email_scan)}</span>
        <span>Jobs searched {fmtRel(d.last_runs.job_scan)}</span>
        <span>Deadlines reviewed {fmtRel(d.last_runs.deadline_check)}</span>
      </footer>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div>
      <div className={`font-display text-2xl ${accent ? "text-amber" : ""}`}>{value}</div>
      <div className="text-dim">{label}</div>
    </div>
  );
}

function Panel({ title, to, children }: { title: string; to: string; children: React.ReactNode }) {
  return (
    <section className="panel p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-medium">{title}</h2>
        <Link to={to} className="text-dim hover:text-ink" aria-label={`Open ${title}`}><ArrowRight size={16} /></Link>
      </div>
      <ul className="space-y-3">{children}</ul>
    </section>
  );
}

function Row({ top, sub, right, dot }: { top: string; sub: string; right: string; dot?: boolean }) {
  return (
    <li className="flex gap-3 text-sm">
      {dot !== undefined && <span className={`mt-2 h-1.5 w-1.5 rounded-full shrink-0 ${dot ? "bg-amber" : "bg-transparent"}`} />}
      <div className="min-w-0 flex-1">
        <div className="truncate">{top}</div>
        <div className="text-dim truncate">{sub}</div>
      </div>
      <div className="text-dim shrink-0">{right}</div>
    </li>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <li className="text-sm text-dim">{children}</li>;
}

