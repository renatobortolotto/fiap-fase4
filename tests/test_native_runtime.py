import hashlib
import io
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit
from zipfile import ZipFile, ZipInfo

import pytest

import voc_olist.native_runtime as native


class Response(io.BytesIO):
    def __init__(self, data, status, headers, url="https://huggingface.co/fixture"):
        super().__init__(data)
        self.status, self.headers, self.url = status, headers, url
    def geturl(self):
        return self.url


def asset(name, data):
    return native._Asset(name, "https://huggingface.co/fixture/" + name,
                         len(data), hashlib.sha256(data).hexdigest())


def zip_data(entries):
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return stream.getvalue()


@pytest.fixture
def small_downloads(monkeypatch):
    monkeypatch.setattr(native, "_CHUNK_SIZE", 8)
    monkeypatch.setattr(native, "_WORKERS", 3)
    monkeypatch.setattr(native, "_PROGRESS_INTERVAL", 16)
    monkeypatch.setattr(native.time, "sleep", lambda _: None)


def range_server(monkeypatch, registry, *, ignored=False, wrong_range=False):
    requests = []
    def open_url(request, timeout):
        requests.append(request)
        payload = registry[urlsplit(request.full_url).path.rsplit("/", 1)[-1]]
        header = request.get_header("Range")
        if not header or ignored:
            return Response(payload, 200, {"Content-Length": str(len(payload))})
        start, end = map(int, re.fullmatch(r"bytes=(\d+)-(\d+)", header).groups())
        returned_start = start + 1 if wrong_range else start
        return Response(payload[start:end + 1], 206, {"Content-Range": f"bytes {returned_start}-{end}/{len(payload)}"})
    monkeypatch.setattr(native, "urlopen", open_url)
    return requests


def test_range_download_integrity_and_valid_cache_skips_all_network(tmp_path, monkeypatch, small_downloads):
    content = b"0123456789abcdefghi"
    spec = asset("weights.gguf", content)
    requests = range_server(monkeypatch, {spec.name: content})
    target = tmp_path / spec.name
    assert native._download_asset(spec, target).read_bytes() == content
    assert len(requests) == 3
    assert not list(tmp_path.rglob("*.part"))
    monkeypatch.setattr(native, "urlopen", lambda *a, **k: pytest.fail("valid cache must be offline"))
    assert native._download_asset(spec, target) == target


def test_complete_part_is_resumed_and_unrelated_file_is_not_removed(tmp_path, monkeypatch, small_downloads):
    content = b"abcdefghijklmnopqrst"
    spec = asset("resume.gguf", content)
    directory = tmp_path / ".download-parts" / spec.sha256
    directory.mkdir(parents=True)
    (directory / native._part_name(0, 7)).write_bytes(content[:8])
    (directory / "user-note.txt").write_text("keep", encoding="utf-8")
    requests = range_server(monkeypatch, {spec.name: content})
    native._download_asset(spec, tmp_path / spec.name)
    assert {r.get_header("Range") for r in requests} == {"bytes=8-15", "bytes=16-19"}
    assert (directory / "user-note.txt").read_text() == "keep"
    assert not list(directory.glob("*.part"))


def test_short_saved_part_is_downloaded_again(tmp_path, monkeypatch, small_downloads):
    content = b"abcdefghijklmnopqrst"
    spec = asset("partial.gguf", content)
    directory = tmp_path / ".download-parts" / spec.sha256
    directory.mkdir(parents=True)
    (directory / native._part_name(0, 7)).write_bytes(b"bad")
    requests = range_server(monkeypatch, {spec.name: content})
    native._download_asset(spec, tmp_path / spec.name)
    assert "bytes=0-7" in [r.get_header("Range") for r in requests]


def test_range_unsupported_falls_back_to_verified_sequential_download(tmp_path, monkeypatch, small_downloads):
    content = b"sequential file content"
    spec = asset("sequential.gguf", content)
    requests = range_server(monkeypatch, {spec.name: content}, ignored=True)
    native._download_asset(spec, tmp_path / spec.name)
    assert [r.get_header("Range") for r in requests] == ["bytes=0-7", None]
    assert (tmp_path / spec.name).read_bytes() == content


def test_wrong_content_range_never_publishes_file(tmp_path, monkeypatch, small_downloads):
    content = b"range mismatch"
    spec = asset("bad-range.gguf", content)
    range_server(monkeypatch, {spec.name: content}, wrong_range=True)
    with pytest.raises(RuntimeError, match="Content-Range"):
        native._download_asset(spec, tmp_path / spec.name)
    assert not (tmp_path / spec.name).exists()


def test_hash_mismatch_cleans_only_owned_parts_and_keeps_existing_target(tmp_path, monkeypatch, small_downloads):
    expected = b"correct expected content"
    wrong = b"wronggg expected content"
    assert len(expected) == len(wrong)
    spec = asset("bad-hash.gguf", expected)
    target = tmp_path / spec.name
    target.write_bytes(b"previous cache")
    directory = tmp_path / ".download-parts" / spec.sha256
    directory.mkdir(parents=True)
    (directory / "keep.txt").write_text("keep", encoding="utf-8")
    range_server(monkeypatch, {spec.name: wrong})
    with pytest.raises(RuntimeError, match="SHA-256"):
        native._download_asset(spec, target)
    assert target.read_bytes() == b"previous cache"
    assert not list(directory.glob("*.part"))
    assert (directory / "keep.txt").read_text() == "keep"


