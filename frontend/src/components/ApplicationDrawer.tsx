import { ExternalLink, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, fmtDate } from "../lib/api";
import { STATUSES, STATUS_LABEL, type Application, type Status } from "../lib/types";

interface Props {
  app: Application | null;         // null = create new
  open: boolean;
  onClose: () => void;
  onSaved: (a: Application | undefined) => void;
}

const empty: Partial<Application> = { company: "", role: "", location: "", url: "", status: "applied", notes: "", next_action: "", next_action_at: null };

export default function ApplicationDrawer({ app, open, onClose, onSaved }: Props) {
  const [form, setForm] = useState<Partial<Application> & { status_reason?: string }>(empty);
  const [busy, setBusy] = useState(false);
  const [domains, setDomains] = useState("");

  useEffect(() => {
    setForm(app ? { ...app } : empty);
    setDomains(app?.company_domains?.join(", ") ?? "");
  }, [app, open]);

  if (!open) return null;
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value || null }));

  const save = async () => {
    setBusy(true);
    try {
      const body = { ...form, company_domains: domains.split(",").map((s) => s.trim()).filter(Boolean) };
      delete (body as Partial<Application>).events;
      const saved = app ? await api.updateApplication(app.id, body) : await api.createApplication(body);
      onSaved(saved);
    } finally {
      setBusy(false);
    }
  };
  const remove = async () => {
    if (!app || !confirm(`Delete ${app.company} — ${app.role}?`)) return;
    await api.deleteApplication(app.id);
    onSaved(undefined);
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-void/60 backdrop-blur-sm" onClick={onClose}>
      <aside className="w-full max-w-lg h-full overflow-y-auto bg-deck border-l border-line p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4 mb-6">
          <h2 className="text-xl font-semibold">{app ? `${app.company}` : "Add application"}</h2>
          <button className="btn-quiet" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><label className="label">Company</label><input className="input" value={form.company ?? ""} onChange={set("company")} /></div>
          <div className="col-span-2"><label className="label">Role</label><input className="input" value={form.role ?? ""} onChange={set("role")} /></div>
          <div><label className="label">Location</label><input className="input" value={form.location ?? ""} onChange={set("location")} /></div>
          <div>
            <label className="label">Status</label>
            <select className="input" value={form.status ?? "applied"} onChange={set("status")}>
              {STATUSES.map((s: Status) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
            </select>
          </div>
          <div className="col-span-2 flex gap-2 items-end">
            <div className="flex-1"><label className="label">Job link</label><input className="input" value={form.url ?? ""} onChange={set("url")} /></div>
            {form.url && <a className="btn-ghost" href={form.url} target="_blank" rel="noreferrer"><ExternalLink size={16} /></a>}
          </div>
          <div><label className="label">Next action</label><input className="input" placeholder="e.g. Finish OA" value={form.next_action ?? ""} onChange={set("next_action")} /></div>
          <div><label className="label">Due</label><input className="input" type="date" value={form.next_action_at?.slice(0, 10) ?? ""} onChange={set("next_action_at")} /></div>
          <div className="col-span-2">
            <label className="label">Company email domains <span className="opacity-60">— emails from these auto-link here</span></label>
            <input className="input" placeholder="stripe.com, greenhouse.io" value={domains} onChange={(e) => setDomains(e.target.value)} />
          </div>
          <div className="col-span-2"><label className="label">Notes</label><textarea className="input min-h-24" value={form.notes ?? ""} onChange={set("notes")} /></div>
          <div className="col-span-2"><label className="label">Job description <span className="opacity-60">— helps Discover find similar roles</span></label><textarea className="input min-h-24" value={form.job_description ?? ""} onChange={set("job_description")} /></div>
        </div>

        <div className="flex items-center gap-2 mt-6">
          <button className="btn-primary" onClick={save} disabled={busy || !form.company || !form.role}>{app ? "Save changes" : "Add application"}</button>
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          {app && <button className="btn-quiet ml-auto text-rose" onClick={remove}><Trash2 size={16} /> Delete</button>}
        </div>

        {app && app.events.length > 0 && (
          <section className="mt-8">
            <h3 className="text-sm text-dim mb-2">History</h3>
            <ol className="border-l border-line ml-1 pl-4 space-y-3">
              {app.events.map((e) => (
                <li key={e.id} className="text-sm">
                  <span className="text-ink">{STATUS_LABEL[e.to_status as Status] ?? e.to_status}</span>
                  <span className="text-dim"> · {fmtDate(e.created_at)}{e.source !== "manual" ? ` · via ${e.source}` : ""}</span>
                  {e.reason && <p className="text-dim">{e.reason}</p>}
                </li>
              ))}
            </ol>
          </section>
        )}
      </aside>
    </div>
  );
}
