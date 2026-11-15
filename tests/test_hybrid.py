"""Behavioral checks for lexical reranking of an eligible dense pool."""
import copy

import numpy as np
import pytest

from voc_olist.hybrid import HybridIndex
from voc_olist.retrieval import VectorIndex


class Embedder:
    model_name = "fixture"
    revision = "fixed"

    def __init__(self):
        self.calls = 0

    def encode_query(self, question):
        self.calls += 1
        return np.asarray([1.0, 0.0], dtype=np.float32)


def index_with(texts, scores=None, vectors=None):
    scores = scores or [5] * len(texts)
    docs = [
        {"doc_id": f"doc{i}", "text": text, "score": scores[i],
         "purchase_date": "2018-01-01", "categories": ["livros"], "delivered_late": i == 1}
        for i, text in enumerate(texts)
    ]
    if vectors is None:
        vectors = [[1.0, 0.0], [.8, .6]][:len(texts)]
    vectors = np.asarray(vectors, dtype=np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return VectorIndex(docs, vectors, {"model_name": "fixture", "revision": "fixed"})


def test_lexical_match_can_outrank_semantically_similar_wrong_theme():
    base = index_with(["O pedido chegou antes do prazo.", "Atraso de uma semana na entrega."])
    embedder = Embedder()
    assert base.search("atrasos", embedder, top_k=2)[0]["document"]["doc_id"] == "doc0"
    embedder.calls = 0
    results = HybridIndex(base).search("atrasos", embedder, top_k=2)
    assert [hit["document"]["doc_id"] for hit in results] == ["doc1", "doc0"]
    assert results[0]["similarity"] == pytest.approx(.8)
    assert results[0]["retrieval_score"] > results[1]["retrieval_score"]
    assert embedder.calls == 1


def test_accent_case_and_negation_are_retained_for_matching():
    base = index_with(["O produto chegou.", "NÃO chegou."])
    results = HybridIndex(base).search("não chegou", Embedder(), top_k=2)
    assert results[0]["document"]["doc_id"] == "doc1"
    base = index_with(["Reclamei do atraso.", "Compra sem atraso."])
    assert HybridIndex(base).search("SEM ATRASO", Embedder())[0]["document"]["doc_id"] == "doc1"


@pytest.mark.parametrize("question", ["o e a de para", "hiperespacial inexistente"])
def test_no_lexical_terms_or_matches_preserves_pure_cosine_order(question):
    base = index_with(["Entrega antecipada.", "Atraso na entrega."])
    results = HybridIndex(base).search(question, Embedder(), top_k=2)
    assert [hit["document"]["doc_id"] for hit in results] == ["doc0", "doc1"]
    assert [hit["similarity"] for hit in results] == pytest.approx([1.0, .8])


def test_metadata_filters_are_applied_before_fusion():
    base = index_with(["Entrega antes do prazo.", "Atraso de uma semana."], scores=[5, 1])
    results = HybridIndex(base).search(
        "atraso", Embedder(), filters={"score_max": 2, "category": "livros", "delivered_late": True},
    )
    assert len(results) == 1 and results[0]["document"]["doc_id"] == "doc1"
    assert HybridIndex(base).search("atraso", Embedder(), filters={"category": "inexistente"}) == []


def test_lexical_match_cannot_bypass_cosine_threshold():
    base = index_with(["Entrega antes do prazo.", "Atraso de uma semana."])
    results = HybridIndex(base).search("atraso", Embedder(), min_similarity=.9)
    assert [hit["document"]["doc_id"] for hit in results] == ["doc0"]
    with pytest.raises(ValueError, match="limiar"):
        HybridIndex(base).search("atraso", Embedder(), min_similarity=1.01)


@pytest.mark.parametrize("attribute", ["model_name", "revision"])
def test_delegate_rejects_incompatible_model_before_encoding_question(attribute):
    base = index_with(["Entrega antes do prazo.", "Atraso de uma semana."])
    embedder = Embedder()
    setattr(embedder, attribute, "another-model-or-revision")
    with pytest.raises(ValueError, match="Modelo ou revisão"):
        HybridIndex(base).search("atraso", embedder)
    assert embedder.calls == 0


def test_repeated_text_is_deduplicated_and_base_objects_are_not_mutated():
    base = index_with(
        ["Atraso na entrega.", "Atraso na entrega.", "Entrega antecipada."],
        vectors=[[1, 0], [.8, .6], [.6, .8]],
    )
    docs, manifest, vectors = copy.deepcopy(base.documents), copy.deepcopy(base.manifest), base.vectors.copy()
    hybrid = HybridIndex(base)
    results = hybrid.search("atraso", Embedder(), top_k=3, min_similarity=.5)
    assert len(results) == 2
    assert len({hit["document"]["text"] for hit in results}) == 2
    assert base.documents == docs and base.manifest == manifest
    np.testing.assert_array_equal(base.vectors, vectors)
    assert hybrid.documents is base.documents
    assert hybrid.manifest is base.manifest
    assert hybrid.vectors is base.vectors
    assert all("retrieval_score" not in document for document in base.documents)


def test_dense_candidate_pool_is_bounded_and_query_is_encoded_once():
    base = index_with(["Entrega antes do prazo.", "Atraso de uma semana."])
    recorded = []
    original = base.search

    def record(*args, **kwargs):
        recorded.append(kwargs)
        return original(*args, **kwargs)

    base.search = record
    embedder = Embedder()
    HybridIndex(base, candidate_k=3).search("atraso", embedder, top_k=2)
    assert recorded[0]["top_k"] == 12
    assert embedder.calls == 1


def test_lexical_match_outside_dense_pool_is_not_recovered():
    base = index_with(
        ["Chegou cedo.", "Veio rápido.", "Ótima compra.", "Produto excelente.", "Atraso enorme no frete."],
        vectors=[[1, 0], [.99, .1], [.97, .2], [.95, .3], [.8, .6]],
    )
    results = HybridIndex(base, candidate_k=1).search("atraso", Embedder(), top_k=1)
    assert results[0]["document"]["doc_id"] == "doc0"
    assert all(hit["document"]["doc_id"] != "doc4" for hit in results)


@pytest.mark.parametrize("candidate_k", [0, -1, True, 1.5])
def test_invalid_pool_size_is_rejected(candidate_k):
    with pytest.raises(ValueError, match="candidate_k"):
        HybridIndex(index_with(["Texto"], vectors=[[1, 0]]), candidate_k)
