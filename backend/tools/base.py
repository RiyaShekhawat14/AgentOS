import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def storage_dir() -> Path:
    """Folder where uploaded CSV files live (one sub-folder per agent)."""
    return Path(os.getenv("STORAGE_DIR") or Path(__file__).resolve().parents[1] / "storage")


def agent_data_dir(agent_id: int) -> Path:
    return storage_dir() / f"agent_{agent_id}"


class ToolError(Exception):
    """A problem the agent can understand and react to (bad input, missing file...)."""


@dataclass
class ToolContext:
    agent_id: int
    data_dir: Path


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args: dict  # argument name -> short help text, shown to the LLM
    run: Callable[[dict, ToolContext], Any]
