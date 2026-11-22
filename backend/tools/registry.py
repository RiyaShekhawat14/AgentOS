from backend.tools import calculator, code, csv_reader, web_search
from backend.tools.base import Tool, ToolContext, ToolError, agent_data_dir

TOOLS: dict[str, Tool] = {m.TOOL.name: m.TOOL for m in (web_search, calculator, csv_reader, code)}


def get_tool(name: str) -> Tool:
    if name not in TOOLS:
        raise ToolError(f"Unknown tool '{name}'. Available tools: {', '.join(TOOLS)}")
    return TOOLS[name]


def describe(names) -> list[dict]:
    """Tool descriptions for the LLM prompt (only the tools this agent may use)."""
    return [{"name": t.name, "description": t.description, "args": t.args}
            for t in (TOOLS[n] for n in names if n in TOOLS)]


def run_tool(name: str, args: dict, agent_id: int):
    """Run one tool. Returns {"ok": True, "result": ...} or {"ok": False, "error": "..."}.

    Never raises, so one bad tool call cannot crash a run.
    """
    try:
        tool = get_tool(name)
        if not isinstance(args, dict):
            raise ToolError("Tool arguments must be an object.")
        result = tool.run(args, ToolContext(agent_id=agent_id, data_dir=agent_data_dir(agent_id)))
        return {"ok": True, "result": result}
    except ToolError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # a tool bug must not stop the whole run
        return {"ok": False, "error": f"{name} failed: {e}"}
