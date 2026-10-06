export type Approval = {
  id: string;
  lead_id: string;
  status: string;
  requested_at: string;
  expires_at: string;
  decided_at: string | null;
};

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request(path: string, init?: RequestInit) {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
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
};
