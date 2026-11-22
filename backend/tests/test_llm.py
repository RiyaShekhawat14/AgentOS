import io
import json
import urllib.error

import pytest

from backend.engine import llm as llm_module
from backend.engine.llm import LLMError, OllamaLLM


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def reply(monkeypatch, body=None, error=None, seen=None):
    def fake_urlopen(request, timeout=None):
        if seen is not None:
            seen.append((request.full_url, json.loads(request.data) if request.data else None))
        if error:
            raise error
        return Response(json.dumps(body).encode())

    monkeypatch.setattr(llm_module.urllib.request, "urlopen", fake_urlopen)


def test_defaults_and_env(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    assert (OllamaLLM().base_url, OllamaLLM().model) == ("http://localhost:11434", "qwen2.5")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://box:1234/")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1")
    assert (OllamaLLM().base_url, OllamaLLM().model) == ("http://box:1234", "llama3.1")


def test_chat_sends_json_mode_and_returns_text(monkeypatch):
    seen = []
    reply(monkeypatch, {"message": {"content": '{"action": "final"}'}}, seen=seen)
    assert OllamaLLM("http://x:1", "m").chat([{"role": "user", "content": "hi"}]) == '{"action": "final"}'
    url, body = seen[0]
    assert url == "http://x:1/api/chat"
    assert body["model"] == "m" and body["format"] == "json" and body["stream"] is False


def test_chat_errors_are_readable(monkeypatch):
    reply(monkeypatch, error=urllib.error.URLError("refused"))
    with pytest.raises(LLMError, match="ollama serve"):
        OllamaLLM("http://x:1", "m").chat([])
    err = urllib.error.HTTPError("u", 404, "nf", {}, io.BytesIO(b'{"error":"model not found"}'))
    reply(monkeypatch, error=err)
    with pytest.raises(LLMError, match="ollama pull m"):
        OllamaLLM("http://x:1", "m").chat([])
    reply(monkeypatch, {"message": {"content": "  "}})
    with pytest.raises(LLMError, match="empty"):
        OllamaLLM("http://x:1", "m").chat([])


def test_status(monkeypatch):
    reply(monkeypatch, {"models": [{"name": "qwen2.5:latest"}, {"name": "llama3.1:8b"}]})
    ok = OllamaLLM("http://x:1", "qwen2.5").status()
    assert ok["ok"] is True and ok["error"] is None and "llama3.1:8b" in ok["models"]
    missing = OllamaLLM("http://x:1", "mistral").status()
    assert missing["ok"] is False and "ollama pull mistral" in missing["error"]
    reply(monkeypatch, error=urllib.error.URLError("refused"))
    down = OllamaLLM("http://x:1", "qwen2.5").status()
    assert down["ok"] is False and "Cannot reach Ollama" in down["error"]
