"""Adaptadores de geração local. Nenhuma chave ou serviço pago é necessário."""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import TRANSFORMERS_MODEL, TRANSFORMERS_REVISION
from .model_store import local_model_path


class GenerationError(RuntimeError):
    pass


def parse_json(text: str) -> dict:
    if not isinstance(text, str):
        raise GenerationError("O modelo retornou conteúdo sem texto válido.")
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1).removesuffix("```").strip()
    try:
        result = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise GenerationError("O modelo não retornou JSON válido; nenhuma conclusão foi publicada.") from exc
    if not isinstance(result, dict):
        raise GenerationError("O modelo deve retornar um objeto JSON.")
    return result


SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {"type": "array", "maxItems": 2, "items": {"type": "string", "maxLength": 220}},
        "examples": {"type": "array", "maxItems": 2, "items": {
            "type": "object", "properties": {"evidence_id": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["evidence_id", "quote"], "additionalProperties": False}},
    },
    "required": ["findings", "examples"], "additionalProperties": False,
}


def response_schema(messages):
    """Restringe IDs aos documentos desta consulta, sem confundir isso com suporte."""
    schema = deepcopy(SCHEMA)
    try:
        bodies = [json.loads(m["content"]) for m in messages if m["role"] == "user"]
        body = next(b for b in bodies if isinstance(b, dict) and "evidence" in b)
        ids = [e["id"] for e in body.get("evidence", []) if isinstance(e.get("id"), str)]
    except (StopIteration, ValueError, TypeError, KeyError):
        ids = []
    if ids:
        # O decoder escolhe trechos de origem; não precisa reconstruí-los palavra
        # por palavra. Cada alternativa vincula o trecho à fonte correta.
        alternatives = []
        for source in body["evidence"]:
            text = source.get("text", "")
            if not isinstance(text, str) or not text:
                continue
            pieces = [p.strip() for p in re.split(r"(?<=[.!?])\s+|\n+", text) if len(p.strip()) >= 3]
            choices = list(dict.fromkeys(pieces + [text]))
            alternatives.append({"type": "object", "properties": {
                "evidence_id": {"type": "string", "enum": [source["id"]]},
                "quote": {"type": "string", "enum": choices}},
                "required": ["evidence_id", "quote"], "additionalProperties": False})
        schema["properties"]["examples"]["items"] = {"anyOf": alternatives}
    return schema


class OllamaGenerator:
    def __init__(self, model="qwen2.5:3b", base_url="http://127.0.0.1:11434", timeout=180):
        self.model, self.base_url, self.timeout = model, base_url.rstrip("/"), timeout

    def generate(self, messages: list[dict]) -> dict:
        payload = {"model": self.model, "messages": messages, "stream": False,
                   "format": response_schema(messages), "options": {"temperature": 0, "num_predict": 640, "num_ctx": 8192}}
        request = Request(self.base_url + "/api/chat", data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
            return parse_json(result["message"]["content"])
        except (URLError, HTTPError, TimeoutError) as exc:
            raise GenerationError(
                "Ollama indisponível ou modelo ausente. Inicie o Ollama e execute "
                f"'ollama pull {self.model}', ou selecione o modo RAG local."
            ) from exc
        except (KeyError, json.JSONDecodeError) as exc:
            raise GenerationError("Resposta inesperada do servidor Ollama.") from exc


class TransformersGenerator:
    """Alternativa pequena para CPU; a qualidade deve ser avaliada separadamente."""
    def __init__(self, model=TRANSFORMERS_MODEL, revision=TRANSFORMERS_REVISION, cache_dir: Path | None = None,
                 timeout=180, threads=4):
        self.model, self.revision, self.cache_dir = model, revision, cache_dir
        self._tokenizer = self._model = None
        self.timeout, self.threads = timeout, threads
        self._tokenizer_data = None

    def generate(self, messages: list[dict]) -> dict:
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from lmformatenforcer import JsonSchemaParser
        from lmformatenforcer.integrations.transformers import (
            build_transformers_prefix_allowed_tokens_fn, build_token_enforcer_tokenizer_data)

        torch.set_num_threads(min(self.threads, os.cpu_count() or 1))
        if self._model is None:
            path = local_model_path(self.model, self.revision, Path(self.cache_dir or ".cache/huggingface"))
            options = {"trust_remote_code": False, "local_files_only": True}
            self._tokenizer = AutoTokenizer.from_pretrained(path, **options)
            self._model = AutoModelForCausalLM.from_pretrained(path, **options, dtype=torch.float32, use_safetensors=True).eval()
            self._tokenizer_data = build_token_enforcer_tokenizer_data(self._tokenizer)
        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._tokenizer(prompt, return_tensors="pt")
        if inputs.input_ids.shape[1] > 7000:
            raise GenerationError("Contexto excedeu o limite local; diminua TOP_K ou o tamanho dos comentários.")
        parser = JsonSchemaParser(response_schema(messages))
        prefix_fn = build_transformers_prefix_allowed_tokens_fn(self._tokenizer_data, parser)
        with torch.inference_mode():
            output = self._model.generate(**inputs, max_new_tokens=640, max_time=self.timeout, do_sample=False,
                                          temperature=None, top_p=None, top_k=None,
                                          prefix_allowed_tokens_fn=prefix_fn,
                                          pad_token_id=self._tokenizer.eos_token_id)
        return parse_json(self._tokenizer.decode(output[0, inputs.input_ids.shape[1]:], skip_special_tokens=True))


def make_generator(settings):
    if settings.provider == "native":
        from .native_llm import NativeGenerator
        return NativeGenerator(settings.root / ".cache", settings.llm_model, settings.llm_revision,
                               settings.timeout, settings.llm_threads)
    if settings.provider == "evidence":
        return None
    if settings.provider == "ollama":
        return OllamaGenerator(settings.llm_model, settings.ollama_url, settings.timeout)
    if settings.provider == "transformers":
        return TransformersGenerator(settings.llm_model, settings.llm_revision, settings.cache_dir,
                                     settings.timeout, settings.llm_threads)
    raise ValueError("LLM_PROVIDER deve ser native, ollama, transformers ou evidence.")
