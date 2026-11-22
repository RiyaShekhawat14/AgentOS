import os
import subprocess
import sys
import tempfile

from backend.tools.base import Tool, ToolContext, ToolError

TIMEOUT_SECONDS = 10
MAX_CODE_LENGTH = 10_000
MAX_OUTPUT = 4_000
MEMORY_LIMIT = 256 * 1024 * 1024  # bytes


def _limits():  # runs in the child process before the code starts (Linux/macOS)
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000, 1_000_000))


def _cut(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT else text[:MAX_OUTPUT] + "\n...[output cut]"


def run(args: dict, ctx: ToolContext):
    code = str(args.get("code", ""))
    if not code.strip():
        raise ToolError("Give Python code in 'code' and print() the answer.")
    if len(code) > MAX_CODE_LENGTH:
        raise ToolError("Code is too long.")
    with tempfile.TemporaryDirectory(prefix="agentos_") as workdir:
        try:
            done = subprocess.run(
                [sys.executable, "-I", "-c", code],
                cwd=workdir, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"},
                preexec_fn=_limits if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            raise ToolError(f"Code took longer than {TIMEOUT_SECONDS} seconds and was stopped.")
    result = {"exit_code": done.returncode, "output": _cut(done.stdout)}
    if done.returncode != 0:
        raise ToolError(f"Code failed: {_cut(done.stderr).strip() or 'unknown error'}")
    if done.stderr.strip():
        result["warnings"] = _cut(done.stderr)
    return result


TOOL = Tool(
    name="code",
    description="Run a short Python script for calculations or data work. Use print() to show results. "
                "Runs in an empty temp folder with a 10 second and 256 MB limit.",
    args={"code": "Python code to run"},
    run=run,
)
