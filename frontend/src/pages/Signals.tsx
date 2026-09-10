import { Check, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtRel } from "../lib/api";
import { STATUS_LABEL, type Alert, type AlertKind } from "../lib/types";

const KIND_LABEL: Record<AlertKind, string> = {
  interview: "Interview", assessment: "Assessment", status_update: "Update", follow_up: "Follow up",
  new_company: "New company", deadline: "Deadline", discovery: "Match", system: "Orbit",
};
const KIND_COLOR: Record<AlertKind, string> = {
  interview: "text-signal", assessment: "text-amber", status_update: "text-ink", follow_up: "text-ink",
  new_company: "text-mint", deadline: "text-rose", discovery: "text-mint", system: "text-rose",
};

export default function Signals() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const load = () => api.alerts().then(setAlerts);
  useEffect(() => { load(); }, []);

  const act = async (fn: () => Promise<unknown>) => { await fn(); load(); };
  const urgent = alerts.filter((a) => a.urgency === 3);
  const rest = alerts.filter((a) => a.urgency < 3);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Signals</h1>
          <p className="text-dim text-sm">What your inbox and the job boards turned up. Nothing changes on the board until you confirm it.</p>
        </div>
        {alerts.some((a) => !a.read) && <button className="btn-quiet" onClick={() => act(api.readAllAlerts)}>Mark all read</button>}
      </header>

      {alerts.length === 0 && (
        <div className="panel p-8 text-center text-dim">
          Nothing to act on. The morning check runs automatically; or trigger one from <Link to="/" className="text-signal">Today</Link>.
        </div>
      )}

      {urgent.length > 0 && <Group title="Needs a reply today" items={urgent} act={act} />}
      {rest.length > 0 && <Group title={urgent.length ? "Everything else" : "Recent"} items={rest} act={act} />}
    </div>
  );
}

function Group({ title, items, act }: { title: string; items: Alert[]; act: (fn: () => Promise<unknown>) => void }) {
  return (
    <section>
      <h2 className="text-sm text-dim mb-2">{title}</h2>
      <ul className="space-y-2">
        {items.map((a) => (
          <li key={a.id} className={`panel p-4 flex gap-4 ${a.read ? "opacity-70" : ""}`} onMouseEnter={() => !a.read && api.readAlert(a.id)}>
            <span className={`text-xs w-20 shrink-0 pt-0.5 ${KIND_COLOR[a.kind]}`}>{KIND_LABEL[a.kind]}</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm">{a.title}</div>
              {a.body && <p className="text-sm text-dim mt-0.5">{a.body}</p>}
              <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-dim">
                <span>{fmtRel(a.created_at)}</span>
                {a.application_id && <Link to={`/pipeline?app=${a.application_id}`} className="text-signal">Open in pipeline</Link>}
                {a.suggested_status && (
                  <button className="btn-ghost !py-1 !px-2 text-xs" onClick={() => act(() => api.applyAlertStatus(a.id))}>
                    <Check size={14} /> Move to {STATUS_LABEL[a.suggested_status]}
                  </button>
                )}
              </div>
            </div>
            <button className="btn-quiet self-start" aria-label="Dismiss" onClick={() => act(() => api.dismissAlert(a.id))}><X size={16} /></button>
          </li>
        ))}
      </ul>
    </section>
  );
}
