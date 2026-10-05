# Product

Status: accepted (Slice 1)

## Problem

Inbound leads arrive unstructured (company + website + contact + message).
Turning one into an informed next action today is manual, slow, inconsistent,
and hard to audit.

## What ClientOps Agent does

Given an inbound lead, reliably determine what should happen next,
explain why with evidence, and safely execute that action when authorized.

Pipeline:

```text
Research → Evidence → Opportunity assessment → Recommendation
  → Deterministic policy → Human approval → Action → Audit
```

## Scope (Slice 1)

- Research: web search + website fetch only.
- Qualification: automation-opportunity assessment with evidence.
- Action: DB persist + Slack message to fixed `#sales-leads` test channel.
- Approval: frontend queue. Zero automatic external action.

## Non-goals (Slice 1)

- No CRM writes, no email sending, no email drafts.
- No LinkedIn / registries / Crunchbase / news.
- No full replay; event-chain audit only.
- No general-purpose "AI employee".

## Success

A lead can go from intake to approved Slack message with an evidence chain
answering "why did this action happen?", or be defensibly rejected/reviewed.
