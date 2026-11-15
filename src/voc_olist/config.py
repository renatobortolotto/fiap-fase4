"""Configuração local explícita, sem dependência de nuvem."""
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    root: Path
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_revision: str | None = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    provider: str = "ollama"
    llm_model: str = "qwen2.5:3b"
    llm_revision: str | None = None
    ollama_url: str = "http://127.0.0.1:11434"
    timeout: int = 180
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
        load_dotenv(root / ".env", override=False)
        provider = os.getenv("LLM_PROVIDER", "ollama")
        default_model = "Qwen/Qwen2.5-0.5B-Instruct" if provider == "transformers" else "qwen2.5:3b"
        result = cls(
            root=root,
            embedding_model=os.getenv("EMBEDDING_MODEL", cls.embedding_model),
            embedding_revision=os.getenv("EMBEDDING_REVISION", cls.embedding_revision) or None,
            provider=provider,
            llm_model=os.getenv("LLM_MODEL", default_model),
            llm_revision=os.getenv("LLM_REVISION") or None,
            ollama_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
            timeout=int(os.getenv("LLM_TIMEOUT", "180")),
            min_similarity=float(os.getenv("MIN_SIMILARITY", "0.75")),
            min_evidences=int(os.getenv("MIN_EVIDENCES", "2")),
            top_k=int(os.getenv("TOP_K", "8")),
            retrieval_mode=os.getenv("RETRIEVAL_MODE", "hybrid"),
        )
        if not -1 <= result.min_similarity <= 1 or result.min_evidences < 1 or result.top_k < result.min_evidences:
            raise ValueError("Configuração inválida: limiar entre -1 e 1; TOP_K >= MIN_EVIDENCES >= 1.")
        if result.retrieval_mode not in {"hybrid", "dense"}:
            raise ValueError("RETRIEVAL_MODE deve ser hybrid ou dense.")
        return result
