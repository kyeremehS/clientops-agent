# Agents (Slice 1 — boundaries)

Status: stub — prompts land in `feat/agents-slice1`.

## Research agent (`agents/research/`)

- Responsibility: company profile + operational signals + pain-point candidates.
- Inputs: Lead (company, website, message). Tools: `web_search`, `website_fetch`.
- Outputs: list of {claim, evidence_refs[], source_urls[]}. No scores, no recommendations.
- Forbidden: scoring, policy decisions, external writes.

## Qualification agent (`agents/qualification/`)

- Responsibility: assess automation opportunity from research + evidence.
- Inputs: Lead + ResearchArtifacts. Tools: none (reasoning over evidence only).
- Outputs (JSON-schema → Pydantic): {operational_pain 0-3, automation_plausibility 0-3,
  relevance 0-3, evidence_quality 0-3, supporting_evidence_ids[], summary}.
- Forbidden: inventing 0-100 scores, inventing sources, calling tools or Slack.
- May output "no sufficiently supported automation opportunity found."

Scoring and policy live in `backend/app/policy/` (see `policy.md`), never in prompts.
