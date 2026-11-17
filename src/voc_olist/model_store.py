"""Modelos locais sem exigir symlinks ou privilegios de administrador no Windows.

Usa o modo local_dir documentado pelo Hugging Face Hub, preservando a estrutura
do repositorio com arquivos normais. Downloads aceitam apenas pesos safetensors,
configuracoes e arquivos de tokenizacao; codigo Python e pesos pickle nao entram.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

from huggingface_hub import snapshot_download
from huggingface_hub.utils import validate_repo_id

_MARKER = ".voc-model-ready.json"
_PATTERNS = ["*.json", "*.safetensors", "*.model", "*.txt", "tokenizer*", "vocab*", "merges*"]
_IGNORED = ["*.bin", "*.pt", "*.pth", "*.pkl", "*.pickle", "*.py", "*.pyc"]


def _inside(root: Path, *parts: str) -> Path:
    candidate = root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("O caminho do modelo deve permanecer dentro de seu cache.")
    return candidate


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _complete(path: Path, model_name: str) -> bool:
    try:
        config = _json(path / "config.json")
        if not isinstance(config, dict) or not config:
            return False
        weights = [p for p in path.glob("*.safetensors") if _nonempty(p)]
        if not weights:
            return False
        # A shard index must not make an interrupted snapshot look complete.
        shards_path = path / "model.safetensors.index.json"
        if shards_path.exists():
            shard_map = _json(shards_path)
            names = set(shard_map.get("weight_map", {}).values()) if isinstance(shard_map, dict) else set()
            if not names or any(not isinstance(name, str) or not name.endswith(".safetensors")
                                or not _nonempty(_inside(path, name)) for name in names):
                return False
        tokenizer_names = ("tokenizer.json", "vocab.json", "vocab.txt", "tokenizer.model",
                           "spiece.model", "sentencepiece.bpe.model")
        if not any(_nonempty(path / name) for name in tokenizer_names):
            return False
        modules_path = path / "modules.json"
        if modules_path.exists() or model_name.startswith("intfloat/multilingual-e5"):
            modules = _json(modules_path)
            if not isinstance(modules, list) or not modules:
                return False
            pooling_found = False
            for module in modules:
                if not isinstance(module, dict):
                    return False
                if str(module.get("type", "")).endswith(".Pooling"):
                    pooling_found = True
                    location = module.get("path")
                    if not isinstance(location, str) or not isinstance(_json(_inside(path, location, "config.json")), dict):
                        return False
            if model_name.startswith("intfloat/multilingual-e5") and not pooling_found:
                return False
        return True
    except (OSError, TypeError, ValueError):
        return False


def _ref_label(revision: str | None) -> str:
    ref = "main" if revision is None else revision
    if not isinstance(ref, str) or not ref or len(ref) > 256 or ref != ref.strip():
        raise ValueError("Revisao do modelo invalida.")
    if ref.startswith(("/", "\\")) or "\\" in ref or ":" in ref or any(ord(c) < 32 for c in ref):
        raise ValueError("Revisao do modelo invalida.")
    if any(part in {"", ".", ".."} for part in ref.split("/")):
        raise ValueError("Revisao do modelo invalida.")
    return ref


def _directory_ref(ref: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", ref):
        return ref
    slug = re.sub(r"[^A-Za-z0-9_.-]", "-", ref)[:70].strip(".-") or "ref"
    return slug + "-" + hashlib.sha256(ref.encode("utf-8")).hexdigest()[:12]


def local_model_path(model_name: str, revision: str | None, cache_dir: Path) -> Path:
    """Retorna um diretorio local pronto; reutiliza pesos completos sem rede.

    Revisoes fixadas sao recomendadas. Para uma revisao mutavel como main, o
    marcador preserva a copia ja obtida ate que esse diretorio seja removido.
    Um diretorio explicitamente fornecido pelo usuario e devolvido como esta;
    os carregadores continuam responsaveis por trust_remote_code=False.
    """
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("Informe um identificador ou diretorio de modelo valido.")
    try:
        supplied = Path(model_name).expanduser()
        if supplied.is_dir():
            return supplied.resolve()
    except (OSError, ValueError):
        pass
    try:
        validate_repo_id(model_name)
    except ValueError as exc:
        raise ValueError("Use um identificador Hugging Face valido, como organizacao/modelo.") from exc
    ref = _ref_label(revision)
    cache = Path(cache_dir).expanduser().resolve()
    repo_key = model_name.replace("/", "--")

    legacy_root = _inside(cache, "models--" + repo_key)
    legacy = _inside(legacy_root, "snapshots", _directory_ref(ref))
    if _complete(legacy, model_name):
        return legacy
    reference = _inside(legacy_root, "refs", *ref.split("/"))
    if reference.is_file():
        try:
            resolved_ref = reference.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            resolved_ref = ""
        if re.fullmatch(r"[0-9a-fA-F]{40}", resolved_ref):
            legacy = _inside(legacy_root, "snapshots", resolved_ref)
            if _complete(legacy, model_name):
                return legacy

    target = _inside(cache, "local-models", repo_key, _directory_ref(ref))
    marker = target / _MARKER
    identity = {"schema_version": 1, "model_name": model_name, "revision": ref}
    if _json(marker) == identity and _complete(target, model_name):
        return target
    try:
        target.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=model_name, revision=revision, local_dir=str(target),
            allow_patterns=list(_PATTERNS), ignore_patterns=list(_IGNORED), local_dir_use_symlinks=False,
            endpoint="https://huggingface.co",
        )
        if not _complete(target, model_name):
            raise RuntimeError("O download terminou sem todos os arquivos necessarios do modelo.")
        temporary = target / (_MARKER + "." + uuid4().hex + ".tmp")
        temporary.write_text(json.dumps(identity, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(marker)
    except Exception as exc:
        raise RuntimeError(
            "Nao foi possivel preparar o modelo local. Confira o identificador/revisao, "
            "as permissoes da pasta de cache e a conexao com https://huggingface.co. "
            "No primeiro uso, conecte a internet e repita com HF_HUB_OFFLINE=0."
        ) from exc
    return target
