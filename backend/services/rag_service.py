"""
RAG service – hybrid approach:
  • ChromaDB Cloud for persistent review vector storage
  • TF-IDF fallback when ChromaDB is unavailable or for quick in-memory queries

Review embeddings use Gemini text-embedding-004.
"""
import re
import math
import logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


# ─── TF-IDF utilities (fallback / lightweight) ────────────────────────────────

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


# ─── ChromaDB-backed RAG ──────────────────────────────────────────────────────

class ReviewRAG:
    """
    Hybrid RAG system:
      1. Index reviews into ChromaDB with Gemini embeddings (persistent)
      2. Fall back to TF-IDF in-memory when ChromaDB is unavailable
    """

    def __init__(self):
        # In-memory TF-IDF fallback store: movie_id → {reviews, tokens, vectors}
        self._store: Dict[int, dict] = {}

    # ── ChromaDB helpers ──────────────────────────────────────────────────────

    def _get_chroma_collection(self):
        try:
            from services.chromadb_service import get_reviews_collection
            return get_reviews_collection()
        except Exception as e:
            logger.warning(f"ChromaDB reviews collection unavailable: {e}")
            return None

    def _chroma_doc_id(self, movie_id: int, review_id: str) -> str:
        return f"{movie_id}_{review_id}"

    # ── Index reviews ─────────────────────────────────────────────────────────

    def index_reviews(self, movie_id: int, reviews: List[Dict]) -> None:
        """
        Index reviews for a movie.
        Primary: embed & upsert into ChromaDB.
        Fallback: TF-IDF in-memory.
        """
        texts = [r.get("content", "") for r in reviews if r.get("content", "").strip()]
        valid_reviews = [r for r in reviews if r.get("content", "").strip()]
        if not texts:
            return

        # Always build TF-IDF fallback
        tokenized = [_tokenize(t) for t in texts]
        vectors = _compute_tfidf(tokenized)
        self._store[movie_id] = {
            "reviews": valid_reviews,
            "texts": texts,
            "tokens": tokenized,
            "vectors": vectors,
        }

        # Try ChromaDB with Gemini embeddings
        collection = self._get_chroma_collection()
        if collection is None:
            return

        try:
            from services.embedding_service import embed_text
            ids, embeddings, documents, metadatas = [], [], [], []
            for review in valid_reviews[:50]:  # cap at 50 per movie
                rid = str(review.get("id", ""))
                content = review.get("content", "")[:1000]
                embedding = embed_text(content, task_type="retrieval_document")
                if embedding is None:
                    continue
                ids.append(self._chroma_doc_id(movie_id, rid))
                embeddings.append(embedding)
                documents.append(content)
                metadatas.append({
                    "movie_id": str(movie_id),
                    "review_id": rid,
                    "author": review.get("author", ""),
                })

            if ids:
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
                logger.info(f"Indexed {len(ids)} reviews for movie {movie_id} into ChromaDB.")
        except Exception as e:
            logger.warning(f"ChromaDB review indexing failed for movie {movie_id}: {e}")

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def retrieve(self, movie_id: int, query: str, top_k: int = 10) -> List[str]:
        """
        Retrieve the top-k most relevant review snippets.
        Primary: ChromaDB vector search.
        Fallback: TF-IDF cosine similarity.
        """
        # Try ChromaDB first
        collection = self._get_chroma_collection()
        if collection is not None:
            try:
                from services.embedding_service import embed_query
                q_embedding = embed_query(query)
                if q_embedding is not None:
                    results = collection.query(
                        query_embeddings=[q_embedding],
                        n_results=min(top_k, 10),
                        where={"movie_id": str(movie_id)},
                    )
                    docs = results.get("documents", [[]])[0]
                    if docs:
                        return docs
            except Exception as e:
                logger.warning(f"ChromaDB retrieve failed: {e}, using TF-IDF fallback")

        # TF-IDF fallback
        if movie_id not in self._store:
            return []
        store = self._store[movie_id]
        q_tokens = _tokenize(query)
        if not q_tokens:
            return store["texts"][:top_k]
        q_vec = _compute_tfidf([q_tokens])[0]
        scored: List[Tuple[float, str]] = [
            (_cosine_similarity(q_vec, vec), text)
            for vec, text in zip(store["vectors"], store["texts"])
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored[:top_k]]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_all_texts(self, movie_id: int) -> List[str]:
        if movie_id not in self._store:
            return []
        return self._store[movie_id]["texts"]

    def is_indexed(self, movie_id: int) -> bool:
        # Check in-memory first (fast)
        if movie_id in self._store:
            return True
        # Check ChromaDB
        collection = self._get_chroma_collection()
        if collection is not None:
            try:
                result = collection.get(
                    where={"movie_id": str(movie_id)},
                    limit=1,
                )
                return len(result.get("ids", [])) > 0
            except Exception:
                pass
        return False

    def count(self, movie_id: int) -> int:
        if movie_id in self._store:
            return len(self._store[movie_id]["texts"])
        return 0


# Singleton instance
rag_store = ReviewRAG()
