"""Configuração local explícita, sem dependência de nuvem."""
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M"
DEFAULT_LLM_REVISION = "bb5d59e06d9551d752d08b292a50eb208b07ab1f"
TRANSFORMERS_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
TRANSFORMERS_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"


def generation_defaults(provider: str) -> tuple[str, str | None]:
    if provider == "transformers":
        return TRANSFORMERS_MODEL, TRANSFORMERS_REVISION
    if provider == "native":
        return DEFAULT_LLM_MODEL, DEFAULT_LLM_REVISION
    return "qwen2.5:3b", None


@dataclass(frozen=True)
class Settings:
    root: Path
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_revision: str | None = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    embedding_threads: int = 4
    provider: str = "native"
    llm_model: str = DEFAULT_LLM_MODEL
    llm_revision: str | None = DEFAULT_LLM_REVISION
    ollama_url: str = "http://127.0.0.1:11434"
    timeout: int = 180
    llm_threads: int = 4
    min_similarity: float = 0.75
    min_evidences: int = 2
    top_k: int = 8
    retrieval_mode: str = "hybrid"

    @property
    def raw_dir(self):
        return self.root / "data" / "raw"

    @property
    def processed_dir(self):
        return self.root / "data" / "processed"

    @property
    def index_dir(self):
        return self.root / "artifacts" / "index"

    @property
    def cache_dir(self):
        return self.root / ".cache" / "huggingface"

    @classmethod
    def from_env(cls, root: Path | None = None):
        root = (root or Path(os.environ.get("VOC_PROJECT_ROOT", Path(__file__).resolve().parents[2]))).resolve()
        # Ler um projeto não altera o ambiente de outro projeto na mesma sessão.
        values = {**dotenv_values(root / ".env"), **os.environ}
        provider = values.get("LLM_PROVIDER", "native")
        default_model, default_revision = generation_defaults(provider)
        chosen_model = values.get("LLM_MODEL", default_model)
        if chosen_model != default_model:
            default_revision = None
        result = cls(
            root=root,
            embedding_model=values.get("EMBEDDING_MODEL", cls.embedding_model),
            embedding_revision=values.get("EMBEDDING_REVISION", cls.embedding_revision) or None,
            embedding_threads=int(values.get("EMBEDDING_THREADS", "4")),
            provider=provider,
            llm_model=chosen_model,
            llm_revision=values.get("LLM_REVISION", default_revision) or None,
            ollama_url=values.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
            timeout=int(values.get("LLM_TIMEOUT", "180")),
            llm_threads=int(values.get("LLM_THREADS", "4")),
            min_similarity=float(values.get("MIN_SIMILARITY", "0.75")),
            min_evidences=int(values.get("MIN_EVIDENCES", "2")),
            top_k=int(values.get("TOP_K", "8")),
            retrieval_mode=values.get("RETRIEVAL_MODE", "hybrid"),
        )
        if not -1 <= result.min_similarity <= 1 or result.min_evidences < 1 or result.top_k < result.min_evidences:
            raise ValueError("Configuração inválida: limiar entre -1 e 1; TOP_K >= MIN_EVIDENCES >= 1.")
        if result.retrieval_mode not in {"hybrid", "dense"}:
            raise ValueError("RETRIEVAL_MODE deve ser hybrid ou dense.")
        if result.provider not in {"native", "transformers", "ollama", "evidence"} or result.timeout < 1 or min(result.llm_threads, result.embedding_threads) < 1:
            raise ValueError("Provedor inválido; timeout e threads devem ser positivos.")
        return result
