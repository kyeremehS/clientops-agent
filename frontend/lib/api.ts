export type Approval = {
  id: string;
  lead_id: string;
  status: string;
  requested_at: string;
  expires_at: string;
  decided_at: string | null;
};

export type Artifact = {
  id: string;
  source_url: string;
  excerpt: string;
  content_hash: string;
};

export type Qualification = {
  operational_pain: number;
  automation_plausibility: number;
  relevance: number;
  evidence_quality: number;
  supporting_evidence_ids: string[];
  summary: string;
  score: number;
};

export type LeadDetail = {
  lead: { id: string; company: string; website: string; contact: string; message: string };
  state: string;
  artifacts: Artifact[];
  qualification: Qualification | null;
  decision: { outcome: string; reasons: string[] } | null;
  approval: Approval | null;
};

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const KEY = process.env.NEXT_PUBLIC_API_KEY;

async function request(path: string, init?: RequestInit) {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(KEY ? { Authorization: `Bearer ${KEY}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `request_failed_${response.status}`);
  }
  return response.json();
}

export const api = {
  pendingApprovals: (): Promise<Approval[]> =>
    request("/approvals/pending", { cache: "no-store" }),
  approve: (id: string): Promise<Approval> =>
    request(`/approvals/${id}/approve`, { method: "POST" }),
  reject: (id: string): Promise<Approval> =>
    request(`/approvals/${id}/reject`, { method: "POST" }),
  leadDetail: (id: string): Promise<LeadDetail> =>
    request(`/leads/${id}/detail`, { cache: "no-store" }),
};
