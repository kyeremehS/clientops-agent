"use client";

import { useState } from "react";
import { api, type Approval } from "../../lib/api";

export default function ApprovalCard({ approval }: { approval: Approval }) {
  const [status, setStatus] = useState(approval.status);
  const [error, setError] = useState<string | null>(null);

  async function act(kind: "approve" | "reject") {
    setError(null);
    try {
      const updated = await api[kind](approval.id);
      setStatus(updated.status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "request_failed");
    }
  }

  const decided = status !== "pending";
  return (
    <li style={{ border: "1px solid #ccc", padding: "1rem", marginBottom: "1rem" }}>
      <div>
        <strong>Approval</strong> {approval.id}
      </div>
      <div>Lead {approval.lead_id}</div>
      <div>Status: {status}</div>
      <div>Expires: {new Date(approval.expires_at).toISOString()}</div>
      {!decided && (
        <div style={{ marginTop: "0.5rem" }}>
          <button onClick={() => act("approve")}>Approve</button>{" "}
          <button onClick={() => act("reject")}>Reject</button>
        </div>
      )}
      {error && <div style={{ color: "red" }}>{error}</div>}
    </li>
  );
}
