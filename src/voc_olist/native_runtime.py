"""Runtime CPU portatil e pesos GGUF oficiais, com tamanho e SHA-256 fixados.

Nao instala programas globalmente e nao inicia processos. Arquivos baixados so
substituem o cache depois da verificacao integral. Partes retomaveis pertencem
a um unico asset identificado por seu hash.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct-GGUF:Q4_K_M"
MODEL_REVISION = "bb5d59e06d9551d752d08b292a50eb208b07ab1f"
RUNTIME_VERSION = "b12359"

logger = logging.getLogger(__name__)
_CHUNK_SIZE = 8 * 1024 * 1024
_WORKERS = 8
_PROGRESS_INTERVAL = 128 * 1024 * 1024
_ENSURE_LOCK = threading.Lock()


@dataclass(frozen=True)
class _Asset:
    name: str
    url: str
    size: int
    sha256: str


_RUNTIME_ASSET = _Asset(
    "llama-b12359-bin-win-cpu-x64.zip",
    "https://github.com/ggml-org/llama.cpp/releases/download/b12359/llama-b12359-bin-win-cpu-x64.zip",
    25097509,
    "837c1655e87df3b66989f4be33a792a1399c785bf259038dc75c900096683e69",
)
_MODEL_ASSETS = (
    _Asset(
        "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
        "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/"
        + MODEL_REVISION + "/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf?download=true",
        3993201344,
        "dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db",
    ),
    _Asset(
        "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf",
        "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/"
        + MODEL_REVISION + "/qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf?download=true",
        689872288,
        "539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a",
    ),
)


class _RangeUnsupported(Exception):
    pass


def _inside(root: Path, *parts: str) -> Path:
    target = root.joinpath(*parts).resolve()
    if not target.is_relative_to(root.resolve()):
        raise RuntimeError("Destino de cache fora da pasta autorizada.")
    return target


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(_CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _matches(path: Path, asset: _Asset) -> bool:
    return path.is_file() and path.stat().st_size == asset.size and _sha256(path) == asset.sha256


def _ranges(size: int):
    return [(start, min(size, start + _CHUNK_SIZE) - 1) for start in range(0, size, _CHUNK_SIZE)]


def _part_name(start: int, end: int) -> str:
    return f"{start:012d}-{end:012d}.part"


def _open(asset: _Asset, headers: dict | None = None, start: int | None = None):
    parsed = urlsplit(asset.url)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "huggingface.co"} or parsed.username:
        raise RuntimeError("A origem do asset deve ser o GitHub ou Hugging Face oficial via HTTPS.")
    url = asset.url
    if start is not None:
        url += ("&" if "?" in url else "?") + "voc_part=" + str(start)
    request = Request(url, headers={"User-Agent": "voc-olist/native-runtime", "Accept-Encoding": "identity", **(headers or {})})
    response = urlopen(request, timeout=60)
    if hasattr(response, "geturl") and urlsplit(response.geturl()).scheme != "https":
        response.close()
        raise RuntimeError("O download foi redirecionado para uma origem sem HTTPS.")
    return response


def _download_part(asset: _Asset, directory: Path, start: int, end: int) -> Path:
    target = _inside(directory, _part_name(start, end))
    expected_size = end - start + 1
    if target.is_file() and target.stat().st_size == expected_size:
        return target
    for attempt in range(3):
        temporary = _inside(directory, target.name + "." + uuid4().hex + ".tmp")
        try:
            try:
                response = _open(asset, {"Range": f"bytes={start}-{end}"}, start=start)
            except HTTPError as exc:
                if exc.code in {400, 405, 416}:
                    raise _RangeUnsupported() from exc
                raise
            with response:
                if response.status == 200:
                    raise _RangeUnsupported()
                content_range = response.headers.get("Content-Range", "")
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range, flags=re.IGNORECASE)
                if response.status != 206 or not match or tuple(map(int, match.groups())) != (start, end, asset.size):
                    raise RuntimeError(f"Content-Range invalido ao obter {asset.name}.")
                data = response.read(expected_size + 1)
                if len(data) != expected_size:
                    raise RuntimeError(f"Parte incompleta ao obter {asset.name}.")
            temporary.write_bytes(data)
            temporary.replace(target)
            return target
        except _RangeUnsupported:
            raise
        except Exception:
            if attempt == 2:
                raise
            time.sleep(0.5 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)
    raise RuntimeError("Falha inesperada no download de uma parte.")


def _cleanup_parts(directory: Path, ranges: list[tuple[int, int]]) -> None:
    # Only deterministic filenames owned by this asset are removed, never a
    # recursive directory deletion that could include unrelated user files.
    for start, end in ranges:
        _inside(directory, _part_name(start, end)).unlink(missing_ok=True)
    try:
        directory.rmdir()
        directory.parent.rmdir()
    except OSError:
        pass


def _sequential(asset: _Asset, temporary: Path) -> None:
    logger.info("Servidor sem Range; baixando %s sequencialmente", asset.name)
    received, next_progress = 0, _PROGRESS_INTERVAL
    digest = hashlib.sha256()
    with _open(asset) as response, temporary.open("wb") as destination:
        if response.status != 200:
            raise RuntimeError(f"Resposta HTTP invalida para {asset.name}.")
        for block in iter(lambda: response.read(_CHUNK_SIZE), b""):
            received += len(block)
            if received > asset.size:
                raise RuntimeError(f"Tamanho excede o esperado para {asset.name}.")
            destination.write(block)
            digest.update(block)
            if received >= next_progress:
                logger.info("%s: %.0f/%.0f MiB", asset.name, received / 2**20, asset.size / 2**20)
                next_progress = (received // _PROGRESS_INTERVAL + 1) * _PROGRESS_INTERVAL
    if received != asset.size or digest.hexdigest() != asset.sha256:
        raise RuntimeError(f"Tamanho ou SHA-256 invalido para {asset.name}.")


def _download_asset(asset: _Asset, target: Path) -> Path:
    if asset.size < 1 or not re.fullmatch(r"[0-9a-f]{64}", asset.sha256):
        raise RuntimeError("Metadados invalidos para o asset nativo.")
    if _matches(target, asset):
        logger.info("Cache conferido: %s", asset.name)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    directory = _inside(target.parent, ".download-parts", asset.sha256)
    directory.mkdir(parents=True, exist_ok=True)
    ranges = _ranges(asset.size)
    temporary = _inside(target.parent, target.name + "." + uuid4().hex + ".download")
    logger.info("Obtendo %s (%.1f MiB)", asset.name, asset.size / 2**20)
    try:
        try:
            # Probe once before scheduling a large number of parallel requests.
            _download_part(asset, directory, *ranges[0])
            completed, next_progress = ranges[0][1] + 1, _PROGRESS_INTERVAL
            with ThreadPoolExecutor(max_workers=_WORKERS) as executor:
                jobs = {executor.submit(_download_part, asset, directory, start, end): (start, end)
                        for start, end in ranges[1:]}
                try:
                    for job in as_completed(jobs):
                        job.result()
                        start, end = jobs[job]
                        completed += end - start + 1
                        if completed >= next_progress or completed == asset.size:
                            logger.info("%s: %.0f/%.0f MiB recebidos ou retomados", asset.name, completed / 2**20, asset.size / 2**20)
                            next_progress = (completed // _PROGRESS_INTERVAL + 1) * _PROGRESS_INTERVAL
                except Exception:
                    for job in jobs:
                        job.cancel()
                    raise
            digest = hashlib.sha256()
            with temporary.open("wb") as destination:
                for start, end in ranges:
                    with _inside(directory, _part_name(start, end)).open("rb") as source:
                        for block in iter(lambda: source.read(_CHUNK_SIZE), b""):
                            destination.write(block)
                            digest.update(block)
            if temporary.stat().st_size != asset.size or digest.hexdigest() != asset.sha256:
                _cleanup_parts(directory, ranges)
                raise RuntimeError(f"Tamanho ou SHA-256 invalido para {asset.name}; partes invalidas removidas.")
        except _RangeUnsupported:
            _sequential(asset, temporary)
        temporary.replace(target)
        _cleanup_parts(directory, ranges)
        logger.info("SHA-256 conferido: %s", asset.name)
        return target
    except Exception as exc:
        raise RuntimeError(
            f"Nao foi possivel obter {asset.name}. Confira a rede e o espaco de disco e repita; "
            "partes completas validaveis serao retomadas. " + str(exc)
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def _safe_zip_path(root: Path, filename: str) -> Path:
    pure = PurePosixPath(filename.replace("\\", "/"))
    if pure.is_absolute() or any(part == ".." or ":" in part for part in pure.parts):
        raise RuntimeError("ZIP do runtime contem um caminho inseguro.")
    return _inside(root, *pure.parts)


def _zip_digest(bundle: ZipFile, info) -> str:
    digest = hashlib.sha256()
    with bundle.open(info) as source:
        for block in iter(lambda: source.read(_CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _extract_runtime(archive: Path, destination: Path) -> Path:
    try:
        with ZipFile(archive) as bundle:
            entries, seen = [], set()
            if sum(info.file_size for info in bundle.infolist()) > 1024**3:
                raise RuntimeError("ZIP do runtime excede o limite de extracao.")
            for info in bundle.infolist():
                path = _safe_zip_path(destination, info.filename)
                identity = str(path).casefold()
                if identity in seen or stat.S_ISLNK(info.external_attr >> 16):
                    raise RuntimeError("ZIP do runtime contem links ou caminhos duplicados.")
                seen.add(identity)
                entries.append((info, path))
            servers = [path for info, path in entries if not info.is_dir() and path.name.lower() == "llama-server.exe"]
            if len(servers) != 1:
                raise RuntimeError("ZIP do runtime deve conter um unico llama-server.exe.")
            # Validate every path before writing even the first archive member.
            for info, path in entries:
                if info.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                    continue
                expected = _zip_digest(bundle, info)
                if path.is_file() and path.stat().st_size == info.file_size and _sha256(path) == expected:
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = _inside(path.parent, path.name + "." + uuid4().hex + ".extract")
                try:
                    digest = hashlib.sha256()
                    with bundle.open(info) as source, temporary.open("wb") as target:
                        for block in iter(lambda: source.read(_CHUNK_SIZE), b""):
                            target.write(block)
                            digest.update(block)
                    if temporary.stat().st_size != info.file_size or digest.hexdigest() != expected:
                        raise RuntimeError("Falha ao conferir um componente do runtime.")
                    temporary.replace(path)
                finally:
                    temporary.unlink(missing_ok=True)
            return servers[0]
    except (BadZipFile, OSError) as exc:
        raise RuntimeError("Nao foi possivel extrair o runtime nativo verificado.") from exc


def ensure_native_runtime(cache_dir: Path) -> tuple[Path, Path]:
    """Obtem os assets fixados e retorna servidor CPU e primeiro shard GGUF.

    O provedor portatil atual atende Windows x64. Outros sistemas podem usar os
    provedores transformers ou ollama. Nao inicia servidor nem instala servicos.
    """
    if platform.system() != "Windows" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("O runtime portatil exige Windows AMD64/x64; use transformers ou ollama neste sistema.")
    root = Path(cache_dir).expanduser().resolve()
    with _ENSURE_LOCK:
        native = _inside(root, "native")
        archive = _download_asset(_RUNTIME_ASSET, _inside(native, "archives", _RUNTIME_ASSET.name))
        server = _extract_runtime(archive, _inside(native, "llama.cpp-" + RUNTIME_VERSION))
        model_dir = _inside(native, "models", "qwen2.5-7b-instruct-q4_k_m-" + MODEL_REVISION)
        models = [_download_asset(asset, _inside(model_dir, asset.name)) for asset in _MODEL_ASSETS]
        return server, models[0]
