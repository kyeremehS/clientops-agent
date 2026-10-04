# Backend

Scaffold only. See root `AGENTS.md`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest tests -q
uvicorn app.main:app --reload
```
