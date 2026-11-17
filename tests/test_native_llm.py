import io
import json
import subprocess
from unittest.mock import Mock
from urllib.error import URLError

import pytest

import voc_olist.native_llm as native
from voc_olist.llm import GenerationError


@pytest.fixture
def generator(tmp_path, monkeypatch):
    monkeypatch.setattr(native.atexit, "register", lambda _: None)
    return native.NativeGenerator(tmp_path)


def test_runtime_requires_the_verified_model(generator):
    with pytest.raises(ValueError, match="fixados"):
        native.NativeGenerator(generator.cache_dir, model="unverified")


def test_schema_request_binds_quote_to_its_source_and_uses_loopback(generator, monkeypatch):
    monkeypatch.setattr(generator, "_start", lambda: None)
    generator._base_url = "http://127.0.0.1:12345"
    captured = {}
    def request(req, timeout):
        captured.update(url=req.full_url, data=json.loads(req.data), timeout=timeout)
        return io.BytesIO(b'{"choices":[{"message":{"content":"{\\"findings\\":[],\\"examples\\":[]}"}}]}')
    monkeypatch.setattr(native, "urlopen", request)
    result = generator.generate([{"role": "user", "content": json.dumps({"evidence": [
        {"id": "E2", "text": "A caixa veio quebrada."}]})}])
    assert result == {"findings": [], "examples": []}
    assert captured["url"] == "http://127.0.0.1:12345/v1/chat/completions"
    fmt = captured["data"]["response_format"]
    assert fmt["type"] == "json_object"
    item = fmt["schema"]["properties"]["examples"]["items"]["anyOf"][0]
    assert item["properties"]["evidence_id"]["enum"] == ["E2"]
    assert item["properties"]["quote"]["enum"] == ["A caixa veio quebrada."]


@pytest.mark.parametrize("response", [b'{}', b'{"choices":[]}', b'not-json',
    b'{"choices":[{"message":{"content":null}}]}'])
def test_unusable_server_output_never_becomes_a_response(generator, monkeypatch, response):
    monkeypatch.setattr(generator, "_start", lambda: None)
    generator._base_url = "http://127.0.0.1:12345"
    monkeypatch.setattr(native, "urlopen", lambda *a, **k: io.BytesIO(response))
    with pytest.raises(GenerationError):
        generator.generate([])


def test_server_transport_failure_becomes_an_actionable_error(generator, monkeypatch):
    monkeypatch.setattr(generator, "_start", lambda: None)
    generator._base_url = "http://127.0.0.1:12345"
    def offline(*a, **k):
        raise URLError("fixture offline")
    monkeypatch.setattr(native, "urlopen", offline)
    with pytest.raises(GenerationError, match="tempo configurado"):
        generator.generate([])


def test_start_binds_only_loopback_and_does_not_restart_a_healthy_owned_process(generator, monkeypatch, tmp_path):
    binary, model = tmp_path / "llama-server.exe", tmp_path / "model.gguf"
    monkeypatch.setattr(native, "ensure_native_runtime", lambda _: (binary, model))
    probe = Mock()
    probe.getsockname.return_value = ("127.0.0.1", 45678)
    context = Mock()
    context.__enter__ = Mock(return_value=probe)
    context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(native.socket, "socket", lambda: context)
    process = Mock()
    process.poll.return_value = None
    launch = Mock(return_value=process)
    monkeypatch.setattr(native.subprocess, "Popen", launch)
    health = Mock()
    health.status = 200
    health.__enter__ = Mock(return_value=health)
    health.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(native, "urlopen", lambda *a, **k: health)
    generator._start()
    generator._start()
    probe.bind.assert_called_once_with(("127.0.0.1", 0))
    launch.assert_called_once()
    args = launch.call_args.args[0]
    assert args[args.index("--host") + 1] == "127.0.0.1"
    assert args[args.index("--port") + 1] == "45678"
    generator.close()
    process.terminate.assert_called_once()


def test_failed_start_releases_own_process_and_log(generator, monkeypatch, tmp_path):
    monkeypatch.setattr(native, "ensure_native_runtime", lambda _: (tmp_path / "server.exe", tmp_path / "model.gguf"))
    probe = Mock()
    probe.getsockname.return_value = ("127.0.0.1", 45678)
    probe.__enter__ = Mock(return_value=probe)
    probe.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(native.socket, "socket", lambda: probe)
    process = Mock()
    process.poll.return_value = 1
    monkeypatch.setattr(native.subprocess, "Popen", lambda *a, **k: process)
    with pytest.raises(GenerationError, match="não iniciou"):
        generator._start()
    assert generator._process is None and generator._log_file is None
    process.terminate.assert_not_called()


def test_close_kills_only_its_unresponsive_child_and_is_idempotent(generator):
    process = Mock()
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired("fixture", 5), None]
    generator._process = process
    generator._log_file = io.BytesIO()
    generator.close()
    generator.close()
    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    assert generator._process is None and generator._log_file is None


def test_windows_launch_denial_releases_the_log(generator, monkeypatch, tmp_path):
    monkeypatch.setattr(native, "ensure_native_runtime", lambda _: (tmp_path / "server.exe", tmp_path / "model.gguf"))
    probe = Mock()
    probe.getsockname.return_value = ("127.0.0.1", 45678)
    probe.__enter__ = Mock(return_value=probe)
    probe.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(native.socket, "socket", lambda: probe)
    def denied(*a, **k):
        raise PermissionError("fixture Windows denied executable")
    monkeypatch.setattr(native.subprocess, "Popen", denied)
    with pytest.raises(GenerationError, match="iniciar o runtime"):
        generator._start()
    assert generator._process is None and generator._log_file is None
