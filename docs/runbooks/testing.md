# Testing

```powershell
# Backend unit (required before every backend commit)
python -m pytest backend/tests -q
```

```powershell
# Evaluation (from B6)
python evaluation/run.py
```

Policy/scoring tests must cover: `eq<=1 → REVIEW`, `count<2 → REVIEW`,
`score<40 → REJECT`, expired approval → `409 approval_expired`,
no external action without valid approval.
