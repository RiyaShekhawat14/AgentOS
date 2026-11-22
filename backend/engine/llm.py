import json
import os
import urllib.error
import urllib.request

DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5"


class LLMError(Exception):
    """The language model could not be reached or gave an unusable answer."""


class OllamaLLM:
    """Talks to a local Ollama server (https://ollama.com)."""

    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: float = 180):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or DEFAULT_URL).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    def _call(self, path: str, payload: dict | None = None, timeout: float | None = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            if e.code == 404:
                raise LLMError(f"Model '{self.model}' is not installed. Run: ollama pull {self.model}")
            raise LLMError(f"Ollama returned an error ({e.code}): {detail}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            raise LLMError(f"Cannot reach Ollama at {self.base_url} ({e}). "
                           "Start it with: ollama serve")
        except ValueError:
            raise LLMError("Ollama sent an answer that could not be read.")

    def chat(self, messages: list[dict]) -> str:
        """Send the conversation and return the model's reply text (JSON mode)."""
        answer = self._call("/api/chat", {
            "model": self.model, "messages": messages, "stream": False, "format": "json",
            "options": {"temperature": 0.2},
        })
        text = (answer.get("message") or {}).get("content")
        if not isinstance(text, str) or not text.strip():
            raise LLMError("The model sent an empty answer.")
        return text

    def status(self) -> dict:
        """Used by the UI to show whether Ollama is ready."""
        try:
            models = [m.get("name", "") for m in self._call("/api/tags", timeout=5).get("models", [])]
        except LLMError as e:
            return {"ok": False, "model": self.model, "error": str(e)}
        installed = any(n == self.model or n.split(":")[0] == self.model.split(":")[0] for n in models)
        error = None if installed else f"Model '{self.model}' is not installed. Run: ollama pull {self.model}"
        return {"ok": installed, "model": self.model, "models": models, "error": error}


def get_llm() -> OllamaLLM:
    return OllamaLLM()
