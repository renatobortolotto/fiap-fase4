"""Comandos reproduzíveis do projeto. Execute python -m voc_olist --help."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import logging
from pathlib import Path
import sys

from .config import Settings, generation_defaults
from .download import download_dataset
from .llm import make_generator
from .prepare import prepare_dataset
from .rag import RagService
from .retrieval import SentenceEmbedder, VectorIndex


def emit(data, output=None):
    content = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
    print(content)


def make_embedder(settings):
    return SentenceEmbedder(settings.embedding_model, settings.embedding_revision, settings.cache_dir, settings.embedding_threads)


def make_search_index(index, settings):
    if settings.retrieval_mode == "hybrid":
        from .hybrid import HybridIndex
        return HybridIndex(index)
    return index


def add_search_options(command):
    command.add_argument("--top-k", type=int, default=None)
    command.add_argument("--min-similarity", type=float, default=None)
    command.add_argument("--score-min", type=int, choices=range(1, 6))
    command.add_argument("--score-max", type=int, choices=range(1, 6))
    command.add_argument("--date-from", help="Data da compra YYYY-MM-DD")
    command.add_argument("--date-to", help="Data da compra YYYY-MM-DD")
    command.add_argument("--category", help="Categoria original Olist, por exemplo beleza_saude")
    command.add_argument("--late", choices=["yes", "no"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Voice of Customer Olist: preparação, busca e RAG com evidências")
    parser.add_argument("--root", type=Path, help="Raiz do projeto (opcional)")
    sub = parser.add_subparsers(dest="command", required=True)
    download = sub.add_parser("download", help="Baixar base pública Olist ou extrair ZIP baixado manualmente")
    download.add_argument("--archive", type=Path)
    sub.add_parser("prepare", help="Limpar avaliações e agregar metadados, gerando relatório")
    index = sub.add_parser("index", help="Criar índice de embeddings E5 em CPU")
    index.add_argument("--batch-size", type=int, default=64)
    index.add_argument("--documents", type=Path, help="JSONL alternativo, por exemplo pool de avaliação")
    index.add_argument("--index-dir", type=Path, help="Destino alternativo para o índice")
    ask = sub.add_parser("ask", help="Responder uma pergunta com fontes identificáveis")
    ask.add_argument("question")
    add_search_options(ask)
    ask.add_argument("--provider", choices=["native", "ollama", "transformers", "evidence"])
    ask.add_argument("--model", help="Modelo gerador, conforme provedor selecionado")
    ask.add_argument("--llm-revision", help="Commit do modelo gerador no Hugging Face")
    ask.add_argument("--output", type=Path, help="Salvar a consulta e as fontes em JSON")
    evaluate = sub.add_parser("evaluate", help="Medir recuperação sobre perguntas com relevância rotulada")
    evaluate.add_argument("--queries", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, default=Path("reports/evaluation.json"))
    evaluate.add_argument("--top-k", type=int, default=None)
    evaluate.add_argument("--min-similarity", type=float, default=None)
    evaluate.add_argument("--index-dir", type=Path, help="Índice alternativo do pool de avaliação")
    evaluate.add_argument("--retrieval-mode", choices=["dense", "hybrid"], help="Comparar busca densa ou reranking híbrido")
    sub.add_parser("status", help="Conferir disponibilidade dos dados e índice sem carregar modelos")
    sub.add_parser("models", help="Obter os modelos locais e o runtime portátil, sem criar índice")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    try:
        settings = Settings.from_env(args.root)
        overrides = {}
        for name in ("top_k", "min_similarity"):
            if getattr(args, name, None) is not None:
                overrides[name] = getattr(args, name)
        if getattr(args, "retrieval_mode", None):
            overrides["retrieval_mode"] = args.retrieval_mode
        if getattr(args, "provider", None):
            overrides["provider"] = args.provider
            if args.provider != settings.provider and not args.model:
                overrides["llm_model"], overrides["llm_revision"] = generation_defaults(args.provider)
        if getattr(args, "model", None):
            overrides["llm_model"], overrides["llm_revision"] = args.model, None
        if getattr(args, "llm_revision", None):
            overrides["llm_revision"] = args.llm_revision
        settings = replace(settings, **overrides)
        if not -1 <= settings.min_similarity <= 1 or not 1 <= settings.min_evidences <= settings.top_k:
            raise ValueError("Use -1 <= min-similarity <= 1 e top-k >= MIN_EVIDENCES >= 1.")
        if args.command == "download":
            emit(download_dataset(settings.raw_dir, args.archive))
        elif args.command == "prepare":
            emit(prepare_dataset(settings.raw_dir, settings.processed_dir))
        elif args.command == "models":
            from .model_store import local_model_path
            local_model_path(settings.embedding_model, settings.embedding_revision, settings.cache_dir)
            if settings.provider == "native":
                from .native_runtime import ensure_native_runtime
                ensure_native_runtime(settings.root / ".cache")
            elif settings.provider == "transformers":
                local_model_path(settings.llm_model, settings.llm_revision, settings.cache_dir)
            emit({"provider": settings.provider, "embedding_model": settings.embedding_model,
                  "llm_model": settings.llm_model, "note": "Arquivos preparados; o modelo é carregado na primeira consulta. Ollama requer servidor próprio."})
        elif args.command == "index":
            emit(VectorIndex.build(args.documents or settings.processed_dir / "documents.jsonl", args.index_dir or settings.index_dir,
                                   make_embedder(settings), args.batch_size))
        elif args.command in {"ask", "evaluate"}:
            idx = make_search_index(VectorIndex.load(getattr(args, "index_dir", None) or settings.index_dir), settings)
            embedder = make_embedder(settings)
            if args.command == "ask":
                filters = {k: getattr(args, k) for k in ("score_min", "score_max", "date_from", "date_to", "category")
                           if getattr(args, k) is not None}
                if args.late:
                    filters["delivered_late"] = args.late == "yes"
                result = RagService(idx, embedder, make_generator(settings), settings).answer(args.question, filters)
                emit(result, args.output)
            else:
                from .evaluation import evaluate_retrieval
                result = evaluate_retrieval(idx, embedder, args.queries, settings.top_k, settings.min_similarity)
                result["retrieval_mode"], result["index_manifest"] = settings.retrieval_mode, idx.manifest
                emit(result, args.output)
        else:
            emit({"root": str(settings.root), "raw_data": (settings.raw_dir / "olist_order_reviews_dataset.csv").exists(),
                  "documents": (settings.processed_dir / "documents.jsonl").exists(),
                  "index": (settings.index_dir / "manifest.json").exists(),
                  "provider": settings.provider, "llm_model": settings.llm_model,
                  "note": "Disponibilidade de arquivos; não confirma servidor, modelo carregado ou qualidade das respostas."})
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
