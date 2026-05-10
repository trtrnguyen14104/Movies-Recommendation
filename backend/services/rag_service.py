"""
RAG (Retrieval-Augmented Generation) service.
Embeds reviews using TF-IDF vectors and retrieves the most relevant
chunks when building the context for the Gemini AI summary.
"""
import re
import math
from typing import List, Dict, Tuple
from collections import defaultdict


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) > 2]


def _compute_tfidf(docs: List[List[str]]) -> List[Dict[str, float]]:
    N = len(docs)
    df: Dict[str, int] = defaultdict(int)
    for doc in docs:
        for term in set(doc):
            df[term] += 1

    vectors = []
    for doc in docs:
        tf: Dict[str, int] = defaultdict(int)
        for term in doc:
            tf[term] += 1
        vec: Dict[str, float] = {}
        for term, count in tf.items():
            idf = math.log((N + 1) / (df[term] + 1)) + 1
            vec[term] = (count / len(doc)) * idf
        vectors.append(vec)
    return vectors


def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    common = set(a.keys()) & set(b.keys())
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class ReviewRAG:
    """
    Lightweight RAG system using TF-IDF.
    No external embedding model required.
    """

    def __init__(self):
        self._store: Dict[int, dict] = {}  # movie_id -> {reviews, tokens, vectors}

    def index_reviews(self, movie_id: int, reviews: List[Dict]) -> None:
        """Index reviews for a movie."""
        texts = [r.get("content", "") for r in reviews if r.get("content", "").strip()]
        if not texts:
            return
        tokenized = [_tokenize(t) for t in texts]
        vectors = _compute_tfidf(tokenized)
        self._store[movie_id] = {
            "reviews": reviews[:len(texts)],
            "texts": texts,
            "tokens": tokenized,
            "vectors": vectors,
        }

    def retrieve(self, movie_id: int, query: str, top_k: int = 10) -> List[str]:
        """Retrieve the top-k most relevant review snippets."""
        if movie_id not in self._store:
            return []
        store = self._store[movie_id]
        q_tokens = _tokenize(query)
        if not q_tokens:
            # fallback: return first top_k
            return store["texts"][:top_k]
        q_vec = _compute_tfidf([q_tokens])[0]
        scored: List[Tuple[float, str]] = []
        for vec, text in zip(store["vectors"], store["texts"]):
            score = _cosine_similarity(q_vec, vec)
            scored.append((score, text))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored[:top_k]]

    def get_all_texts(self, movie_id: int) -> List[str]:
        if movie_id not in self._store:
            return []
        return self._store[movie_id]["texts"]

    def is_indexed(self, movie_id: int) -> bool:
        return movie_id in self._store

    def count(self, movie_id: int) -> int:
        if movie_id not in self._store:
            return 0
        return len(self._store[movie_id]["texts"])


# Singleton instance
rag_store = ReviewRAG()
