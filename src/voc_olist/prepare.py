"""Prepare the public Olist reviews without multiplying reviews in metadata joins.

This module deliberately uses only the Python standard library. Input files are
never modified. Each emitted document represents one (review_id, order_id) pair;
there is no generated or imputed customer text in the knowledge base.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterator


REVIEW_FILE = "olist_order_reviews_dataset.csv"
ORDER_FILE = "olist_orders_dataset.csv"
ITEM_FILE = "olist_order_items_dataset.csv"
PRODUCT_FILE = "olist_products_dataset.csv"
_ID = re.compile(r"[0-9a-fA-F]{32}\Z")
_SPACE = re.compile(r"\s+")
_REQUIRED = {
    REVIEW_FILE: {
        "review_id", "order_id", "review_score", "review_comment_title",
        "review_comment_message",
    },
    ORDER_FILE: {
        "order_id", "order_purchase_timestamp", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    },
    ITEM_FILE: {"order_id", "product_id"},
    PRODUCT_FILE: {"product_id", "product_category_name"},
}


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        self.parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.parts.append(" ")


def _clean(value: str | None) -> str:
    """Decode entities and remove markup, preserving accents, case and wording."""
    parser = _TextOnly()
    parser.feed(value or "")
    parser.close()
    return _SPACE.sub(" ", html.unescape("".join(parser.parts))).strip()


def _identifier(value: str | None) -> str | None:
    value = (value or "").strip()
    return value.lower() if _ID.fullmatch(value) else None


def _date(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date().isoformat()
    except (TypeError, ValueError):
        return None


def _timestamp(value: str | None) -> str:
    if not value or not value.strip():
        return ""
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed.isoformat(timespec="microseconds")
    except (TypeError, ValueError):
        return ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(row: dict) -> str:
    return json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _rows(path: Path, source: dict) -> Iterator[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            fields = reader.fieldnames or []
            missing = _REQUIRED[path.name] - set(fields)
            if missing:
                raise ValueError(
                    f"CSV {path.name}: colunas obrigatórias ausentes: {', '.join(sorted(missing))}."
                )
            if len(fields) != len(set(fields)):
                raise ValueError(f"CSV {path.name}: cabeçalho contém colunas duplicadas.")
            for row in reader:
                source["rows_read"] += 1
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(
                        f"CSV {path.name}: linha {reader.line_num} tem quantidade inválida de colunas."
                    )
                yield row
    except (UnicodeError, csv.Error) as exc:
        raise ValueError(f"Não foi possível ler o CSV {path.name}: {exc}") from exc


def _source(path: Path, required: bool = False) -> dict:
    if not path.is_file():
        if required:
            raise FileNotFoundError(
                f"Arquivo obrigatório não encontrado: {path}. Baixe e extraia a base Olist."
            )
        return {"present": False, "required": False, "rows_read": 0, "sha256": None}
    return {
        "present": True, "required": required, "path": str(path.resolve()),
        "bytes": path.stat().st_size, "sha256": _sha256(path), "rows_read": 0,
        "invalid_id_rows": 0, "exact_duplicate_rows": 0, "conflicting_rows": 0,
    }


def _optional_indexes(raw_dir: Path, sources: dict) -> tuple[dict, dict, dict]:
    """Aggregate categories per order before joining to reviews."""
    orders: dict[str, dict] = {}
    products: dict[str, str] = {}
    order_products: dict[str, set[str]] = {}
    for name, key_name, index in (
        (ORDER_FILE, "order_id", orders), (PRODUCT_FILE, "product_id", products),
    ):
        source = sources[name]
        if not source["present"]:
            continue
        signatures: dict[str, set[str]] = {}
        ranks: dict[str, str] = {}
        if name == ORDER_FILE:
            source["invalid_date_values"] = 0
        for row in _rows(raw_dir / name, source):
            key = _identifier(row[key_name])
            if key is None:
                source["invalid_id_rows"] += 1
                continue
            signature = _canonical(row)
            seen = signatures.setdefault(key, set())
            if signature in seen:
                source["exact_duplicate_rows"] += 1
                continue
            if seen:
                source["conflicting_rows"] += 1
            seen.add(signature)
            if name == ORDER_FILE:
                dates = {
                    "purchase_date": _date(row["order_purchase_timestamp"]),
                    "delivered_date": _date(row["order_delivered_customer_date"]),
                    "estimated_date": _date(row["order_estimated_delivery_date"]),
                }
                for column, parsed in zip(
                    ("order_purchase_timestamp", "order_delivered_customer_date",
                     "order_estimated_delivery_date"), dates.values(),
                ):
                    if row[column].strip() and parsed is None:
                        source["invalid_date_values"] += 1
                delivered, estimated = dates["delivered_date"], dates["estimated_date"]
                value = {
                    "purchase_date": dates["purchase_date"],
                    "delivered_late": delivered > estimated if delivered and estimated else None,
                }
            else:
                value = _clean(row["product_category_name"])
            # Optional duplicate keys also have an explicit order-independent policy.
            if key not in ranks or signature > ranks[key]:
                ranks[key] = signature
                index[key] = value
        source["unique_keys"] = len(index)

    source = sources[ITEM_FILE]
    if source["present"]:
        pairs: set[tuple[str, str]] = set()
        source_rows: set[str] = set()
        source["repeated_order_product_rows"] = 0
        for row in _rows(raw_dir / ITEM_FILE, source):
            order_id, product_id = _identifier(row["order_id"]), _identifier(row["product_id"])
            if order_id is None or product_id is None:
                source["invalid_id_rows"] += 1
                continue
            pair = (order_id, product_id)
            if pair in pairs:
                source["repeated_order_product_rows"] += 1
            row_signature = hashlib.sha256(_canonical(row).encode("utf-8")).hexdigest()
            if row_signature in source_rows:
                source["exact_duplicate_rows"] += 1
                continue
            source_rows.add(row_signature)
            pairs.add(pair)
            order_products.setdefault(order_id, set()).add(product_id)
        source["unique_order_product_pairs"] = len(pairs)
        source["unique_orders"] = len(order_products)
        source["pairs_without_product_metadata"] = sum(p not in products for _, p in pairs)
    categories = {
        order_id: sorted({products[p] for p in product_ids if products.get(p)})
        for order_id, product_ids in order_products.items()
    }
    return orders, categories, order_products


def prepare_dataset(raw_dir: Path, output_dir: Path) -> dict:
    """Create documents.jsonl and preparation_report.json and return the report.

    Invalid review IDs (not 32 hexadecimal characters), invalid scores and empty
    text are excluded and counted. Missing/malformed CSV schemas fail explicitly.
    Duplicate policy: exact source rows are discarded; different rows sharing the
    key compete by nonempty/longest cleaned content, latest answer timestamp, then
    canonical source row. Date parsing failures become null and are counted.
    Optional inputs, when supplied, must have their expected Olist columns.
    """
    raw_dir, output_dir = Path(raw_dir), Path(output_dir)
    sources = {
        name: _source(raw_dir / name, required=(name == REVIEW_FILE))
        for name in _REQUIRED
    }
    orders, categories, order_products = _optional_indexes(raw_dir, sources)
    counts = {
        "input_rows": 0, "invalid_id_rows": 0, "invalid_score_rows": 0,
        "invalid_rows": 0, "valid_rows": 0, "empty_text_rows": 0,
        "title_only_rows": 0, "message_only_rows": 0, "title_and_message_rows": 0,
        "invalid_review_date_values": 0, "invalid_answer_timestamp_values": 0,
        "exact_duplicate_rows": 0, "conflicting_rows": 0, "conflicting_keys": 0,
        "unique_keys": 0, "empty_text_keys_excluded": 0,
    }
    candidates: dict[tuple[str, str], tuple[tuple, dict]] = {}
    signatures: dict[tuple[str, str], set[str]] = {}
    conflict_keys = set()
    for row in _rows(raw_dir / REVIEW_FILE, sources[REVIEW_FILE]):
        counts["input_rows"] += 1
        review_id, order_id = _identifier(row["review_id"]), _identifier(row["order_id"])
        invalid = False
        if review_id is None or order_id is None:
            counts["invalid_id_rows"] += 1
            invalid = True
        score_raw = row["review_score"].strip()
        if score_raw not in {"1", "2", "3", "4", "5"}:
            counts["invalid_score_rows"] += 1
            invalid = True
        if invalid:
            counts["invalid_rows"] += 1
            continue
        counts["valid_rows"] += 1
        title, message = _clean(row["review_comment_title"]), _clean(row["review_comment_message"])
        text = "\n".join(part for part in (title, message) if part)
        if not text:
            counts["empty_text_rows"] += 1
        elif title and message:
            counts["title_and_message_rows"] += 1
        elif title:
            counts["title_only_rows"] += 1
        else:
            counts["message_only_rows"] += 1
        review_date = _date(row.get("review_creation_date"))
        answer_ts = _timestamp(row.get("review_answer_timestamp"))
        if (row.get("review_creation_date") or "").strip() and review_date is None:
            counts["invalid_review_date_values"] += 1
        if (row.get("review_answer_timestamp") or "").strip() and not answer_ts:
            counts["invalid_answer_timestamp_values"] += 1
        key = (review_id, order_id)
        signature = _canonical(row)
        seen = signatures.setdefault(key, set())
        if signature in seen:
            counts["exact_duplicate_rows"] += 1
            continue
        if seen:
            counts["conflicting_rows"] += 1
            conflict_keys.add(key)
        seen.add(signature)
        rank = (bool(text), len(text), answer_ts, signature)
        document = {
            "doc_id": hashlib.sha256(f"{review_id}:{order_id}".encode("ascii")).hexdigest(),
            "review_id": review_id, "order_id": order_id, "score": int(score_raw),
            "title": title, "message": message, "text": text, "review_date": review_date,
            "purchase_date": orders.get(order_id, {}).get("purchase_date"),
            "categories": categories.get(order_id, []),
            "delivered_late": orders.get(order_id, {}).get("delivered_late"),
        }
        if key not in candidates or rank > candidates[key][0]:
            candidates[key] = (rank, document)
    counts["conflicting_keys"] = len(conflict_keys)
    counts["unique_keys"] = len(candidates)
    documents = [
        document for _, document in (candidates[key] for key in sorted(candidates))
        if document["text"]
    ]
    counts["empty_text_keys_excluded"] = len(candidates) - len(documents)
    if not documents:
        raise ValueError(
            "Nenhuma avaliação válida com texto foi encontrada. Confira IDs hexadecimais de 32 "
            "caracteres, notas inteiras de 1 a 5 e os campos de título/comentário. "
            f"Diagnóstico: {json.dumps(counts, ensure_ascii=False)}"
        )
    sources[REVIEW_FILE].update({
        "invalid_id_rows": counts["invalid_id_rows"],
        "exact_duplicate_rows": counts["exact_duplicate_rows"],
        "conflicting_rows": counts["conflicting_rows"],
    })
    report = {
        "schema_version": 1, "total_documents": len(documents), "sources": sources,
        "reviews": counts,
        "metadata": {
            "documents_with_order_metadata": sum(d["order_id"] in orders for d in documents),
            "documents_with_item_metadata": sum(d["order_id"] in order_products for d in documents),
            "documents_with_categories": sum(bool(d["categories"]) for d in documents),
            "documents_with_purchase_date": sum(d["purchase_date"] is not None for d in documents),
            "documents_with_delivery_status": sum(d["delivered_late"] is not None for d in documents),
        },
        "policies": {
            "unit": "Uma avaliação por (review_id, order_id); doc_id = sha256(review_id:order_id).",
            "text": "Título e mensagem com HTML removido, entidades decodificadas e espaços normalizados; "
                    "acentos e maiúsculas preservados. Campos ausentes não são inventados. Textos curtos são mantidos.",
            "ids": "IDs devem conter 32 caracteres hexadecimais; valores normalizados em minúsculas.",
            "invalid_reviews": "IDs ou notas inválidos são excluídos e contados; notas válidas: inteiros 1..5.",
            "duplicates": "Linhas de origem idênticas são descartadas. Conflitos por chave preferem texto não "
                          "vazio, maior comprimento do texto limpo, review_answer_timestamp mais recente e, "
                          "por fim, a maior representação JSON canônica da linha. Ordem da entrada não decide.",
            "optional_duplicates": "Pedidos/produtos conflitantes usam a maior linha JSON canônica. "
                                   "Itens repetidos por (order_id, product_id) são consolidados como conjunto; "
                                   "repeated_order_product_rows inclui quantidades legítimas do mesmo produto. "
                                   "exact_duplicate_rows compara a linha completa da origem.",
            "missing": "Sem título e mensagem: chave excluída. Datas ausentes/inválidas: null. "
                       "Metadados opcionais ausentes: null ou lista vazia; CSV opcional presente exige schema válido.",
            "joins": "Categorias distintas são agregadas e ordenadas por pedido antes do join; "
                     "nenhum join multiplica avaliações.",
            "late_delivery": "Compara o dia da entrega com o dia estimado; mesmo dia não conta como atraso. "
                             "Entrega ou previsão ausente/inválida resulta em null.",
            "counts": "Contagens de texto/datas em reviews são por linha válida, antes da deduplicação. "
                      "conflicting_rows conta cada linha distinta adicional da mesma chave.",
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary: list[Path] = []
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", suffix=".tmp",
                                         dir=output_dir, delete=False) as handle:
            temporary.append(Path(handle.name))
            for document in documents:
                handle.write(json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n")
        report["documents_sha256"] = _sha256(temporary[0])
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", suffix=".tmp",
                                         dir=output_dir, delete=False) as handle:
            temporary.append(Path(handle.name))
            json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary[0], output_dir / "documents.jsonl")
        os.replace(temporary[1], output_dir / "preparation_report.json")
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)
    return report
