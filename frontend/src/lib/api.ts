import type { Alert, Application, Dashboard, DiscoveredJob, Profile } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.status === 204 ? (undefined as T) : r.json();
}

export const api = {
  dashboard: () => req<Dashboard>("/system/dashboard"),
  runJob: (job: "email_scan" | "job_scan" | "deadline_check") => req(`/system/run/${job}`, { method: "POST" }),
  runs: () => req<{ job: string; started_at: string; finished_at: string | null; ok: boolean; summary: string | null }[]>("/system/runs"),

  applications: () => req<Application[]>("/applications"),
  createApplication: (body: Partial<Application>) => req<Application>("/applications", { method: "POST", body: JSON.stringify(body) }),
  updateApplication: (id: number, body: Partial<Application> & { status_reason?: string }) =>
    req<Application>(`/applications/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteApplication: (id: number) => req<void>(`/applications/${id}`, { method: "DELETE" }),
  saveDiscovered: (jobId: number) => req<Application>(`/applications/from-discovered/${jobId}`, { method: "POST" }),

  alerts: () => req<Alert[]>("/alerts"),
  readAlert: (id: number) => req<Alert>(`/alerts/${id}/read`, { method: "POST" }),
  dismissAlert: (id: number) => req<Alert>(`/alerts/${id}/dismiss`, { method: "POST" }),
  applyAlertStatus: (id: number) => req<Alert>(`/alerts/${id}/apply-status`, { method: "POST" }),
  readAllAlerts: () => req("/alerts/read-all", { method: "POST" }),

  jobs: (minScore = 0) => req<DiscoveredJob[]>(`/jobs?min_score=${minScore}`),
  dismissJob: (id: number) => req<DiscoveredJob>(`/jobs/${id}/dismiss`, { method: "POST" }),

  profile: () => req<Profile>("/profile"),
  updateProfile: (body: Partial<Profile>) => req<Profile>("/profile", { method: "PUT", body: JSON.stringify(body) }),
  uploadResume: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/profile/resume", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    return r.json() as Promise<Profile>;
  },
  summariseProfile: () => req<Profile>("/profile/summarise", { method: "POST" }),

  emailStatus: () => req<{ connected: boolean; configured: boolean }>("/email/status"),
  disconnectEmail: () => req("/email/disconnect", { method: "POST" }),
};

export const fmtDate = (s: string | null | undefined) =>
  s ? new Date(s).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : "";

export const fmtRel = (s: string | null | undefined) => {
  if (!s) return "never";
  const d = (Date.now() - new Date(s).getTime()) / 36e5;
  if (d < 1) return "just now";
  if (d < 24) return `${Math.round(d)}h ago`;
  return `${Math.round(d / 24)}d ago`;
};
