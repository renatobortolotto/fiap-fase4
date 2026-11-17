import json
from pathlib import Path

import pytest

import voc_olist.model_store as store


def model_files(path, *, e5=False, pooling=True):
    path.mkdir(parents=True, exist_ok=True)
    (path / "config.json").write_text('{"model_type":"bert"}', encoding="utf-8")
    (path / "model.safetensors").write_bytes(b"fixture-weights")
    (path / "tokenizer.json").write_text('{"version":"1.0"}', encoding="utf-8")
    if e5:
        (path / "modules.json").write_text(json.dumps([
            {"path": "", "type": "sentence_transformers.models.Transformer"},
            {"path": "1_Pooling", "type": "sentence_transformers.models.Pooling"},
        ]), encoding="utf-8")
        if pooling:
            (path / "1_Pooling").mkdir()
            (path / "1_Pooling" / "config.json").write_text('{"pooling_mode_mean_tokens":true}', encoding="utf-8")


def no_network(*args, **kwargs):
    raise AssertionError("Este caso deve retornar sem acessar a rede")


def test_explicit_existing_local_directory_is_returned_without_network(tmp_path, monkeypatch):
    local = tmp_path / "my local model"
    local.mkdir()
    monkeypatch.setattr(store, "snapshot_download", no_network)
    assert store.local_model_path(str(local), None, tmp_path / "cache") == local.resolve()


def test_download_uses_normal_local_files_and_ready_marker_then_no_network(tmp_path, monkeypatch):
    calls = []
    def download(**kwargs):
        calls.append(kwargs)
        model_files(Path(kwargs["local_dir"]))
        return kwargs["local_dir"]
    monkeypatch.setattr(store, "snapshot_download", download)
    path = store.local_model_path("org/model", "a" * 40, tmp_path)
    assert path.is_relative_to(tmp_path / "local-models")
    assert calls[0]["local_dir_use_symlinks"] is False
    assert "cache_dir" not in calls[0]
    assert calls[0]["endpoint"] == "https://huggingface.co"
    assert calls[0]["revision"] == "a" * 40
    assert "*.safetensors" in calls[0]["allow_patterns"]
    assert "*.bin" not in calls[0]["allow_patterns"] and "*.py" not in calls[0]["allow_patterns"]
    assert "*.bin" in calls[0]["ignore_patterns"] and "*.py" in calls[0]["ignore_patterns"]
    assert json.loads((path / ".voc-model-ready.json").read_text()) == {
        "schema_version": 1, "model_name": "org/model", "revision": "a" * 40}
    monkeypatch.setattr(store, "snapshot_download", no_network)
    assert store.local_model_path("org/model", "a" * 40, tmp_path) == path


def test_complete_legacy_snapshot_is_reused_without_network(tmp_path, monkeypatch):
    expected = tmp_path / "models--org--model" / "snapshots" / ("b" * 40)
    model_files(expected)
    monkeypatch.setattr(store, "snapshot_download", no_network)
    assert store.local_model_path("org/model", "b" * 40, tmp_path) == expected.resolve()


def test_legacy_main_ref_resolves_only_a_valid_commit_hash(tmp_path, monkeypatch):
    repo = tmp_path / "models--org--model"
    expected = repo / "snapshots" / ("c" * 40)
    model_files(expected)
    (repo / "refs").mkdir()
    (repo / "refs" / "main").write_text("c" * 40, encoding="utf-8")
    monkeypatch.setattr(store, "snapshot_download", no_network)
    assert store.local_model_path("org/model", None, tmp_path) == expected.resolve()


def test_e5_legacy_snapshot_requires_pooling_configuration(tmp_path, monkeypatch):
    old = tmp_path / "models--intfloat--multilingual-e5-small" / "snapshots" / ("d" * 40)
    model_files(old, e5=True, pooling=False)
    calls = []
    def download(**kwargs):
        calls.append(kwargs)
        model_files(Path(kwargs["local_dir"]), e5=True)
    monkeypatch.setattr(store, "snapshot_download", download)
    result = store.local_model_path("intfloat/multilingual-e5-small", "d" * 40, tmp_path)
    assert result != old and len(calls) == 1
    assert (result / "1_Pooling" / "config.json").is_file()


def test_complete_e5_legacy_snapshot_is_reused(tmp_path, monkeypatch):
    old = tmp_path / "models--intfloat--multilingual-e5-small" / "snapshots" / ("d" * 40)
    model_files(old, e5=True)
    monkeypatch.setattr(store, "snapshot_download", no_network)
    assert store.local_model_path("intfloat/multilingual-e5-small", "d" * 40, tmp_path) == old.resolve()


