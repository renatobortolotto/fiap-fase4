"""Lexical reranking of an eligible dense candidate pool, with reciprocal ranks.

This is deliberately a bounded hybrid reranker: BM25 cannot recover a review
outside the dense pool. The base index supplies up to max(candidate_k * 4, top_k)
distinct reviews after metadata filtering and the cosine threshold. That single
search also preserves the base model/revision validation and encodes the query
only once. BM25 statistics use the complete corpus, but lexical ranking is
restricted to those eligible candidates. The persisted vector index is unchanged.
"""
from __future__ import annotations

from collections import Counter
import math
import re
import unicodedata


# Negation words (nao, nunca, nem, sem) are intentionally absent from this set.
_STOPWORDS = frozenset({
    "a", "as", "o", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas", "ao", "aos", "com", "por", "para", "pra", "e", "ou",
    "mas", "que", "qual", "quais", "como", "sobre", "ser", "sao", "foi", "foram", "era",
    "eram", "esta", "estao", "esse", "essa", "esses", "essas", "este", "estes", "estas",
    "isso", "isto", "aquilo", "eu", "voce", "voces", "me", "se", "sua", "seu", "suas",
    "seus", "nosso", "nossa", "nossos", "nossas", "ele", "ela", "eles", "elas", "pelo",
    "pela", "pelos", "pelas", "num", "numa", "aquela", "aquele", "aquelas", "aqueles",
})
_WORDS = re.compile(r"[a-z0-9]+")
_RRF_CONSTANT = 60


def _tokens(text: str) -> list[str]:
    folded = "".join(
        char for char in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(char)
    )
    words = (word for word in _WORDS.findall(folded) if word not in _STOPWORDS)
    # A light plural normalization, not a Portuguese morphological stemmer.
    return [word[:-1] if len(word) > 4 and word.endswith("s") else word for word in words]


class HybridIndex:
    """Delegate index storage and fuse dense/BM25 ranks within a dense pool.

    Equal-weight RRF uses 1/(60 + one-based rank). Only a positive lexical score
    adds a lexical rank contribution. Scores are ordering aids, not confidence or
    probabilities. Returned ``similarity`` always remains the original cosine.
    """

    def __init__(self, base_index, candidate_k: int = 50):
        if type(candidate_k) is not int or candidate_k < 1:
            raise ValueError("candidate_k deve ser um inteiro positivo.")
        self.base_index = base_index
        self.candidate_k = candidate_k
        self._term_counts: dict[str, Counter] = {}
        document_frequency: Counter = Counter()
        total_length = 0
        for document in self.documents:
            text = document["text"]
            counts = Counter(_tokens(text))
            self._term_counts[text] = counts
            document_frequency.update(counts.keys())
            total_length += sum(counts.values())
        count = len(self.documents)
        self._average_length = total_length / count if count and total_length else 1.0
        self._idf = {
            term: math.log(1.0 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    @property
    def documents(self):
        return self.base_index.documents

    @property
    def manifest(self):
        return self.base_index.manifest

    @property
    def vectors(self):
        return self.base_index.vectors

    def _bm25(self, terms: set[str], text: str) -> float:
        counts = self._term_counts.get(text)
        if counts is None:
            # A caller-supplied index may expose a copied or newly appended review.
            counts = Counter(_tokens(text))
        length = sum(counts.values())
        normalization = 1.5 * (1.0 - 0.75 + 0.75 * length / self._average_length)
        score = 0.0
        for term in sorted(terms):
            frequency = counts.get(term, 0)
            if frequency:
                score += self._idf.get(term, 0.0) * frequency * 2.5 / (frequency + normalization)
        return score

    def search(self, question: str, embedder, top_k: int = 8,
               filters: dict | None = None, min_similarity: float = 0.75) -> list[dict]:
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k deve ser um inteiro positivo.")
        pool_size = max(self.candidate_k * 4, top_k)
        dense_hits = self.base_index.search(
            question, embedder, top_k=pool_size, filters=filters,
            min_similarity=min_similarity,
        )
        # The real base already deduplicates text. Retain that guarantee for
        # compatible custom indexes without mutating their documents or hits.
        pool = []
        seen = set()
        for hit in dense_hits:
            text_key = " ".join(hit["document"]["text"].casefold().split())
            if text_key in seen:
                continue
            seen.add(text_key)
            pool.append(hit)
        terms = set(_tokens(question))
        lexical_scores = [self._bm25(terms, hit["document"]["text"]) for hit in pool] if terms else []
        lexical_order = sorted(
            (position for position, score in enumerate(lexical_scores) if score > 0.0),
            key=lambda position: (
                -lexical_scores[position], position,
                str(pool[position]["document"].get("doc_id", "")),
            ),
        )
        lexical_ranks = {position: rank for rank, position in enumerate(lexical_order, 1)}
        ranked = []
        for position, hit in enumerate(pool):
            score = 1.0 / (_RRF_CONSTANT + position + 1)
            if position in lexical_ranks:
                score += 1.0 / (_RRF_CONSTANT + lexical_ranks[position])
            lexical_score = lexical_scores[position] if lexical_scores else 0.0
            ranked.append((score, lexical_score, position, hit))
        # With no lexical matches, reciprocal dense ranks preserve the exact base
        # order. Inverse dense/lexical ranks can produce equal RRF sums; prefer
        # the stronger lexical match in that case, then cosine and stable ID.
        ranked.sort(key=lambda item: (
            -item[0], -item[1], -item[3]["similarity"],
            str(item[3]["document"].get("doc_id", "")), item[2],
        ))
        return [{**hit, "retrieval_score": score} for score, _, _, hit in ranked[:top_k]]
