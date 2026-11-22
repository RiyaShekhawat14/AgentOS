from dataclasses import dataclass
from typing import Iterable, Mapping

# What happens when the agent owner has not chosen a mode for a tool.
# Only `code` is risky enough to ask first.
DEFAULT_MODES = {
    "web_search": "auto",
    "calculator": "auto",
    "csv_reader": "auto",
    "code": "ask",
}
MODES = ("auto", "ask", "blocked")


@dataclass(frozen=True)
class Decision:
    mode: str  # auto = run now, ask = wait for a human, blocked = never run
    reason: str


def decide(enabled_tools: Iterable[str] | None, permissions: Mapping[str, str] | None,
           tool: str) -> Decision:
    """Decide what to do before a tool runs.

    The order matters: a tool the agent does not have is blocked first, then the
    owner's setting is used, then the default. Anything unknown is treated as
    'ask' (the safe choice), except unknown tool names, which are blocked.
    """
    if tool not in DEFAULT_MODES:
        return Decision("blocked", f"'{tool}' is not a known tool.")
    if tool not in (enabled_tools or []):
        return Decision("blocked", f"'{tool}' is not enabled for this agent.")
    chosen = (permissions or {}).get(tool)
    if chosen is None:
        return Decision(DEFAULT_MODES[tool], f"Default setting for '{tool}'.")
    if chosen not in MODES:
        return Decision("ask", f"Unknown permission '{chosen}' for '{tool}', so a human must approve.")
    return Decision(chosen, f"Agent setting for '{tool}'.")
