"""Métricas com rótulos controlados; nenhum modelo ou serviço externo."""
import json

import pytest

from voc_olist.evaluation import evaluate_retrieval


class FakeEmbedder:
    pass


class FakeIndex:
    def __init__(self, rankings=None):
        self.documents = [{"doc_id": key} for key in ["a", "b", "c", "d"]]
        self.rankings = rankings or {}
        self.calls = []

    def search(self, question, embedder, top_k=8, filters=None, min_similarity=0.75):
        self.calls.append((question, embedder, top_k, filters, min_similarity))
        return [
            {"document": {"doc_id": key}, "similarity": score}
            for key, score in self.rankings.get(question, [])
            if score >= min_similarity
        ][:top_k]


def write_queries(tmp_path, queries):
    path = tmp_path / "queries.jsonl"
    path.write_text("\n".join(json.dumps(query, ensure_ascii=False) for query in queries), encoding="utf-8")
    return path


def test_averages_only_judged_queries_and_preserves_ranks(tmp_path):
    index = FakeIndex({
        "atraso": [("c", 0.99), ("b", 0.95)],
        "defeito": [("a", 0.98), ("d", 0.94)],
        "sem rótulo": [("a", 0.97)],
    })
    path = write_queries(tmp_path, [
        {"query_id": "q1", "question": "atraso", "relevant_ids": ["a", "b"]},
        {"query_id": "q2", "question": "defeito", "relevant_ids": ["c"]},
        {"query_id": "q3", "question": "sem rótulo", "relevant_ids": []},
    ])
    report = evaluate_retrieval(index, FakeEmbedder(), path, top_k=2)
    assert report["n_queries"] == 3
    assert report["n_relevance_queries"] == 2
    assert report["recall_at_k"] == pytest.approx(0.25)
    assert report["mrr_at_k"] == pytest.approx(0.25)
    assert report["results"][0]["hits"] == [
        {"id": "c", "similarity": 0.99}, {"id": "b", "similarity": 0.95},
    ]
    assert report["results"][0]["n_retrieved_relevant"] == 1
    assert report["results"][0]["n_relevant"] == 2
    assert report["results"][2]["recall_at_k"] is None
    assert report["results"][2]["reciprocal_rank_at_k"] is None
    assert report["retrieval_gate_abstention_accuracy"] is None
    # The report is an ordinary strict JSON artifact, including empty metrics.
    json.dumps(report, allow_nan=False)


def test_only_retrieval_gate_is_scored_with_explicit_denominator(tmp_path):
    index = FakeIndex({
        "vazio": [],
        "um": [("a", 0.9)],
        "dois": [("b", 0.9), ("c", 0.8)],
        "não julgado": [],
    })
    path = write_queries(tmp_path, [
        {"query_id": "q1", "question": "vazio", "expect_abstain": True},
        {"query_id": "q2", "question": "um", "expect_abstain": False},
        {"query_id": "q3", "question": "dois", "expect_abstain": False},
        {"query_id": "q4", "question": "não julgado"},
    ])
    report = evaluate_retrieval(index, FakeEmbedder(), path)
    assert report["n_abstention_queries"] == 3
    assert report["n_abstention_correct"] == 2
    assert report["retrieval_gate_abstention_accuracy"] == pytest.approx(2 / 3)
    assert [row["retrieval_gate_abstained"] for row in report["results"]] == [True, True, False, True]
    assert report["results"][3]["retrieval_gate_abstention_correct"] is None
    assert report["n_relevance_queries"] == 0
    assert report["recall_at_k"] is None
    assert report["mrr_at_k"] is None
    assert any("não executa" in limitation and "LLM" in limitation for limitation in report["limitations"])


def test_top_k_threshold_and_filters_are_forwarded(tmp_path):
    index = FakeIndex({"entrega": [("a", 0.99), ("b", 0.88), ("c", 0.77)]})
    embedder = FakeEmbedder()
    filters = {"score_max": 2, "category": "livros"}
    path = write_queries(tmp_path, [{
        "query_id": "q1", "question": " entrega ", "relevant_ids": ["b", "c"], "filters": filters,
    }])
    report = evaluate_retrieval(index, embedder, path, top_k=1, min_similarity=0.9)
    assert index.calls == [("entrega", embedder, 1, filters, 0.9)]
    assert report["top_k"] == 1
    assert report["min_similarity"] == 0.9
    assert report["results"][0]["hits"] == [{"id": "a", "similarity": 0.99}]
    assert report["recall_at_k"] == 0
    assert report["mrr_at_k"] == 0


def test_duplicate_relevance_labels_do_not_inflate_denominator(tmp_path):
    index = FakeIndex({"atraso": [("a", 0.99)]})
    path = write_queries(tmp_path, [{
        "query_id": "q1", "question": "atraso", "relevant_ids": ["a", "a"],
    }])
    report = evaluate_retrieval(index, FakeEmbedder(), path)
    assert report["results"][0]["relevant_ids"] == ["a"]
    assert report["recall_at_k"] == 1
    assert report["mrr_at_k"] == 1


def test_unknown_relevant_id_fails_before_any_search(tmp_path):
    index = FakeIndex()
    path = write_queries(tmp_path, [
        {"query_id": "good", "question": "válida", "relevant_ids": ["a"]},
        {"query_id": "bad", "question": "inválida", "relevant_ids": ["ausente"]},
    ])
    with pytest.raises(ValueError, match="IDs relevantes desconhecidos.*ausente"):
        evaluate_retrieval(index, FakeEmbedder(), path)
    assert index.calls == []


