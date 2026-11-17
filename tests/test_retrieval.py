"""Contratos de persistência e recuperação, sem baixar modelos ou usar API."""
import hashlib
import json

import numpy as np
import pytest

from voc_olist.retrieval import SentenceEmbedder, VectorIndex


class FakeEmbedder:
    model_name = "teste-sem-download"
    revision = "revision-1"

    def __init__(self):
        self.query_calls = 0

    def encode_documents(self, texts):
        mapping = {
            "Entrega atrasada": [1.0, 0.0, 0.0],
            "entrega  atrasada": [1.0, 0.0, 0.0],
            "Produto com defeito": [0.8, 0.6, 0.0],
            "Entrega rápida": [0.6, 0.0, 0.8],
            "Atendimento cordial": [0.0, 0.0, 1.0],
        }
        return np.asarray([mapping[text] for text in texts], dtype=np.float32)

    def encode_query(self, question):
        self.query_calls += 1
        return np.asarray([1.0, 0.0, 0.0], dtype=np.float32)


@pytest.fixture
def documents():
    return [
        {"id": "r1", "text": "Entrega atrasada", "score": 1, "purchase_date": "2018-01-10", "categories": ["livros"], "delivered_late": True},
        {"id": "r2", "text": "entrega  atrasada", "score": 2, "purchase_date": "2018-01-12", "categories": ["livros"], "delivered_late": True},
        {"id": "r3", "text": "Produto com defeito", "score": 1, "purchase_date": "2018-02-10", "categories": ["informatica", "eletronicos"], "delivered_late": False},
        {"id": "r4", "text": "Entrega rápida", "score": 5, "purchase_date": "2018-03-01", "categories": ["livros"], "delivered_late": False},
        {"id": "r5", "text": "Atendimento cordial", "score": 4, "purchase_date": None, "categories": [], "delivered_late": None},
    ]


@pytest.fixture
def built(tmp_path, documents):
    source = tmp_path / "source.jsonl"
    source.write_text("\n".join(json.dumps(doc, ensure_ascii=False) for doc in documents), encoding="utf-8")
    embedder = FakeEmbedder()
    index_dir = tmp_path / "index"
    manifest = VectorIndex.build(source, index_dir, embedder, batch_size=2)
    return source, index_dir, embedder, manifest


def test_roundtrip_ranking_threshold_and_deduplication(built, documents):
    source, index_dir, embedder, manifest = built
    index = VectorIndex.load(index_dir)
    assert index.documents == documents
    assert manifest["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert index.vectors.dtype == np.float32
    assert manifest["shape"] == [5, 3]
    results = index.search("Problemas de entrega", embedder, top_k=3, min_similarity=0.5)
    assert [hit["document"]["id"] for hit in results] == ["r1", "r3", "r4"]
    assert [hit["similarity"] for hit in results] == pytest.approx([1.0, 0.8, 0.6])
    assert len(index.search("Problemas", embedder, min_similarity=0.9)) == 1


def test_filters_apply_before_ranking_and_exclude_unknown_metadata(built):
    _, index_dir, embedder, _ = built
    index = VectorIndex.load(index_dir)
    assert index.search("Problemas", embedder, top_k=1, filters={"score_min": 5}, min_similarity=0)[0]["document"]["id"] == "r4"
    filters = {"score_min": 1, "score_max": 2, "date_from": "2018-02-01", "date_to": "2018-02-28", "category": "ELETRONICOS", "delivered_late": False}
    assert index.search("Problemas", embedder, filters=filters, min_similarity=0)[0]["document"]["id"] == "r3"
    dated = index.search("Problemas", embedder, filters={"date_from": "2016-01-01"}, min_similarity=-1)
    assert "r5" not in [hit["document"]["id"] for hit in dated]
    on_time = index.search("Problemas", embedder, filters={"delivered_late": False}, min_similarity=-1)
    assert {hit["document"]["id"] for hit in on_time} == {"r3", "r4"}


def test_empty_filter_results_do_not_call_encoder(built):
    _, index_dir, embedder, _ = built
    index = VectorIndex.load(index_dir)
    assert index.search("Problemas", embedder, filters={"category": "categoria-ausente"}) == []
    assert embedder.query_calls == 0


@pytest.mark.parametrize("attribute,value", [("model_name", "outro-modelo"), ("revision", "outra-revisao")])
def test_model_or_revision_mismatch_is_rejected(built, attribute, value):
    _, index_dir, embedder, _ = built
    setattr(embedder, attribute, value)
    with pytest.raises(ValueError, match="Modelo ou revisão"):
        VectorIndex.load(index_dir).search("Problemas", embedder)


@pytest.mark.parametrize("filename", ["docs.jsonl", "vectors.npy"])
def test_tampered_index_files_are_rejected(built, filename):
    _, index_dir, _, _ = built
    with (index_dir / filename).open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError, match="Integridade"):
        VectorIndex.load(index_dir)


