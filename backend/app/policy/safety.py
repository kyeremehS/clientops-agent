"""Per-tool-call safety gate. Every external call passes through check()."""


class GuardBlockedError(Exception):
    """Raised when a tool call is denied. Carries a stable code + plain reason."""

    def __init__(self, code: str, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason


class SafetyTracker:
    """Per-run call accounting: budget + repeat-call breaker state."""

    def __init__(self, max_calls: int = 30) -> None:
        self.max_calls = max_calls
        self.calls = 0
        self._seen: dict[str, int] = {}

    def record(self, signature: str) -> None:
        self.calls += 1
        self._seen[signature] = self._seen.get(signature, 0) + 1

    def repeats(self, signature: str) -> int:
        return self._seen.get(signature, 0)


def classify(tool_name: str) -> str:
    """auto = read-only observation; unknown tool names fail closed at check()."""
    raise NotImplementedError


def check(tracker: SafetyTracker, tool_name: str, args: dict) -> str:
    """Gate one tool call. Returns the action class, raises GuardBlockedError."""
    raise NotImplementedError


def _signature(tool_name: str, args: dict) -> str:
    raise NotImplementedError