def test_sequential_hash_mismatch_is_rejected(tmp_path, monkeypatch, small_downloads):
    spec = asset("bad-sequential.gguf", b"correct")
    range_server(monkeypatch, {spec.name: b"WRONGGG"}, ignored=True)
    with pytest.raises(RuntimeError, match="SHA-256"):
        native._download_asset(spec, tmp_path / spec.name)
    assert not (tmp_path / spec.name).exists()


def test_corrupt_valid_size_cache_is_replaced_after_verification(tmp_path, monkeypatch, small_downloads):
    content = b"a valid cache"
    spec = asset("repair.gguf", content)
    target = tmp_path / spec.name
    target.write_bytes(b"x" * len(content))
    range_server(monkeypatch, {spec.name: content})
    native._download_asset(spec, target)
    assert target.read_bytes() == content


@pytest.mark.parametrize("bad_name", ["../escape.exe", "/absolute.exe", "C:/escape.exe", "..\\escape.exe", "file.exe:stream"])
def test_zip_paths_are_all_validated_before_any_extraction(tmp_path, bad_name):
    data = zip_data([("llama-server.exe", b"fixture server"), (bad_name, b"unsafe")])
    archive = tmp_path / "runtime.zip"
    archive.write_bytes(data)
    destination = tmp_path / "runtime"
    with pytest.raises(RuntimeError, match="inseguro"):
        native._extract_runtime(archive, destination)
    assert not destination.exists()


def test_zip_symlink_is_rejected(tmp_path):
    archive = tmp_path / "runtime.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("llama-server.exe", b"fixture")
        link = ZipInfo("library.dll")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(link, "../outside")
    with pytest.raises(RuntimeError, match="links"):
        native._extract_runtime(archive, tmp_path / "runtime")


def test_zip_keeps_libraries_and_licenses_and_repairs_tampered_components(tmp_path):
    archive = tmp_path / "runtime.zip"
    archive.write_bytes(zip_data([("bin/llama-server.exe", b"server"), ("bin/ggml.dll", b"library"), ("LICENSE", b"license")]))
    destination = tmp_path / "runtime"
    server = native._extract_runtime(archive, destination)
    assert server.read_bytes() == b"server"
    assert (destination / "LICENSE").read_bytes() == b"license"
    (server.parent / "ggml.dll").write_bytes(b"tampered")
    assert native._extract_runtime(archive, destination) == server
    assert (server.parent / "ggml.dll").read_bytes() == b"library"


def test_runtime_ensure_returns_both_shards_and_reuses_verified_assets(tmp_path, monkeypatch, small_downloads):
    archive = zip_data([("llama-server.exe", b"fixture server"), ("ggml.dll", b"fixture library"), ("LICENSE", b"license")])
    runtime = asset("runtime.zip", archive)
    models = (asset("first.gguf", b"first shard"), asset("second.gguf", b"second shard"))
    monkeypatch.setattr(native, "_RUNTIME_ASSET", runtime)
    monkeypatch.setattr(native, "_MODEL_ASSETS", models)
    monkeypatch.setattr(native.platform, "system", lambda: "Windows")
    monkeypatch.setattr(native.platform, "machine", lambda: "AMD64")
    registry = {runtime.name: archive, models[0].name: b"first shard", models[1].name: b"second shard"}
    range_server(monkeypatch, registry)
    server, first = native.ensure_native_runtime(tmp_path)
    assert server.name == "llama-server.exe"
    assert first.read_bytes() == b"first shard"
    assert (first.parent / "second.gguf").read_bytes() == b"second shard"
    assert server.is_relative_to(tmp_path) and first.is_relative_to(tmp_path)
    monkeypatch.setattr(native, "urlopen", lambda *a, **k: pytest.fail("verified assets must not access network"))
    assert native.ensure_native_runtime(tmp_path) == (server, first)


@pytest.mark.parametrize("system,machine", [("Linux", "x86_64"), ("Windows", "ARM64"), ("Darwin", "arm64")])
def test_native_platform_has_clear_alternative_provider_error(tmp_path, monkeypatch, system, machine):
    monkeypatch.setattr(native.platform, "system", lambda: system)
    monkeypatch.setattr(native.platform, "machine", lambda: machine)
    with pytest.raises(RuntimeError, match="transformers ou ollama"):
        native.ensure_native_runtime(tmp_path)


def test_insecure_download_source_is_rejected(tmp_path, small_downloads):
    spec = native._Asset("no.gguf", "http://huggingface.co/no.gguf", 1, hashlib.sha256(b"a").hexdigest())
    with pytest.raises(RuntimeError, match="HTTPS"):
        native._download_asset(spec, tmp_path / spec.name)
