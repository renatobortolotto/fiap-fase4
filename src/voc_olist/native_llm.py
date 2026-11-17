"""Servidor llama.cpp portátil, restrito ao loopback e gerenciado pela aplicação."""
from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from .llm import GenerationError, parse_json, response_schema
from .native_runtime import ensure_native_runtime, MODEL_NAME, MODEL_REVISION


class NativeGenerator:
    def __init__(self, cache_dir: Path, model=MODEL_NAME, revision=MODEL_REVISION, timeout=180, threads=4):
        if model != MODEL_NAME or revision != MODEL_REVISION:
            raise ValueError("O provedor nativo usa o modelo e a revisão fixados. Para outros modelos use Ollama ou Transformers.")
        self.cache_dir, self.model, self.revision = Path(cache_dir), model, revision
        self.timeout, self.threads = timeout, threads
        self._process = None
        self._base_url = None
        self._log_file = None
        self._lock = threading.Lock()
        atexit.register(self.close)

    def _start(self):
        if self._process is not None and self._process.poll() is None:
            return
        binary, model_file = ensure_native_runtime(self.cache_dir)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self._base_url = f"http://127.0.0.1:{port}"
        logs = self.cache_dir / "native" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        log_path = logs / f"server-{os.getpid()}-{port}.log"
        self._log_file = log_path.open("wb")
        args = [str(binary), "-m", str(model_file), "--alias", "voc-olist", "--host", "127.0.0.1",
                "--port", str(port), "-c", "8192", "-t", str(self.threads), "-tb", str(self.threads),
                "--parallel", "1"]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        try:
            self._process = subprocess.Popen(args, stdout=self._log_file, stderr=subprocess.STDOUT,
                                             cwd=binary.parent, creationflags=flags)
        except OSError as exc:
            self.close()
            raise GenerationError("Não foi possível iniciar o runtime portátil. Confira o log e o bloqueio do executável pelo Windows.") from exc
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                self._log_file.flush()
                tail = log_path.read_text(encoding="utf-8", errors="replace")[-1600:]
                self.close()
                raise GenerationError("O runtime local não iniciou. Detalhes: " + tail)
            try:
                with urlopen(self._base_url + "/health", timeout=2) as response:
                    if response.status == 200:
                        return
            except (URLError, HTTPError, TimeoutError):
                pass
            time.sleep(.2)
        self.close()
        raise GenerationError("O modelo local não ficou pronto no tempo configurado. Confira memória e LLM_TIMEOUT.")

    def generate(self, messages):
        with self._lock:
            self._start()
            payload = {"model": "voc-olist", "messages": messages, "temperature": 0, "max_tokens": 640,
                       "stream": False, "response_format": {"type": "json_object", "schema": response_schema(messages)}}
            request = Request(self._base_url + "/v1/chat/completions",
                              data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                              headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    result = json.load(response)
                return parse_json(result["choices"][0]["message"]["content"])
            except (URLError, HTTPError, TimeoutError) as exc:
                raise GenerationError("A geração local falhou ou excedeu o tempo configurado. Tente novamente com menos fontes.") from exc
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise GenerationError("O runtime local retornou uma resposta inesperada.") from exc

    def close(self):
        process, self._process = self._process, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None
