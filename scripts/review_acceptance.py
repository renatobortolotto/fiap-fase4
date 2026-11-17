"""Execução reproduzível de consultas de aceitação; não substitui revisão das fontes."""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path

from voc_olist.cli import make_embedder, make_search_index
from voc_olist.config import Settings, generation_defaults
from voc_olist.llm import make_generator
from voc_olist.rag import RagService
from voc_olist.retrieval import VectorIndex


class TracingGenerator:
    """Rastreio de saídas do ensaio, incluindo rejeitadas; não são conclusões validadas."""
    def __init__(self, generator):
        self.generator = generator
        self.trace = []
    def generate(self, messages):
        result = self.generator.generate(messages)
        self.trace.append(result)
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path)
    parser.add_argument("--provider", choices=["native", "transformers", "ollama"], default="native")
    parser.add_argument("--questions", type=Path, default=Path("evaluation/review_questions.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("reports/review-20261116/acceptance-results.json"))
    parser.add_argument("--ids", help="IDs separados por vírgula, útil para diagnóstico")
    parser.add_argument("--resume", action="store_true", help="Conservar casos já executados neste arquivo")
    args = parser.parse_args()
    settings = Settings.from_env(args.root)
    model, revision = generation_defaults(args.provider)
    settings = replace(settings, provider=args.provider, llm_model=model, llm_revision=revision)
    questions = [json.loads(line) for line in args.questions.read_text(encoding="utf-8").splitlines() if line.strip()]
    requested = set(args.ids.split(",")) if args.ids else None
    output = {"review_type": "assistant_assisted_technical_acceptance_not_human_benchmark",
              "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "questions_sha256": hashlib.sha256(args.questions.read_bytes()).hexdigest(),
              "packages": {p: importlib.metadata.version(p) for p in ["transformers", "sentence-transformers", "torch", "lm-format-enforcer"]},
              "model": model, "revision": revision, "results": []}
    if args.resume and args.output.exists():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        if previous["questions_sha256"] != output["questions_sha256"] or previous["revision"] != revision:
            raise ValueError("Não é possível retomar resultados com perguntas ou modelo diferentes.")
        output["results"] = previous["results"]
    completed = {r["query_id"] for r in output["results"]}
    generator = TracingGenerator(make_generator(settings))
    service = RagService(make_search_index(VectorIndex.load(settings.index_dir), settings),
                         make_embedder(settings), generator, settings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for question in questions:
        if question["query_id"] in completed or requested and question["query_id"] not in requested:
            continue
        generator.trace = []
        result = service.answer(question["question"], question.get("filters"))
        result["generation_trace_unvalidated"] = generator.trace
        result.update({k: question[k] for k in ["query_id", "category", "allowed_statuses", "expectation"]})
        result["status_matches_expected"] = result["status"] in question["allowed_statuses"]
        output["results"].append(result)
        output["status_matches_expected"] = sum(r["status_matches_expected"] for r in output["results"])
        output["n_executed"] = len(output["results"])
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(result["query_id"], result["status"], str(result["elapsed_seconds"]) + "s",
              "status_ok=" + str(result["status_matches_expected"]), "findings=" + str(len(result["findings"])), flush=True)
        print(result["answer"] or result["reason"], flush=True)


if __name__ == "__main__":
    main()