def test_duplicate_query_id_is_rejected_before_search(tmp_path):
    index = FakeIndex()
    path = write_queries(tmp_path, [
        {"query_id": "q1", "question": "primeira"},
        {"query_id": "q1", "question": "segunda"},
    ])
    with pytest.raises(ValueError, match="query_id duplicado"):
        evaluate_retrieval(index, FakeEmbedder(), path)
    assert index.calls == []


def test_blank_lines_and_bom_are_accepted(tmp_path):
    index = FakeIndex()
    path = tmp_path / "queries.jsonl"
    path.write_text('\ufeff\n  \n{"query_id":"q1","question":"elogios"}\n\n', encoding="utf-8")
    report = evaluate_retrieval(index, FakeEmbedder(), path)
    assert report["n_queries"] == 1


@pytest.mark.parametrize("text", ["", "\n  \n"])
def test_empty_query_file_is_rejected(tmp_path, text):
    path = tmp_path / "queries.jsonl"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="arquivo de perguntas está vazio"):
        evaluate_retrieval(FakeIndex(), FakeEmbedder(), path)


@pytest.mark.parametrize("query,match", [
    ([], "objeto JSON"),
    ({"query_id": "", "question": "x"}, "query_id inválido"),
    ({"query_id": "q", "question": " "}, "Pergunta vazia"),
    ({"query_id": "q", "question": "x", "relevant_ids": "a"}, "relevant_ids"),
    ({"query_id": "q", "question": "x", "relevant_ids": [1]}, "relevant_ids"),
    ({"query_id": "q", "question": "x", "expect_abstain": "false"}, "expect_abstain"),
    ({"query_id": "q", "question": "x", "expect_abstain": None}, "expect_abstain"),
    ({"query_id": "q", "question": "x", "filters": []}, "filters"),
])
def test_invalid_query_records_fail_explicitly(tmp_path, query, match):
    path = write_queries(tmp_path, [query])
    with pytest.raises(ValueError, match=match):
        evaluate_retrieval(FakeIndex(), FakeEmbedder(), path)


def test_malformed_json_reports_line_number(tmp_path):
    path = tmp_path / "queries.jsonl"
    path.write_text("\n{broken}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="linha 2"):
        evaluate_retrieval(FakeIndex(), FakeEmbedder(), path)


@pytest.mark.parametrize("kwargs", [
    {"top_k": 0}, {"top_k": True}, {"top_k": 1.5},
    {"min_similarity": float("nan")}, {"min_similarity": float("inf")},
    {"min_similarity": 1.1}, {"min_similarity": True},
])
def test_invalid_parameters_are_rejected(tmp_path, kwargs):
    path = write_queries(tmp_path, [{"query_id": "q", "question": "x"}])
    with pytest.raises(ValueError):
        evaluate_retrieval(FakeIndex(), FakeEmbedder(), path, **kwargs)


@pytest.mark.parametrize("documents", [
    [], [{"doc_id": "a"}, {"doc_id": "a"}], [{"doc_id": None}], [{"id": "legacy"}],
])
def test_invalid_corpus_identity_is_rejected(tmp_path, documents):
    path = write_queries(tmp_path, [{"query_id": "q", "question": "x"}])
    index = FakeIndex()
    index.documents = documents
    with pytest.raises(ValueError, match="corpus"):
        evaluate_retrieval(index, FakeEmbedder(), path)


def test_persisted_vector_index_integrates_with_doc_id_labels(tmp_path):
    """Cobre o contrato real de preparação/índice, diferente do fake de métricas."""
    import hashlib

    import numpy as np

    from voc_olist.retrieval import VectorIndex

    ids = [hashlib.sha256(value.encode("ascii")).hexdigest() for value in ["review1:order1", "review2:order2"]]
    documents = [
        {"doc_id": ids[0], "text": "Relato de entrega atrasada", "score": 1},
        {"doc_id": ids[1], "text": "Outro relato de prazo não cumprido", "score": 2},
    ]
    documents_path = tmp_path / "documents.jsonl"
    documents_path.write_text("\n".join(json.dumps(document) for document in documents), encoding="utf-8")

    class IntegrationEmbedder:
        model_name = "integration-no-download"
        revision = "fixed-test-revision"

        def encode_documents(self, texts):
            assert texts == [document["text"] for document in documents]
            return np.asarray([[1.0, 0.0], [0.8, 0.6]], dtype=np.float32)

        def encode_query(self, question):
            return np.asarray([1.0, 0.0], dtype=np.float32)

    embedder = IntegrationEmbedder()
    index_dir = tmp_path / "index"
    VectorIndex.build(documents_path, index_dir, embedder)
    index = VectorIndex.load(index_dir)
    queries_path = write_queries(tmp_path, [{
        "query_id": "integration-query",
        "question": "Relatos de entrega",
        "relevant_ids": [ids[1]],
        "filters": {"score_max": 2},
        "expect_abstain": False,
    }])
    report = evaluate_retrieval(index, embedder, queries_path, top_k=2)
    assert [hit["id"] for hit in report["results"][0]["hits"]] == ids
    assert [hit["similarity"] for hit in report["results"][0]["hits"]] == pytest.approx([1.0, 0.8])
    assert report["recall_at_k"] == 1.0
    assert report["mrr_at_k"] == 0.5
    assert report["retrieval_gate_abstention_accuracy"] == 1.0
