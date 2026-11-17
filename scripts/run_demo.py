"""Registra exemplos reais sem confundir a demonstração com avaliação cega."""
from dataclasses import replace
import argparse
import json
from pathlib import Path

from voc_olist.cli import make_embedder, make_search_index
from voc_olist.config import Settings, generation_defaults
from voc_olist.llm import make_generator
from voc_olist.rag import RagService
from voc_olist.retrieval import VectorIndex


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["native", "transformers", "ollama"], default="native")
    args = parser.parse_args()
    settings = Settings.from_env()
    model, revision = generation_defaults(args.provider)
    settings = replace(settings, provider=args.provider, llm_model=model, llm_revision=revision, top_k=4)
    service = RagService(make_search_index(VectorIndex.load(settings.index_dir), settings), make_embedder(settings), make_generator(settings), settings)
    examples = [
        ("01-atrasos", "O que os clientes relatam sobre atrasos na entrega?", {"score_max": 2}),
        ("02-elogios", "O que os clientes elogiam nas entregas antes do prazo?", {"score_min": 4}),
        ("03-fora-do-escopo", "Qual será o faturamento da empresa em 2027?", {}),
        ("04-sem-evidencias", "O que os clientes relatam sobre entrega em 2040?", {"date_from": "2040-01-01"}),
    ]
    output = settings.root / "reports" / "examples"
    output.mkdir(parents=True, exist_ok=True)
    for name, question, filters in examples:
        result = service.answer(question, filters)
        (output / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(name, result["status"], f"{result['elapsed_seconds']}s", flush=True)
        print(result["answer"] or result["reason"], flush=True)


if __name__ == "__main__":
    main()
