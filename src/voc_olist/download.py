"""Download público do Kaggle; extrai apenas CSVs esperados, sem executar conteúdo."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile, BadZipFile

DATASET_URL = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
DOWNLOAD_URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
CSV_FILES = (
    "olist_order_reviews_dataset.csv", "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv", "olist_products_dataset.csv",
)


def download_dataset(raw_dir: Path, archive: Path | None = None) -> dict:
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=raw_dir) as temp:
        temp_path = Path(temp)
        zip_path = Path(archive) if archive else temp_path / "olist.zip"
        if not archive:
            try:
                request = Request(DOWNLOAD_URL, headers={"User-Agent": "voc-olist/0.1 (academic project)"})
                with urlopen(request, timeout=120) as response, zip_path.open("wb") as output:
                    total = 0
                    while block := response.read(1024 * 1024):
                        total += len(block)
                        if total > 300 * 1024 * 1024:
                            raise ValueError("Download excedeu 300 MB; verifique a fonte.")
                        output.write(block)
            except (URLError, HTTPError) as exc:
                raise RuntimeError(
                    "Não foi possível baixar do Kaggle. Baixe o ZIP na página oficial e use "
                    "python -m voc_olist download --archive caminho.zip."
                ) from exc
        try:
            with ZipFile(zip_path) as bundle:
                for name in CSV_FILES:
                    matches = [i for i in bundle.infolist() if Path(i.filename).name == name and not i.is_dir()]
                    if len(matches) != 1 or matches[0].file_size > 200 * 1024 * 1024:
                        raise ValueError(f"Arquivo obrigatório ausente, ambíguo ou muito grande no ZIP: {name}")
                    # Basename fixo: nenhum caminho de dentro do ZIP vira destino.
                    with bundle.open(matches[0]) as source, (temp_path / name).open("wb") as output:
                        shutil.copyfileobj(source, output)
        except BadZipFile as exc:
            raise ValueError("A resposta não é um ZIP válido. Use o download manual da página Kaggle.") from exc
        manifest = {"source": DATASET_URL, "download_url": DOWNLOAD_URL,
                    "archive_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(), "files": {}}
        for name in CSV_FILES:
            path = temp_path / name
            manifest["files"][name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
        for name in CSV_FILES:
            (temp_path / name).replace(raw_dir / name)
        (raw_dir / "download_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
