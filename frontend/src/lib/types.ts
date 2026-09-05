export type Status =
  | "saved" | "applied" | "online_assessment" | "interviewing"
  | "offer" | "rejected" | "withdrawn" | "ghosted";

export const STATUSES: Status[] = [
  "saved", "applied", "online_assessment", "interviewing", "offer", "rejected", "withdrawn", "ghosted",
];

export const STATUS_LABEL: Record<Status, string> = {
  saved: "Saved",
  applied: "Applied",
  online_assessment: "Online assessment",
  interviewing: "Interviewing",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  ghosted: "No response",
};

export const STATUS_COLOR: Record<Status, string> = {
  saved: "text-dim",
  applied: "text-ink",
  online_assessment: "text-amber",
  interviewing: "text-signal",
  offer: "text-mint",
  rejected: "text-rose",
  withdrawn: "text-dim",
  ghosted: "text-dim",
};

export interface StatusEvent {
  id: number; from_status: string | null; to_status: string;
  reason: string | null; source: string; created_at: string;
}

export interface Application {
  id: number; company: string; role: string; location: string | null; url: string | null;
  source: string | null; status: Status; applied_at: string | null;
  next_action: string | null; next_action_at: string | null; notes: string | null;
  job_description: string | null; company_domains: string[] | null;
  created_at: string; updated_at: string; events: StatusEvent[];
}

export type AlertKind = "status_update" | "interview" | "assessment" | "follow_up" | "new_company" | "deadline" | "discovery";

export interface Alert {
  id: number; kind: AlertKind; title: string; body: string | null;
  application_id: number | null; email_id: number | null; suggested_status: Status | null;
  urgency: 1 | 2 | 3; read: boolean; dismissed: boolean; created_at: string;
}

export interface DiscoveredJob {
  id: number; external_id: string; source: string; company: string; role: string;
  location: string | null; url: string; description: string | null; posted_at: string | null;
  match_score: number | null; match_reason: string | null; verdict: string | null; found_at: string;
}

export interface Profile {
  id: number; name: string | null; headline: string | null; location: string | null;
  target_roles: string[] | null; target_locations: string[] | null; skills: string[] | null;
  seniority: string | null; availability: string | null; preferences: string | null;
  resume_filename: string | null; resume_text: string | null; llm_summary: string | null; updated_at: string;
}

export interface Dashboard {
  counts_by_status: Record<Status, number>; active: number; response_rate: number; unread_alerts: number;
  due_soon: Application[]; recent_alerts: Alert[]; top_matches: DiscoveredJob[];
  last_runs: Record<"email_scan" | "job_scan" | "deadline_check", string | null>;
  email_connected: boolean; profile_ready: boolean;
}
