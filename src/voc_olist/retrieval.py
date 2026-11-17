"""Embeddings E5 e busca por cosseno em um índice local verificável.

Uma matriz NumPy é suficiente para esta base: preserva o ranking exato, permite
filtrar todos os documentos antes da busca e evita um serviço vetorial externo.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
from .model_store import local_model_path

logger = logging.getLogger(__name__)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalizar(vectors: Any, *, expected_rows: int | None = None) -> np.ndarray:
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] == 0:
        raise ValueError("Embeddings devem formar uma matriz com dimensão positiva.")
    if expected_rows is not None and matrix.shape[0] != expected_rows:
        raise ValueError("Quantidade de embeddings difere da quantidade de documentos.")
    if not np.isfinite(matrix).all():
        raise ValueError("Embeddings contêm valores não finitos.")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if (norms <= 0).any() or not np.isfinite(norms).all():
        raise ValueError("Embeddings não podem conter vetores nulos ou inválidos.")
    return np.ascontiguousarray(matrix / norms, dtype=np.float32)


def _ler_documentos(path: Path) -> list[dict[str, Any]]:
    documents = []
    with path.open(encoding="utf-8-sig") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                document = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido na linha {number} dos documentos.") from exc
            if not isinstance(document, dict):
                raise ValueError(f"Documento na linha {number} deve ser um objeto JSON.")
            if not isinstance(document.get("text"), str) or not document["text"].strip():
                raise ValueError(f"Documento na linha {number} não tem texto válido.")
            documents.append(document)
    if not documents:
        raise ValueError("A base de documentos está vazia.")
    return documents


class SentenceEmbedder:
    """Carrega o modelo somente na primeira codificação, sempre em CPU.

    O E5 espera os prefixos em inglês inclusive para conteúdo em português.
    A revisão pode fixar um commit do Hugging Face para maior reprodutibilidade.
    """

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-small",
        revision: str | None = None,
        cache_dir: str | Path | None = None,
        threads: int = 4,
    ) -> None:
        self.model_name = model_name
        self.revision = revision
        self.cache_dir = cache_dir
        self.threads = threads
        self._model = None

    def _carregar(self):
        if self._model is None:
            try:
                import torch
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ValueError("Instale sentence-transformers para criar ou consultar embeddings.") from exc
            # Em máquinas com muitos núcleos, os pequenos lotes de avaliações
            # podem ficar mais lentos pelo excesso de threads concorrentes.
            torch.set_num_threads(min(self.threads, os.cpu_count() or 1))
            path = local_model_path(self.model_name, self.revision, Path(self.cache_dir or ".cache/huggingface"))
            self._model = SentenceTransformer(str(path), device="cpu", trust_remote_code=False, local_files_only=True)
        return self._model

    def _encode(self, texts: list[str], prefix: str) -> np.ndarray:
        if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Informe textos não vazios para criar embeddings.")
        result = self._carregar().encode(
            [prefix + text.strip() for text in texts],
            batch_size=64,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return _normalizar(result, expected_rows=len(texts))

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        return self._encode(texts, "passage: ")

    def encode_query(self, question: str) -> np.ndarray:
        return self._encode([question], "query: ")[0]


def _validar_filtros(filters: dict[str, Any] | None) -> dict[str, Any]:
    active = {key: value for key, value in (filters or {}).items() if value is not None}
    unknown = set(active) - {"score_min", "score_max", "date_from", "date_to", "category", "delivered_late"}
    if unknown:
        raise ValueError("Filtros desconhecidos: " + ", ".join(sorted(unknown)))
    for key in ("score_min", "score_max"):
        value = active.get(key)
        if value is not None and (type(value) is not int or not 1 <= value <= 5):
            raise ValueError("Filtros de nota devem ser inteiros entre 1 e 5.")
    if active.get("score_min", 1) > active.get("score_max", 5):
        raise ValueError("A nota mínima não pode superar a nota máxima.")
    for key in ("date_from", "date_to"):
        if key in active:
            try:
                active[key] = date.fromisoformat(active[key])
            except (TypeError, ValueError) as exc:
                raise ValueError("Filtros de data devem usar YYYY-MM-DD.") from exc
    if "date_from" in active and "date_to" in active and active["date_from"] > active["date_to"]:
        raise ValueError("A data inicial não pode superar a data final.")
    if "category" in active:
        if not isinstance(active["category"], str) or not active["category"].strip():
            raise ValueError("A categoria deve ser um texto não vazio.")
        active["category"] = active["category"].strip().casefold()
    if "delivered_late" in active and type(active["delivered_late"]) is not bool:
        raise ValueError("O filtro de atraso deve ser verdadeiro ou falso.")
    return active


def _corresponde(document: dict[str, Any], filters: dict[str, Any]) -> bool:
    if "score_min" in filters or "score_max" in filters:
        score = document.get("score")
        if type(score) is not int or not filters.get("score_min", 1) <= score <= filters.get("score_max", 5):
            return False
    if "date_from" in filters or "date_to" in filters:
        value = document.get("purchase_date")
        try:
            purchase_date = date.fromisoformat(value[:10]) if isinstance(value, str) else None
        except ValueError:
            purchase_date = None
        if purchase_date is None:
            return False
        if purchase_date < filters.get("date_from", date.min) or purchase_date > filters.get("date_to", date.max):
            return False
    if "category" in filters:
        categories = document.get("categories", document.get("category", []))
        if isinstance(categories, str):
            categories = [categories]
        if not isinstance(categories, list) or filters["category"] not in {
            item.casefold() for item in categories if isinstance(item, str)
        }:
            return False
    if "delivered_late" in filters and document.get("delivered_late") is not filters["delivered_late"]:
        return False
    return True


@dataclass
class VectorIndex:
    documents: list[dict[str, Any]]
    vectors: np.ndarray
    manifest: dict[str, Any]

    @classmethod
    def build(
        cls,
        documents_path: Path,
        index_dir: Path,
        embedder,
        batch_size: int = 64,
    ) -> dict[str, Any]:
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("O tamanho do lote deve ser um inteiro positivo.")
        if not isinstance(getattr(embedder, "model_name", None), str):
            raise ValueError("O gerador de embeddings deve informar model_name.")
        documents_path, index_dir = Path(documents_path), Path(index_dir)
        source_sha256 = _sha256(documents_path)
        documents = _ler_documentos(documents_path)
        # Repeated wording remains a distinct review in the corpus. Only the
        # expensive encoding is shared for exactly identical strings. Length
        # sorting reduces padding within CPU batches; the mapping below restores
        # one vector per document in its original, traceable source order.
        unique_texts = sorted({document["text"] for document in documents}, key=lambda text: (len(text), text))
        text_rows = {text: row for row, text in enumerate(unique_texts)}
        batches = []
        dimension = None
        next_progress = 1024
        for start in range(0, len(unique_texts), batch_size):
            texts = unique_texts[start:start + batch_size]
            batch = _normalizar(embedder.encode_documents(texts), expected_rows=len(texts))
            if dimension is not None and batch.shape[1] != dimension:
                raise ValueError("A dimensão dos embeddings mudou entre os lotes.")
            dimension = batch.shape[1]
            batches.append(batch)
            completed = start + len(texts)
            if completed >= next_progress or completed == len(unique_texts):
                logger.info("Embeddings: %s/%s textos únicos (%s documentos)", completed, len(unique_texts), len(documents))
                next_progress = (completed // 1024 + 1) * 1024
        unique_vectors = np.concatenate(batches, axis=0)
        document_rows = np.fromiter((text_rows[document["text"]] for document in documents), dtype=np.intp, count=len(documents))
        vectors = np.ascontiguousarray(unique_vectors[document_rows], dtype=np.float32)
        index_dir.mkdir(parents=True, exist_ok=True)
        # O manifesto é substituído por último: cargas concorrentes ou uma escrita
        # interrompida não poderão aceitar silenciosamente arquivos incompatíveis.
        with tempfile.TemporaryDirectory(prefix="build-", dir=index_dir) as temp:
            stage = Path(temp)
            docs_path, vectors_path = stage / "docs.jsonl", stage / "vectors.npy"
            with docs_path.open("w", encoding="utf-8", newline="\n") as stream:
                for document in documents:
                    stream.write(json.dumps(document, ensure_ascii=False, allow_nan=False) + "\n")
            np.save(vectors_path, vectors, allow_pickle=False)
            manifest = {
                "schema_version": 1,
                "model_name": embedder.model_name,
                "revision": getattr(embedder, "revision", None),
                "shape": list(vectors.shape),
                "document_count": len(documents),
                "n_unique_texts": len(unique_texts),
                "batching_strategy": "exact_unique_texts_sorted_by_length_then_text",
                "dimensions": int(vectors.shape[1]),
                "source_sha256": source_sha256,
                "docs_sha256": _sha256(docs_path),
                "vectors_sha256": _sha256(vectors_path),
            }
            (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            for name in ("docs.jsonl", "vectors.npy", "manifest.json"):
                (stage / name).replace(index_dir / name)
        return manifest

    @classmethod
    def load(cls, index_dir: Path) -> "VectorIndex":
        index_dir = Path(index_dir)
        try:
            manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Índice indisponível ou manifesto inválido; reconstrua o índice.") from exc
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
            raise ValueError("Versão do manifesto inválida; reconstrua o índice.")
        for name, key in (("docs.jsonl", "docs_sha256"), ("vectors.npy", "vectors_sha256")):
            try:
                valid = _sha256(index_dir / name) == manifest.get(key)
            except OSError as exc:
                raise ValueError(f"Arquivo {name} ausente; reconstrua o índice.") from exc
            if not valid:
                raise ValueError(f"Integridade de {name} inválida; reconstrua o índice.")
        documents = _ler_documentos(index_dir / "docs.jsonl")
        try:
            vectors = np.load(index_dir / "vectors.npy", allow_pickle=False)
        except (ValueError, OSError) as exc:
            raise ValueError("Matriz vetorial inválida; reconstrua o índice.") from exc
        if vectors.ndim != 2 or vectors.shape[0] != len(documents) or vectors.shape[1] < 1:
            raise ValueError("Dimensões dos vetores e documentos são incompatíveis.")
        if list(vectors.shape) != manifest.get("shape") or len(documents) != manifest.get("document_count"):
            raise ValueError("Dimensões do índice diferem do manifesto.")
        if vectors.shape[1] != manifest.get("dimensions") or vectors.dtype != np.float32:
            raise ValueError("Dimensão ou tipo dos vetores difere do manifesto.")
        if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4):
            raise ValueError("O índice contém embeddings não finitos ou não normalizados.")
        if not isinstance(manifest.get("model_name"), str) or not manifest["model_name"]:
            raise ValueError("O manifesto não identifica o modelo de embeddings.")
        return cls(documents=documents, vectors=vectors, manifest=manifest)

    def search(
        self,
        question: str,
        embedder,
        top_k: int = 8,
        filters: dict[str, Any] | None = None,
        min_similarity: float = 0.75,
    ) -> list[dict[str, Any]]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Informe uma pergunta não vazia.")
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k deve ser um inteiro positivo.")
        if not isinstance(min_similarity, (int, float)) or not math.isfinite(min_similarity) or not -1 <= min_similarity <= 1:
            raise ValueError("O limiar de similaridade deve estar entre -1 e 1.")
        if getattr(embedder, "model_name", None) != self.manifest["model_name"] or getattr(embedder, "revision", None) != self.manifest.get("revision"):
            raise ValueError("Modelo ou revisão de embeddings difere do índice; use o mesmo modelo ou reconstrua o índice.")
        active = _validar_filtros(filters)
        candidates = np.asarray([i for i, document in enumerate(self.documents) if _corresponde(document, active)], dtype=np.int64)
        if candidates.size == 0:
            return []
        query = np.asarray(embedder.encode_query(question.strip()), dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != self.vectors.shape[1]:
            raise ValueError("Dimensão do embedding da pergunta difere do índice.")
        query = _normalizar(query.reshape(1, -1))[0]
        similarities = np.clip(self.vectors[candidates] @ query, -1.0, 1.0)
        # Ordenação estável mantém um desempate reproduzível pela ordem da fonte.
        order = np.argsort(-similarities, kind="stable")
        results, seen = [], set()
        for position in order:
            similarity = float(similarities[position])
            if similarity < min_similarity:
                break
            document = self.documents[int(candidates[position])]
            text_key = " ".join(document["text"].casefold().split())
            if text_key in seen:
                continue
            seen.add(text_key)
            results.append({"document": document, "similarity": similarity})
            if len(results) == top_k:
                break
        return results