@pytest.mark.parametrize("name", ["../escape", "org/../../escape", "https://example.com/model", "org\\model", "", None])
def test_invalid_model_identifiers_cannot_escape_cache(tmp_path, monkeypatch, name):
    monkeypatch.setattr(store, "snapshot_download", no_network)
    with pytest.raises(ValueError):
        store.local_model_path(name, "main", tmp_path)


@pytest.mark.parametrize("revision", ["../escape", "refs/../../escape", "/absolute", "C:\\model", "refs\\pr\\1", "", " main"])
def test_invalid_revisions_cannot_escape_cache(tmp_path, monkeypatch, revision):
    monkeypatch.setattr(store, "snapshot_download", no_network)
    with pytest.raises(ValueError):
        store.local_model_path("org/model", revision, tmp_path)


def test_pull_request_ref_uses_safe_flat_directory_and_preserves_hub_revision(tmp_path, monkeypatch):
    calls = []
    def download(**kwargs):
        calls.append(kwargs)
        model_files(Path(kwargs["local_dir"]))
    monkeypatch.setattr(store, "snapshot_download", download)
    result = store.local_model_path("org/model", "refs/pr/1", tmp_path)
    assert result.is_relative_to(tmp_path / "local-models" / "org--model")
    assert result.parent == tmp_path / "local-models" / "org--model"
    assert calls[0]["revision"] == "refs/pr/1"


def test_network_failure_has_actionable_message_and_no_ready_marker(tmp_path, monkeypatch):
    def offline(**kwargs):
        raise OSError("offline fixture")
    monkeypatch.setattr(store, "snapshot_download", offline)
    with pytest.raises(RuntimeError, match="HF_HUB_OFFLINE=0"):
        store.local_model_path("org/model", "main", tmp_path)
    assert not list(tmp_path.rglob(".voc-model-ready.json"))


def test_incomplete_download_is_not_marked_ready(tmp_path, monkeypatch):
    def incomplete(**kwargs):
        path = Path(kwargs["local_dir"])
        (path / "config.json").write_text('{}', encoding="utf-8")
        (path / "model.safetensors").write_bytes(b"fixture-weights")
    monkeypatch.setattr(store, "snapshot_download", incomplete)
    with pytest.raises(RuntimeError):
        store.local_model_path("org/model", "main", tmp_path)
    assert not list(tmp_path.rglob(".voc-model-ready.json"))


def test_deleted_asset_invalidates_ready_marker_and_triggers_repair(tmp_path, monkeypatch):
    calls = []
    def download(**kwargs):
        calls.append(kwargs)
        model_files(Path(kwargs["local_dir"]))
    monkeypatch.setattr(store, "snapshot_download", download)
    path = store.local_model_path("org/model", None, tmp_path)
    (path / "tokenizer.json").unlink()
    assert store.local_model_path("org/model", None, tmp_path) == path
    assert len(calls) == 2


def test_sharded_snapshot_needs_every_referenced_weight_file(tmp_path, monkeypatch):
    def partial(**kwargs):
        path = Path(kwargs["local_dir"])
        model_files(path)
        (path / "model.safetensors.index.json").write_text(json.dumps({"weight_map": {
            "one": "model.safetensors", "two": "missing-shard.safetensors"}}), encoding="utf-8")
    monkeypatch.setattr(store, "snapshot_download", partial)
    with pytest.raises(RuntimeError):
        store.local_model_path("org/model", "main", tmp_path)
    assert not list(tmp_path.rglob(".voc-model-ready.json"))


def test_sentencepiece_tokenizer_without_tokenizer_json_is_supported(tmp_path, monkeypatch):
    old = tmp_path / "models--org--model" / "snapshots" / ("e" * 40)
    model_files(old)
    (old / "tokenizer.json").unlink()
    (old / "sentencepiece.bpe.model").write_bytes(b"fixture-tokenizer")
    monkeypatch.setattr(store, "snapshot_download", no_network)
    assert store.local_model_path("org/model", "e" * 40, tmp_path) == old.resolve()


def test_e5_metadata_without_any_pooling_module_is_not_ready(tmp_path, monkeypatch):
    def incomplete(**kwargs):
        path = Path(kwargs["local_dir"])
        model_files(path)
        (path / "modules.json").write_text(json.dumps([
            {"path": "", "type": "sentence_transformers.models.Transformer"}]), encoding="utf-8")
    monkeypatch.setattr(store, "snapshot_download", incomplete)
    with pytest.raises(RuntimeError):
        store.local_model_path("intfloat/multilingual-e5-small", "main", tmp_path)
    assert not list(tmp_path.rglob(".voc-model-ready.json"))
