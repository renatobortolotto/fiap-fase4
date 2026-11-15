"""Adaptadores de geração local. Nenhuma chave ou serviço pago é necessário."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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
        "abstain": {"type": "boolean"},
        "reason": {"type": "string"},
        "claims": {"type": "array", "items": {
            "type": "object", "properties": {
                "text": {"type": "string"},
                "evidence_ids": {"type": "array", "items": {"type": "string"}},
            }, "required": ["text", "evidence_ids"], "additionalProperties": False,
        }},
    },
    "required": ["abstain", "reason", "claims"], "additionalProperties": False,
}


class OllamaGenerator:
    def __init__(self, model="qwen2.5:3b", base_url="http://127.0.0.1:11434", timeout=180):
        self.model, self.base_url, self.timeout = model, base_url.rstrip("/"), timeout

    def generate(self, messages: list[dict]) -> dict:
        payload = {"model": self.model, "messages": messages, "stream": False,
                   "format": SCHEMA, "options": {"temperature": 0, "num_predict": 700, "num_ctx": 8192}}
        request = Request(self.base_url + "/api/chat", data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
            return parse_json(result["message"]["content"])
        except (URLError, HTTPError, TimeoutError) as exc:
            raise GenerationError(
                "Ollama indisponível ou modelo ausente. Inicie o Ollama e execute "
                f"'ollama pull {self.model}', ou selecione o provedor transformers."
            ) from exc
        except (KeyError, json.JSONDecodeError) as exc:
            raise GenerationError("Resposta inesperada do servidor Ollama.") from exc


class TransformersGenerator:
    """Alternativa pequena para CPU; a qualidade deve ser avaliada separadamente."""
    def __init__(self, model="Qwen/Qwen2.5-0.5B-Instruct", revision=None, cache_dir: Path | None = None):
        self.model, self.revision, self.cache_dir = model, revision, cache_dir
        self._tokenizer = self._model = None

    def generate(self, messages: list[dict]) -> dict:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.set_num_threads(min(8, os.cpu_count() or 1))
        if self._model is None:
            options = {"revision": self.revision, "cache_dir": str(self.cache_dir) if self.cache_dir else None,
                       "trust_remote_code": False}
            self._tokenizer = AutoTokenizer.from_pretrained(self.model, **options)
            self._model = AutoModelForCausalLM.from_pretrained(self.model, **options, dtype=torch.float32).eval()
        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._tokenizer(prompt, return_tensors="pt")
        if inputs.input_ids.shape[1] > 7000:
            raise GenerationError("Contexto excedeu o limite local; diminua TOP_K ou o tamanho dos comentários.")
        with torch.inference_mode():
            output = self._model.generate(**inputs, max_new_tokens=384, do_sample=False,
                                          pad_token_id=self._tokenizer.eos_token_id)
        return parse_json(self._tokenizer.decode(output[0, inputs.input_ids.shape[1]:], skip_special_tokens=True))


def make_generator(settings):
    if settings.provider == "evidence":
        return None
    if settings.provider == "ollama":
        return OllamaGenerator(settings.llm_model, settings.ollama_url, settings.timeout)
    if settings.provider == "transformers":
        return TransformersGenerator(settings.llm_model, settings.llm_revision, settings.cache_dir)
    raise ValueError("LLM_PROVIDER deve ser ollama, transformers ou evidence.")
