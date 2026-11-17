import json
from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

from voc_olist.retrieval import VectorIndex


class Embedder:
    model_name = "fixture-model"
    revision = None
    def encode_documents(self, texts):
        return np.ones((len(texts), 2), dtype=np.float32)


def test_empty_install_displays_preparation_instructions(tmp_path, monkeypatch):
    monkeypatch.setenv("VOC_PROJECT_ROOT", str(tmp_path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert not app.exception
    assert "Prepare a base" in app.info[0].value


def test_optional_orders_missing_disables_date_filter(tmp_path, monkeypatch):
    monkeypatch.setenv("VOC_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("LLM_PROVIDER", "evidence")
    path = tmp_path / "docs.jsonl"
    path.write_text(json.dumps({"doc_id": "fixture", "text": "Chegou bem.", "score": 5,
                                "purchase_date": None, "categories": []}) + "\n", encoding="utf-8")
    VectorIndex.build(path, tmp_path / "artifacts" / "index", Embedder())
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert not app.exception
    assert app.checkbox[0].disabled
    assert app.metric[0].value == "1"


def test_fresh_default_selects_managed_local_model_instead_of_external_server(tmp_path, monkeypatch):
    monkeypatch.setenv("VOC_PROJECT_ROOT", str(tmp_path))
    for key in ("LLM_PROVIDER", "LLM_MODEL", "LLM_REVISION"):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "docs.jsonl"
    path.write_text(json.dumps({"doc_id": "fixture", "text": "Chegou bem.", "score": 5,
                                "purchase_date": "2018-01-01", "categories": []}) + "\n", encoding="utf-8")
    VectorIndex.build(path, tmp_path / "artifacts" / "index", Embedder())
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert not app.exception
    assert app.selectbox[0].value == "RAG local · Qwen 7B"
    assert any("inicia automaticamente" in caption.value for caption in app.caption)
