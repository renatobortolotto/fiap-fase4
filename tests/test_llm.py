import io
import json
from urllib.error import URLError

import pytest

import voc_olist.llm as llm


def test_ollama_contract_nonstreaming_and_json_schema(monkeypatch):
    captured = {}
    def request(req, timeout):
        captured.update(url=req.full_url, payload=json.loads(req.data), timeout=timeout)
        return io.BytesIO(json.dumps({"message": {"content": '{"abstain":true,"reason":"sem suporte","claims":[]}'}}).encode())
    monkeypatch.setattr(llm, "urlopen", request)
    result = llm.OllamaGenerator("fixture-model", "http://localhost:11434/", 9).generate([
        {"role": "user", "content": "Pergunta"}])
    assert result["abstain"] is True
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["format"]["type"] == "object"
    assert captured["payload"]["model"] == "fixture-model" and captured["timeout"] == 9


def test_ollama_unavailable_has_actionable_error(monkeypatch):
    def unavailable(*args, **kwargs):
        raise URLError("offline fixture")
    monkeypatch.setattr(llm, "urlopen", unavailable)
    with pytest.raises(llm.GenerationError, match="ollama pull"):
        llm.OllamaGenerator().generate([])


def test_ollama_nontext_content_is_rejected(monkeypatch):
    monkeypatch.setattr(llm, "urlopen", lambda *a, **k: io.BytesIO(b'{"message":{"content":null}}'))
    with pytest.raises(llm.GenerationError):
        llm.OllamaGenerator().generate([])
