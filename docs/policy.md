# Policy (Slice 1 — locked)

Status: accepted. Deterministic. Fail closed. Pure functions, unit-tested.

## Dimensions (LLM proposes, code scores)

```text
operational_pain: 0-3, automation_plausibility: 0-3,
relevance: 0-3, evidence_quality: 0-3
0 = no usable evidence, 1 = weak/single/questionable,
2 = moderate, 3 = strong
score = sum(dimensions) / 12 * 100  (computed in code)
```

## Rules

```text
IF evidence_quality <= 1 → REVIEW (weak evidence escalates, never rejects)
ELSE IF supporting_evidence_count < 2 → REVIEW
ELSE IF score < 40 → REJECT
ELSE → REVIEW
```

## Effects

```text
REJECT → no external action (terminal)
REVIEW → requires human approval; no auto-action
APPROVED (human, within 24h) → Slack action allowed
REJECTED_BY_HUMAN | EXPIRED → no external action (terminal)
```

Approval expiry: `expires_at = requested_at + 24h`.
Late approve → `409 approval_expired`.

Safety story: model proposes, app scores + applies policy, human authorizes.