def _replace_vectors_and_hash(index_dir, vectors):
    path = index_dir / "vectors.npy"
    np.save(path, vectors)
    manifest_path = index_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["vectors_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_corrupt_dimensions_are_rejected_even_with_updated_hash(built):
    _, index_dir, _, _ = built
    _replace_vectors_and_hash(index_dir, np.ones((5, 2), dtype=np.float32))
    with pytest.raises(ValueError, match="Dimensões"):
        VectorIndex.load(index_dir)


@pytest.mark.parametrize("bad_value", [0.0, np.nan, np.inf, 2.0])
def test_non_normalized_or_non_finite_vectors_are_rejected(built, bad_value):
    _, index_dir, _, _ = built
    vectors = np.load(index_dir / "vectors.npy")
    vectors[0] = [bad_value, 0.0, 0.0]
    _replace_vectors_and_hash(index_dir, vectors)
    with pytest.raises(ValueError, match="não finitos ou não normalizados"):
        VectorIndex.load(index_dir)


def test_wrong_query_dimension_is_rejected(built):
    _, index_dir, embedder, _ = built
    embedder.encode_query = lambda _: np.ones(2, dtype=np.float32)
    with pytest.raises(ValueError, match="Dimensão do embedding"):
        VectorIndex.load(index_dir).search("Problemas", embedder)


@pytest.mark.parametrize("filters", [{"score_min": 6}, {"score_min": 4, "score_max": 1}, {"date_from": "data inválida"}, {"date_from": "2019-01-01", "date_to": "2018-01-01"}, {"delivered_late": "false"}, {"category": ""}, {"inexistente": True}])
def test_invalid_filters_fail_explicitly(built, filters):
    _, index_dir, embedder, _ = built
    with pytest.raises(ValueError):
        VectorIndex.load(index_dir).search("Problemas", embedder, filters=filters)


def test_e5_prefixes_and_lazy_loading_without_model_download():
    embedder = SentenceEmbedder()
    assert embedder._model is None
    received = []

    class FakeModel:
        def encode(self, texts, **kwargs):
            received.append((texts, kwargs))
            return np.asarray([[3.0, 4.0] for _ in texts], dtype=np.float64)

    embedder._model = FakeModel()
    vectors = embedder.encode_documents(["  entrega atrasada  "])
    query = embedder.encode_query("atraso")
    assert received[0][0] == ["passage: entrega atrasada"]
    assert received[1][0] == ["query: atraso"]
    assert received[0][1]["normalize_embeddings"] is True
    assert vectors.dtype == np.float32
    assert query.shape == (2,)
    assert np.linalg.norm(query) == pytest.approx(1.0)


class RecordingEmbedder:
    model_name = "deterministic-batching-fixture"
    revision = "fixture-revision"

    def __init__(self, mapping):
        self.mapping = mapping
        self.batches = []

    def encode_documents(self, texts):
        self.batches.append(list(texts))
        return np.asarray([self.mapping[text] for text in texts], dtype=np.float64)


def test_unique_length_sorted_batches_restore_every_original_document_row(tmp_path):
    documents = [
        {"doc_id": "review-long-first", "text": "texto maior", "score": 1},
        {"doc_id": "review-z", "text": "z", "score": 5},
        {"doc_id": "review-long-again", "text": "texto maior", "score": 2},
        {"doc_id": "review-a", "text": "a", "score": 4},
        {"doc_id": "review-medium", "text": "médio", "score": 3},
    ]
    source = tmp_path / "source.jsonl"
    source.write_text("\n".join(json.dumps(doc, ensure_ascii=False) for doc in documents), encoding="utf-8")
    original_bytes = source.read_bytes()
    embedder = RecordingEmbedder({"texto maior": [1, 1], "z": [1, 0], "a": [3, 4], "médio": [0, 2]})
    index_dir = tmp_path / "index"
    manifest = VectorIndex.build(source, index_dir, embedder, batch_size=2)
    index = VectorIndex.load(index_dir)

    assert embedder.batches == [["a", "z"], ["médio", "texto maior"]]
    assert sum(map(len, embedder.batches)) == 4
    assert manifest["n_unique_texts"] == 4 and manifest["document_count"] == 5
    assert manifest["shape"] == [5, 2]
    assert index.documents == documents
    assert source.read_bytes() == original_bytes
    assert manifest["source_sha256"] == hashlib.sha256(original_bytes).hexdigest()
    expected = np.asarray([[2**-.5, 2**-.5], [1, 0], [2**-.5, 2**-.5], [.6, .8], [0, 1]], dtype=np.float32)
    np.testing.assert_allclose(index.vectors, expected, atol=1e-6)
    np.testing.assert_array_equal(index.vectors[0], index.vectors[2])
    np.testing.assert_allclose(np.linalg.norm(index.vectors, axis=1), 1.0, atol=1e-6)
    assert index.vectors.dtype == np.float32


def test_encoding_deduplication_uses_exact_text_without_merging_reviews(tmp_path):
    documents = [{"doc_id": str(i), "text": text} for i, text in enumerate(["Entrega", "entrega", "Entrega ", "Entrega"])]
    source = tmp_path / "source.jsonl"
    source.write_text("\n".join(json.dumps(doc) for doc in documents), encoding="utf-8")
    embedder = RecordingEmbedder({"Entrega": [1, 0], "entrega": [0, 1], "Entrega ": [1, 1]})
    index_dir = tmp_path / "index"
    manifest = VectorIndex.build(source, index_dir, embedder, batch_size=1)
    index = VectorIndex.load(index_dir)

    assert embedder.batches == [["Entrega"], ["entrega"], ["Entrega "]]
    assert manifest["n_unique_texts"] == 3 and len(index.documents) == 4
    assert index.documents == documents
    np.testing.assert_array_equal(index.vectors[0], index.vectors[3])
    assert not np.array_equal(index.vectors[0], index.vectors[1])


def test_manifest_without_optional_batching_metadata_remains_loadable(built):
    _, index_dir, _, _ = built
    manifest_path = index_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("n_unique_texts")
    manifest.pop("batching_strategy")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    index = VectorIndex.load(index_dir)
    assert index.vectors.shape == (5, 3)
    assert len(index.documents) == 5


def test_unique_batch_row_count_mismatch_is_rejected(tmp_path):
    source = tmp_path / "source.jsonl"
    source.write_text('{"text":"a"}\n{"text":"b"}\n{"text":"a"}\n', encoding="utf-8")

    class MissingRowEmbedder:
        model_name = "invalid-row-count-fixture"
        revision = None
        def encode_documents(self, texts):
            return np.ones((len(texts) - 1, 2), dtype=np.float32)

    with pytest.raises(ValueError, match="Quantidade de embeddings"):
        VectorIndex.build(source, tmp_path / "index", MissingRowEmbedder(), batch_size=2)


def test_unique_batch_dimension_change_is_rejected(tmp_path):
    source = tmp_path / "source.jsonl"
    source.write_text('{"text":"a"}\n{"text":"bb"}\n', encoding="utf-8")

    class ChangedDimensionEmbedder:
        model_name = "invalid-dimension-fixture"
        revision = None
        calls = 0
        def encode_documents(self, texts):
            self.calls += 1
            return np.ones((len(texts), self.calls + 1), dtype=np.float32)

    with pytest.raises(ValueError, match="dimensão dos embeddings mudou"):
        VectorIndex.build(source, tmp_path / "index", ChangedDimensionEmbedder(), batch_size=1)
