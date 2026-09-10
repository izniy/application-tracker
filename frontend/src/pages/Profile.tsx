import { Plus, Sparkles, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Profile as P } from "../lib/types";

const LEVELS = ["Internship", "New Grad", "Junior (1–2 yrs)", "Mid-level", "Senior+"];

const LOCATIONS = ["Singapore", "Remote", "United States", "United Kingdom", "Hong Kong", "Australia", "Malaysia", "Indonesia", "Japan", "Europe"];

const STACK: Record<string, string[]> = {
  Languages: ["Python", "TypeScript", "JavaScript", "Java", "C++", "Go", "Rust", "C#", "Kotlin", "Swift", "SQL"],
  "Backend & frameworks": ["React", "Next.js", "Node.js", "FastAPI", "Django", "Flask", "Spring", "GraphQL", "gRPC"],
  "Data & AI": ["PostgreSQL", "MongoDB", "Redis", "Spark", "Kafka", "Airflow", "dbt", "PyTorch", "TensorFlow", "LLMs / GenAI", "scikit-learn", "Pandas"],
  "Infra & cloud": ["AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux"],
};

export default function Profile() {
  const [p, setP] = useState<P | null>(null);
  const [form, setForm] = useState({ name: "", headline: "", location: "", target_roles: "", availability: "", preferences: "" });
  const [levels, setLevels] = useState<string[]>([]);
  const [locations, setLocations] = useState<string[]>([]);
  const [stack, setStack] = useState<string[]>([]);
  const [customLoc, setCustomLoc] = useState("");
  const [customTech, setCustomTech] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const hydrate = (x: P) => {
    setP(x);
    setForm({
      name: x.name ?? "", headline: x.headline ?? "", location: x.location ?? "",
      target_roles: (x.target_roles ?? []).join("\n"),
      availability: x.availability ?? "", preferences: x.preferences ?? "",
    });
    setLevels(x.target_levels ?? []);
    setLocations(x.target_locations ?? []);
    setStack(x.skills ?? []);
  };
  useEffect(() => { api.profile().then(hydrate); }, []);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const toggle = (xs: string[], setXs: (v: string[]) => void, v: string) =>
    setXs(xs.includes(v) ? xs.filter((x) => x !== v) : [...xs, v]);

  const save = async () => {
    setBusy("save");
    const x = await api.updateProfile({
      ...form,
      target_roles: form.target_roles.split("\n").map((s) => s.trim()).filter(Boolean),
      target_levels: levels, target_locations: locations, skills: stack,
    });
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

      <section className="panel p-5 grid md:grid-cols-2 gap-4">
        <div><label className="label">Name</label><input className="input" value={form.name} onChange={set("name")} /></div>
        <div><label className="label">Headline</label><input className="input" placeholder="Final-year CS student, backend & AI infra" value={form.headline} onChange={set("headline")} /></div>
        <div className="md:col-span-2"><label className="label">Based in</label><input className="input" value={form.location} onChange={set("location")} /></div>

        <div className="md:col-span-2">
          <label className="label">Target levels <span className="opacity-60">— roles above these are scored down hard</span></label>
          <div className="flex flex-wrap gap-2">
            {LEVELS.map((l) => <Chip key={l} on={levels.includes(l)} label={l} toggle={() => toggle(levels, setLevels, l)} />)}
          </div>
        </div>

        <div className="md:col-span-2">
          <label className="label">Target roles <span className="opacity-60">— one per line, as specific as you like; these become search queries</span></label>
          <textarea className="input min-h-24 font-mono text-sm" placeholder={"Software Engineer Intern\nBackend Engineer — Data Platform\nML Engineer (LLM infra)"} value={form.target_roles} onChange={set("target_roles")} />
        </div>

        <div className="md:col-span-2">
          <label className="label">Target locations</label>
          <div className="flex flex-wrap gap-2">
            {[...new Set([...LOCATIONS, ...locations])].map((l) => <Chip key={l} on={locations.includes(l)} label={l} toggle={() => toggle(locations, setLocations, l)} />)}
            <span className="inline-flex items-center gap-1">
              <input className="input !w-36 !py-1 text-sm" placeholder="Add country/city" value={customLoc} onChange={(e) => setCustomLoc(e.target.value)}
                     onKeyDown={(e) => { if (e.key === "Enter" && customLoc.trim()) { toggle(locations, setLocations, customLoc.trim()); setCustomLoc(""); } }} />
              <button className="btn-quiet !p-1" aria-label="Add location" onClick={() => { if (customLoc.trim()) { toggle(locations, setLocations, customLoc.trim()); setCustomLoc(""); } }}><Plus size={16} /></button>
            </span>
          </div>
        </div>

        <div className="md:col-span-2">
          <label className="label">Tech stack <span className="opacity-60">— what you'd be happy working in</span></label>
          <div className="space-y-2">
            {Object.entries(STACK).map(([group, items]) => (
              <div key={group} className="flex flex-wrap items-baseline gap-2">
                <span className="text-xs text-dim w-32 shrink-0">{group}</span>
                {items.map((t) => <Chip key={t} on={stack.includes(t)} label={t} toggle={() => toggle(stack, setStack, t)} />)}
              </div>
            ))}
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="text-xs text-dim w-32 shrink-0">Your own</span>
              {stack.filter((t) => !Object.values(STACK).flat().includes(t)).map((t) => <Chip key={t} on label={t} toggle={() => toggle(stack, setStack, t)} />)}
              <span className="inline-flex items-center gap-1">
                <input className="input !w-36 !py-1 text-sm" placeholder="Add your own" value={customTech} onChange={(e) => setCustomTech(e.target.value)}
                       onKeyDown={(e) => { if (e.key === "Enter" && customTech.trim()) { toggle(stack, setStack, customTech.trim()); setCustomTech(""); } }} />
                <button className="btn-quiet !p-1" aria-label="Add technology" onClick={() => { if (customTech.trim()) { toggle(stack, setStack, customTech.trim()); setCustomTech(""); } }}><Plus size={16} /></button>
              </span>
            </div>
          </div>
        </div>

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

function Chip({ on, label, toggle }: { on: boolean; label: string; toggle: () => void }) {
  return (
    <button type="button" onClick={toggle}
            className={`px-2.5 py-1 rounded-full border text-sm transition-colors ${on ? "border-signal/60 text-signal bg-signal/10" : "border-line text-dim hover:text-ink"}`}>
      {label}
    </button>
  );
}
