import Link from "next/link";
import { api } from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function LeadDetailPage({ params }: { params: { id: string } }) {
  const detail = await api.leadDetail(params.id);
  const { lead, state, artifacts, qualification, decision, approval } = detail;
  return (
    <main>
      <p>
        <Link href="/approvals">← Approvals</Link>
      </p>
      <h1>{lead.company}</h1>
      <div>Status: {state}</div>
      {lead.website && <div>Website: {lead.website}</div>}
      {lead.contact && <div>Contact: {lead.contact}</div>}
      {lead.message && <div>Message: {lead.message}</div>}

      <h2>Research ({artifacts.length} sources)</h2>
      {artifacts.length === 0 && <p>No research yet.</p>}
      <ul>
        {artifacts.map((art) => (
          <li key={art.id}>
            <a href={art.source_url}>{art.source_url}</a>
            <p>{art.excerpt}</p>
          </li>
        ))}
      </ul>

      <h2>Qualification</h2>
      {!qualification && <p>Not rated yet.</p>}
      {qualification && (
        <div>
          <div>Fit: {qualification.score.toFixed(1)}/100</div>
          <ul>
            <li>Pain {qualification.operational_pain}/3</li>
            <li>Plausibility {qualification.automation_plausibility}/3</li>
            <li>Relevance {qualification.relevance}/3</li>
            <li>Evidence {qualification.evidence_quality}/3</li>
          </ul>
          <p>{qualification.summary}</p>
        </div>
      )}

      <h2>Decision</h2>
      {!decision && <p>No verdict yet.</p>}
      {decision && (
        <div>
          <div>{decision.outcome}</div>
          <ul>
            {decision.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {approval && <div>Approval: {approval.status}</div>}
    </main>
  );
}
