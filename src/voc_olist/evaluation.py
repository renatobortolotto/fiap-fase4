"""Avaliação da recuperação sobre rótulos fornecidos, sem chamar um LLM.

Os resultados não medem sustentação semântica da geração. Rótulos parciais
também não permitem afirmar recall global sobre todo o corpus.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _load_queries(path: Path, document_ids: set[str]) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with Path(path).open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                query = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON inválido na linha {line_number} das perguntas.") from exc
            if not isinstance(query, dict):
                raise ValueError(f"Pergunta na linha {line_number} deve ser um objeto JSON.")
            query_id = query.get("query_id")
            if not isinstance(query_id, str) or not query_id.strip():
                raise ValueError(f"query_id inválido na linha {line_number}.")
            if query_id in seen_ids:
                raise ValueError(f"query_id duplicado: {query_id}.")
            seen_ids.add(query_id)
            question = query.get("question")
            if not isinstance(question, str) or not question.strip():
                raise ValueError(f"Pergunta vazia ou inválida para {query_id}.")
            relevant_ids = query.get("relevant_ids", [])
            if not isinstance(relevant_ids, list) or any(
                not isinstance(value, str) or not value.strip() for value in relevant_ids
            ):
                raise ValueError(f"relevant_ids deve ser uma lista de IDs textuais para {query_id}.")
            # Repetir um rótulo não aumenta o denominador de documentos relevantes.
            relevant_ids = list(dict.fromkeys(relevant_ids))
            unknown = set(relevant_ids) - document_ids
            if unknown:
                raise ValueError(
                    f"IDs relevantes desconhecidos para {query_id}: " + ", ".join(sorted(unknown))
                )
            if "expect_abstain" in query and type(query["expect_abstain"]) is not bool:
                raise ValueError(f"expect_abstain deve ser booleano para {query_id}.")
            filters = query.get("filters", {})
            if not isinstance(filters, dict):
                raise ValueError(f"filters deve ser um objeto JSON para {query_id}.")
            queries.append({
                "query_id": query_id,
                "question": question.strip(),
                "relevant_ids": relevant_ids,
                "expect_abstain": query.get("expect_abstain"),
                "filters": filters,
            })
    if not queries:
        raise ValueError("O arquivo de perguntas está vazio.")
    return queries


def evaluate_retrieval(
    index,
    embedder,
    queries_path: Path,
    top_k: int = 8,
    min_similarity: float = 0.75,
) -> dict[str, Any]:
    """Mede Recall@k, MRR@k e o gate de no mínimo duas evidências.

    Cada linha JSONL contém query_id, question e, se disponíveis,
    relevant_ids, expect_abstain e filters. Sem relevant_ids não há métrica
    de relevância; sem expect_abstain não há julgamento de abstenção.
    Todas as perguntas são validadas antes da primeira busca.
    """
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k deve ser um inteiro positivo.")
    if (
        type(min_similarity) not in (int, float)
        or not math.isfinite(min_similarity)
        or not -1 <= min_similarity <= 1
    ):
        raise ValueError("O limiar de similaridade deve estar entre -1 e 1.")
    document_ids: set[str] = set()
    for document in index.documents:
        document_id = document.get("doc_id")
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("O corpus contém documento sem ID textual válido.")
        if document_id in document_ids:
            raise ValueError(f"O corpus contém ID de documento duplicado: {document_id}.")
        document_ids.add(document_id)
    if not document_ids:
        raise ValueError("O corpus de avaliação está vazio.")
    queries = _load_queries(Path(queries_path), document_ids)

    results = []
    recall_values: list[float] = []
    reciprocal_ranks: list[float] = []
    n_abstention_queries = 0
    n_abstention_correct = 0
    for query in queries:
        raw_hits = index.search(
            query["question"],
            embedder,
            top_k=top_k,
            filters=query["filters"],
            min_similarity=min_similarity,
        )
        hits = [
            {"id": hit["document"]["doc_id"], "similarity": float(hit["similarity"])}
            for hit in raw_hits
        ]
        hit_ids = [hit["id"] for hit in hits]
        relevant = set(query["relevant_ids"])
        matched = relevant.intersection(hit_ids)
        recall = len(matched) / len(relevant) if relevant else None
        reciprocal_rank = None
        if relevant:
            reciprocal_rank = next(
                (1.0 / rank for rank, document_id in enumerate(hit_ids, 1) if document_id in relevant),
                0.0,
            )
            recall_values.append(recall)
            reciprocal_ranks.append(reciprocal_rank)
        gate_abstained = len(hits) < 2
        abstention_correct = None
        if query["expect_abstain"] is not None:
            n_abstention_queries += 1
            abstention_correct = gate_abstained == query["expect_abstain"]
            n_abstention_correct += int(abstention_correct)
        results.append({
            **query,
            "hits": hits,
            "n_relevant": len(relevant),
            "n_retrieved_relevant": len(matched),
            "recall_at_k": recall,
            "reciprocal_rank_at_k": reciprocal_rank,
            "retrieval_gate_abstained": gate_abstained,
            "retrieval_gate_abstention_correct": abstention_correct,
        })

    return {
        "n_queries": len(queries),
        "n_relevance_queries": len(recall_values),
        "recall_at_k": sum(recall_values) / len(recall_values) if recall_values else None,
        "mrr_at_k": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else None,
        "n_abstention_queries": n_abstention_queries,
        "n_abstention_correct": n_abstention_correct,
        "retrieval_gate_abstention_accuracy": (
            n_abstention_correct / n_abstention_queries if n_abstention_queries else None
        ),
        "results": results,
        "top_k": top_k,
        "min_similarity": min_similarity,
        "limitations": [
            "Recall@k e MRR@k usam somente perguntas com relevant_ids não vazios; "
            "IDs relevantes omitidos não são inferidos automaticamente.",
            "Os rótulos podem cobrir apenas um pool de documentos: as métricas não "
            "comprovam recall global do corpus nem prevalência de temas.",
            "A acurácia de abstenção mede somente o gate de recuperação com menos "
            "de duas evidências; não executa nem avalia o LLM ou as regras de escopo.",
            "Esta avaliação não mede sustentação semântica das afirmações, que "
            "exige revisão das respostas e de suas fontes.",
        ],
    }
