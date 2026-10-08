"""Per-tool-call safety gate. Every external call passes through check().

Order per call: known tool → budget → repeat breaker. Unknown names and
exhausted budgets deny by default; the repeat breaker trips on the 3rd
identical (tool, args) call — a loop signal, not a message problem.
"""

import json

_READ_TOOLS = ("web_search", "website_fetch")
_REPEAT_TRIP_AT = 3


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
    """auto = read-only observation, proceeds. Anything else fails closed."""
    if tool_name in _READ_TOOLS:
        return "auto"
    return "unknown"


def _signature(tool_name: str, args: dict) -> str:
    try:
        canonical = json.dumps(args, sort_keys=True, default=str)
    except (TypeError, ValueError):
        canonical = repr(sorted((key, str(value)) for key, value in args.items()))
    return f"{tool_name}:{canonical}"


def check(tracker: SafetyTracker, tool_name: str, args: dict) -> str:
    """Gate one tool call. Returns the action class; raises GuardBlockedError."""
    if classify(tool_name) == "unknown":
        raise GuardBlockedError("unknown_tool", f"tool {tool_name!r} is not registered")
    if tracker.calls >= tracker.max_calls:
        raise GuardBlockedError(
            "budget_exceeded", f"tool budget of {tracker.max_calls} calls exhausted"
        )
    signature = _signature(tool_name, args)
    if tracker.repeats(signature) >= _REPEAT_TRIP_AT - 1:
        raise GuardBlockedError(
            "repeated_call", f"{tool_name} called {_REPEAT_TRIP_AT}x with identical args"
        )
    tracker.record(signature)
    return "auto"
