import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import ApplicationDrawer from "../components/ApplicationDrawer";
import { api, fmtDate } from "../lib/api";
import { STATUS_COLOR, STATUS_LABEL, type Application, type Status } from "../lib/types";

const COLUMNS: Status[] = ["saved", "applied", "online_assessment", "interviewing", "offer", "rejected"];

export default function Board() {
  const [apps, setApps] = useState<Application[]>([]);
  const [selected, setSelected] = useState<Application | null>(null);
  const [open, setOpen] = useState(false);
  const [showArchive, setShowArchive] = useState(false);
  const load = () => api.applications().then(setApps);
  useEffect(() => { load(); }, []);

  const move = async (id: number, status: Status) => {
    setApps((xs) => xs.map((a) => (a.id === id ? { ...a, status } : a)));
    await api.updateApplication(id, { status });
    load();
  };

  const cols = showArchive ? [...COLUMNS, "withdrawn", "ghosted"] as Status[] : COLUMNS;

  return (
    <div className="space-y-5">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Pipeline</h1>
          <p className="text-dim text-sm">Drag a card to change its stage. {apps.length} tracked.</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-quiet" onClick={() => setShowArchive((s) => !s)}>{showArchive ? "Hide" : "Show"} archive</button>
          <button className="btn-primary" onClick={() => { setSelected(null); setOpen(true); }}><Plus size={16} /> Add</button>
        </div>
      </header>

      <div className="grid gap-3 overflow-x-auto pb-2" style={{ gridTemplateColumns: `repeat(${cols.length}, minmax(220px, 1fr))` }}>
        {cols.map((status) => {
          const items = apps.filter((a) => a.status === status);
          return (
            <section
              key={status}
              className="panel p-3 min-h-[60vh] flex flex-col"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { const id = Number(e.dataTransfer.getData("id")); if (id) move(id, status); }}
            >
              <h2 className={`text-sm mb-3 flex justify-between ${STATUS_COLOR[status]}`}>
                <span>{STATUS_LABEL[status]}</span><span className="text-dim">{items.length}</span>
              </h2>
              <div className="space-y-2 flex-1">
                {items.map((a) => (
                  <article
                    key={a.id}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData("id", String(a.id))}
                    onClick={() => { setSelected(a); setOpen(true); }}
                    className="panel-strong p-3 cursor-grab active:cursor-grabbing hover:border-signal/50"
                  >
                    <div className="font-medium text-sm">{a.company}</div>
                    <div className="text-sm text-dim">{a.role}</div>
                    {(a.next_action || a.location) && (
                      <div className="text-xs mt-2 flex justify-between gap-2">
                        <span className={a.next_action ? "text-amber truncate" : "text-dim truncate"}>{a.next_action ?? a.location}</span>
                        {a.next_action_at && <span className="text-dim shrink-0">{fmtDate(a.next_action_at)}</span>}
                      </div>
                    )}
                  </article>
                ))}
                {items.length === 0 && <p className="text-xs text-dim">Drop here</p>}
              </div>
            </section>
          );
        })}
      </div>

      <ApplicationDrawer app={selected} open={open} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); load(); }} />
    </div>
  );
}

