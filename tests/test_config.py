from voc_olist.config import Settings, DEFAULT_LLM_MODEL, DEFAULT_LLM_REVISION


def test_fresh_install_has_pinned_local_generator(tmp_path):
    s = Settings.from_env(tmp_path)
    assert s.provider == "native" and s.llm_model == DEFAULT_LLM_MODEL
    assert s.llm_revision == DEFAULT_LLM_REVISION


def test_project_dotenv_does_not_pollute_other_project(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    (a / ".env").write_text("LLM_PROVIDER=ollama\nLLM_MODEL=my-fixture\n", encoding="utf-8")
    assert Settings.from_env(a).llm_model == "my-fixture"
    assert Settings.from_env(b).provider == "native"


def test_environment_overrides_dotenv_without_wrong_revision(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "different-local-model")
    s = Settings.from_env(tmp_path)
    assert s.llm_model == "different-local-model" and s.llm_revision is None
