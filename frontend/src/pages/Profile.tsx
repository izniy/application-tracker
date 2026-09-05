import { Sparkles, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Profile as P } from "../lib/types";

const list = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const join = (xs: string[] | null | undefined) => (xs ?? []).join(", ");

export default function Profile() {
  const [p, setP] = useState<P | null>(null);
  const [form, setForm] = useState({ name: "", headline: "", location: "", target_roles: "", target_locations: "", skills: "", seniority: "intern", availability: "", preferences: "" });
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const hydrate = (x: P) => {
    setP(x);
    setForm({
      name: x.name ?? "", headline: x.headline ?? "", location: x.location ?? "",
      target_roles: join(x.target_roles), target_locations: join(x.target_locations), skills: join(x.skills),
      seniority: x.seniority ?? "intern", availability: x.availability ?? "", preferences: x.preferences ?? "",
    });
  };
  useEffect(() => { api.profile().then(hydrate); }, []);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = async () => {
    setBusy("save");
    const x = await api.updateProfile({ ...form, target_roles: list(form.target_roles), target_locations: list(form.target_locations), skills: list(form.skills) });
    hydrate(x); setBusy(null); setMsg("Saved.");
  };
  const upload = async (f: File | undefined) => {
    if (!f) return;
    setBusy("upload"); hydrate(await api.uploadResume(f)); setBusy(null); setMsg(`Read ${f.name}.`);
  };
  const summarise = async () => {
    setBusy("llm"); await save(); hydrate(await api.summariseProfile()); setBusy(null); setMsg("Profile summary refreshed.");
  };

  if (!p) return <p className="text-dim">Loading…</p>;

  return (
    <div className="space-y-6 max-w-3xl">
      <header>
        <h1 className="text-2xl font-semibold">Profile</h1>
        <p className="text-dim text-sm">This is what Orbit knows about you. The matcher and the inbox reader both read the summary at the bottom.</p>
      </header>

      <section className="panel p-5 grid md:grid-cols-2 gap-3">
        <div><label className="label">Name</label><input className="input" value={form.name} onChange={set("name")} /></div>
        <div><label className="label">Headline</label><input className="input" placeholder="Final-year CS student, backend & AI infra" value={form.headline} onChange={set("headline")} /></div>
        <div><label className="label">Based in</label><input className="input" value={form.location} onChange={set("location")} /></div>
        <div>
          <label className="label">Seniority</label>
          <select className="input" value={form.seniority} onChange={set("seniority")}>
            <option value="intern">Intern</option><option value="new_grad">New grad</option><option value="mid">Mid-level</option><option value="senior">Senior</option>
          </select>
        </div>
        <div className="md:col-span-2"><label className="label">Target roles <span className="opacity-60">— comma separated; these are the search queries</span></label><input className="input" placeholder="Software Engineer Intern, Data Infrastructure Intern, ML Engineer" value={form.target_roles} onChange={set("target_roles")} /></div>
        <div className="md:col-span-2"><label className="label">Target locations</label><input className="input" placeholder="Singapore, Remote" value={form.target_locations} onChange={set("target_locations")} /></div>
        <div className="md:col-span-2"><label className="label">Skills</label><input className="input" placeholder="Python, TypeScript, Spark, Postgres, LLM evals" value={form.skills} onChange={set("skills")} /></div>
        <div className="md:col-span-2"><label className="label">Availability</label><input className="input" placeholder="Internship Feb–May 2027; full-time from Jun 2027" value={form.availability} onChange={set("availability")} /></div>
        <div className="md:col-span-2"><label className="label">What you want, and what you don't</label><textarea className="input min-h-28" placeholder="Excited by: infra, data platforms, AI tooling. Avoid: pure frontend, unpaid roles." value={form.preferences} onChange={set("preferences")} /></div>
        <div className="md:col-span-2 flex items-center gap-2">
          <button className="btn-primary" onClick={save} disabled={busy !== null}>Save profile</button>
          <span className="text-sm text-dim">{msg}</span>
        </div>
      </section>

      <section className="panel p-5">
        <h2 className="font-medium mb-1">Resume</h2>
        <p className="text-sm text-dim mb-3">{p.resume_filename ? `Using ${p.resume_filename}.` : "No resume yet. PDF or DOCX."}</p>
        <label className="btn-ghost cursor-pointer w-fit">
          <Upload size={16} /> {busy === "upload" ? "Reading…" : "Upload resume"}
          <input type="file" className="hidden" accept=".pdf,.docx,.txt,.md" onChange={(e) => upload(e.target.files?.[0])} />
        </label>
      </section>

      <section className="panel p-5">
        <div className="flex items-center justify-between gap-4 mb-2">
          <h2 className="font-medium">How Orbit describes you</h2>
          <button className="btn-ghost" onClick={summarise} disabled={busy !== null}><Sparkles size={16} /> {busy === "llm" ? "Writing…" : p.llm_summary ? "Regenerate" : "Generate summary"}</button>
        </div>
        {p.llm_summary ? <p className="text-sm leading-relaxed">{p.llm_summary}</p> : <p className="text-sm text-dim">Save your details and upload a resume, then generate. Discover will not run until this exists.</p>}
      </section>
    </div>
  );
}
