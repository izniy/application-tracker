import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

export default function Settings() {
  const [email, setEmail] = useState<{ connected: boolean; configured: boolean } | null>(null);
  const [runs, setRuns] = useState<Awaited<ReturnType<typeof api.runs>>>([]);
  const [params] = useSearchParams();
  const load = () => { api.emailStatus().then(setEmail); api.runs().then(setRuns); };
  useEffect(load, []);

  return (
    <div className="space-y-6 max-w-3xl">
      <header>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-dim text-sm">Connections and the automation log.</p>
      </header>

      <section className="panel p-5">
        <h2 className="font-medium mb-1">Gmail</h2>
        {params.get("email") === "connected" && <p className="text-sm text-mint mb-2">Connected.</p>}
        {email?.connected ? (
          <>
            <p className="text-sm text-dim mb-3">Read-only access. Orbit checks the last two days of mail each morning, sends only job-related messages to the model, and never sends email.</p>
            <button className="btn-ghost" onClick={async () => { await api.disconnectEmail(); load(); }}>Disconnect</button>
          </>
        ) : email?.configured ? (
          <>
            <p className="text-sm text-dim mb-3">Connect to get alerts for interview invites, assessments, rejections and new recruiters — without opening your inbox.</p>
            <a className="btn-primary" href="/api/email/oauth/start">Connect Gmail</a>
          </>
        ) : (
          <p className="text-sm text-dim">Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to backend/.env, then restart the server.</p>
        )}
      </section>

      <section className="panel p-5">
        <h2 className="font-medium mb-1">Job sources</h2>
        <p className="text-sm text-dim">Remotive is on by default. Add ADZUNA_APP_ID / ADZUNA_APP_KEY in backend/.env for Singapore and other country boards. More sources live in backend/app/services/scraper.</p>
      </section>

      <section className="panel p-5">
        <h2 className="font-medium mb-3">Automation log</h2>
        {runs.length === 0 && <p className="text-sm text-dim">No runs yet.</p>}
        <ul className="text-sm space-y-1.5">
          {runs.map((r, i) => (
            <li key={i} className="flex gap-3">
              <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${r.ok ? "bg-mint" : "bg-rose"}`} />
              <span className="w-28 shrink-0 text-dim">{r.job.replace("_", " ")}</span>
              <span className="text-dim shrink-0">{new Date(r.started_at).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
              <span className="truncate">{r.summary}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
