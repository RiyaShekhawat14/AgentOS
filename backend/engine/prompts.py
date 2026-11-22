import json
import re

PLAN_REQUEST = (
    "Before acting, write a short plan (2 to 5 steps). "
    'Reply with JSON only: {"plan": ["step 1", "step 2"]}'
)
FORMAT_REMINDER = (
    "Your last reply was not valid. Reply with ONE JSON object only, either "
    '{"action": "tool", "thought": "...", "tool": "<name>", "args": {...}} or '
    '{"action": "final", "answer": "..."}.'
)
FORCE_FINAL = (
    "You have used all the tool calls you are allowed. Give your best final answer now from what "
    'you already know. Reply with JSON only: {"action": "final", "answer": "..."}'
)
OBSERVATION_LIMIT = 2000


def build_system_prompt(instructions: str, tools: list[dict], memory: list[dict], docs: list[dict]) -> str:
    parts = ["You are an autonomous operations agent working for a user. "
             "Do the task step by step and be accurate."]
    if instructions.strip():
        parts.append("Instructions from the agent owner:\n" + instructions.strip())
    if tools:
        lines = [f"- {t['name']}: {t['description']} Arguments: {json.dumps(t['args'])}" for t in tools]
        parts.append("You can use these tools:\n" + "\n".join(lines))
    else:
        parts.append("You have no tools. Answer directly.")
    if memory:
        parts.append("What you remember from earlier runs:\n" +
                     "\n".join(f"- ({m['kind']}) {m['content']}" for m in memory))
    if docs:
        parts.append("Relevant text from the user's documents:\n" +
                     "\n".join(f"[{d['source']}] {d['text'][:600]}" for d in docs))
    parts.append(
        "Always reply with ONE JSON object and nothing else.\n"
        'To use a tool: {"action": "tool", "thought": "why", "tool": "<name>", "args": {...}}\n'
        'To finish: {"action": "final", "answer": "<clear answer for the user>", '
        '"remember": "<optional fact worth keeping for the future>"}\n'
        "Rules: use tools for maths and data instead of guessing. If a tool fails, read the error "
        "and fix your input or try another way. Never invent data.")
    return "\n\n".join(parts)


def shorten(value, limit: int = OBSERVATION_LIMIT) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + "...[cut]"


def parse_json(text: str):
    """Return a dict from the model's reply, even when it added text around the JSON."""
    text = (text or "").strip()
    for candidate in (text, _between_braces(text)):
        if candidate:
            try:
                value = json.loads(candidate)
            except ValueError:
                continue
            if isinstance(value, dict):
                return value
    return None


def _between_braces(text: str):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else None


def check_action(data) -> str | None:
    """None when the reply is a usable action, otherwise a short reason."""
    if not isinstance(data, dict):
        return "not a JSON object"
    if data.get("action") == "final":
        return None if isinstance(data.get("answer"), str) and data["answer"].strip() else "empty answer"
    if data.get("action") == "tool":
        if not isinstance(data.get("tool"), str) or not data["tool"].strip():
            return "missing tool name"
        if data.get("args") not in (None, {}) and not isinstance(data.get("args"), dict):
            return "args must be an object"
        return None
    return "action must be 'tool' or 'final'"
