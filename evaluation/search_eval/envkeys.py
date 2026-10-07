"""Root-.env fallback for provider keys (testable: path is a parameter)."""

import os
from pathlib import Path

DOTENV_KEYS = ("PARALLEL_API_KEY", "TAVILY_API_KEY", "SERPER_API_KEY")


def load_dotenv_fallback(path: str | Path) -> None:
    """Fill provider keys from a .env file when the shell has none set.

    Real environment variables always win. Only DOTENV_KEYS are read —
    nothing else in the file leaks into the process environment.
    """
    path = Path(path)
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name not in DOTENV_KEYS or os.environ.get(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ[name] = value
