import ApprovalCard from "./approval-card";
import { api } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function ApprovalsPage() {
  const approvals = await api.pendingApprovals();
  return (
    <main>
      <h1>Approvals</h1>
      {approvals.length === 0 && <p>No pending approvals.</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {approvals.map((approval) => (
          <ApprovalCard key={approval.id} approval={approval} />
        ))}
      </ul>
    </main>
  );
}
