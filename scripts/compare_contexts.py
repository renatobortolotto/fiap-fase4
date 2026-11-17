"""Compare final acceptance context with a completely rebuilt index; no LLM calls."""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

from voc_olist.cli import make_embedder, make_search_index
from voc_olist.config import Settings
from voc_olist.rag import RagService
from voc_olist.retrieval import VectorIndex

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--acceptance', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
settings = replace(Settings.from_env(args.root), embedding_threads=2)
index = make_search_index(VectorIndex.load(settings.index_dir), settings)
service = RagService(index, make_embedder(settings), None, settings)
accepted = json.loads(args.acceptance.read_text(encoding='utf-8'))
report = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
          'purpose': 'same-context comparison without generation, not a new semantic acceptance score',
          'cold_index_manifest': index.manifest, 'results': []}
for old in accepted['results']:
    new = service.answer(old['question'], old.get('requested_filters', old['filters']))
    old_context = [(s['doc_id'], s['context_text']) for s in old['sources']]
    new_context = [(s['doc_id'], s['context_text']) for s in new['sources']]
    report['results'].append({'query_id': old['query_id'], 'same_ordered_context': old_context == new_context,
        'same_scope_code': old['scope']['code'] == new['scope']['code'],
        'same_effective_filters': old['filters'] == new['filters'],
        'old_doc_ids': [s[0] for s in old_context], 'cold_doc_ids': [s[0] for s in new_context]})
report['all_contexts_match'] = all(r['same_ordered_context'] and r['same_scope_code'] and r['same_effective_filters'] for r in report['results'])
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'n': len(report['results']), 'all_contexts_match': report['all_contexts_match'],
                 'changed_ids': [r['query_id'] for r in report['results'] if not (r['same_ordered_context'] and r['same_scope_code'] and r['same_effective_filters'])]}, ensure_ascii=False))
