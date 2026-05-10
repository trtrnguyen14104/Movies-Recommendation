"""
ChromaDB vector service for personalized movie recommendations.
Stores movie embeddings and user preference vectors using TF-IDF.
Persists to disk via ChromaDB's local storage.
"""

import math
import re
import json
import os
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

# Fallback in-memory store if ChromaDB not available
_fallback_store: Dict[str, dict] = {}
_fallback_user_prefs: Dict[str, List[float]] = {}
_fallback_movie_vectors: Dict[str, Tuple[List[float], dict]] = {}

# ChromaDB persistence path
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

_chroma_client = None
_movie_collection = None
_user_collection = None


def _get_chroma():
    global _chroma_client, _movie_collection, _user_collection
    if _chroma_client is None and CHROMA_AVAILABLE:
        try:
            os.makedirs(CHROMA_PATH, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
            _movie_collection = _chroma_client.get_or_create_collection(
                name="movies",
                metadata={"hnsw:space": "cosine"},
            )
            _user_collection = _chroma_client.get_or_create_collection(
                name="user_preferences",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            print(f"[ChromaDB] Failed to initialize: {e}")
            _chroma_client = None
    return _chroma_client, _movie_collection, _user_collection


# ─── Text Processing ──────────────────────────────────────────────────────────

GENRE_MAP = {
    28: "action", 12: "adventure", 16: "animation", 35: "comedy",
    80: "crime", 99: "documentary", 18: "drama", 10751: "family",
    14: "fantasy", 36: "history", 27: "horror", 10402: "music",
    9648: "mystery", 10749: "romance", 878: "sci-fi", 10770: "tv-movie",
    53: "thriller", 10752: "war", 37: "western",
}


def _movie_to_text(movie: dict) -> str:
    """Convert movie metadata to a text document for embedding."""
    parts = []
    title = movie.get("title", "")
    if title:
        parts.append(f"title: {title} {title}")  # weight title higher

    overview = movie.get("overview", "")
    if overview:
        parts.append(f"overview: {overview}")

    genre_ids = movie.get("genre_ids", [])
    genres = movie.get("genres", [])
    genre_names = []
    for g in genres:
        genre_names.append(g.get("name", "").lower())
    for gid in genre_ids:
        if gid in GENRE_MAP:
            genre_names.append(GENRE_MAP[gid])

    if genre_names:
        parts.append(f"genre: {' '.join(genre_names)} " * 3)  # weight genres

    rating = movie.get("vote_average", 0)
    if rating >= 7.5:
        parts.append("quality: highly rated acclaimed")
    elif rating >= 6.0:
        parts.append("quality: well received")

    year = (movie.get("release_date", "") or "")[:4]
    if year:
        decade = year[:3] + "0s"
        parts.append(f"era: {year} {decade}")

    return " ".join(parts)


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if len(t) > 2]
    return tokens


def _tfidf_vector(doc_tokens: List[str], vocab: List[str]) -> List[float]:
    """Compute a TF-IDF vector for a document against a fixed vocabulary."""
    tf: Dict[str, int] = defaultdict(int)
    for t in doc_tokens:
        tf[t] += 1
    total = max(len(doc_tokens), 1)
    vec = []
    for term in vocab:
        count = tf.get(term, 0)
        vec.append(count / total)
    return vec


def _build_vocab(docs: List[List[str]], max_terms: int = 300) -> List[str]:
    """Build vocabulary from all documents, returning top frequent terms."""
    freq: Dict[str, int] = defaultdict(int)
    for doc in docs:
        for t in set(doc):
            freq[t] += 1
    # Filter stopwords and keep most frequent
    stopwords = {"the", "and", "for", "that", "this", "with", "from", "has",
                 "are", "was", "its", "but", "not", "have", "been", "they",
                 "his", "her", "him", "she", "who", "what", "when", "where"}
    vocab = [t for t, _ in sorted(freq.items(), key=lambda x: -x[1])
             if t not in stopwords]
    return vocab[:max_terms]


def _cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ─── In-memory fallback ───────────────────────────────────────────────────────

class FallbackVectorStore:
    def __init__(self):
        self._movies: Dict[str, dict] = {}       # id -> {meta, text, vector}
        self._vocab: List[str] = []
        self._dirty = True

    def _rebuild_vocab(self):
        if not self._dirty:
            return
        docs = [_tokenize(m["text"]) for m in self._movies.values()]
        self._vocab = _build_vocab(docs)
        # Recompute all vectors
        for mid, m in self._movies.items():
            tokens = _tokenize(m["text"])
            m["vector"] = _tfidf_vector(tokens, self._vocab)
        self._dirty = False

    def upsert_movie(self, movie_id: str, movie: dict):
        text = _movie_to_text(movie)
        self._movies[movie_id] = {
            "text": text,
            "meta": {
                "title": movie.get("title", ""),
                "vote_average": float(movie.get("vote_average", 0)),
                "genre_ids": json.dumps(movie.get("genre_ids", [])),
                "release_date": (movie.get("release_date", "") or "")[:10],
                "poster_url": movie.get("poster_url", "") or "",
                "backdrop_url": movie.get("backdrop_url", "") or "",
            },
            "vector": [],
        }
        self._dirty = True

    def get_recommendations(
        self, user_vector: List[float], exclude_ids: List[str], top_k: int = 10
    ) -> List[dict]:
        self._rebuild_vocab()
        results = []
        for mid, m in self._movies.items():
            if mid in exclude_ids:
                continue
            if not m["vector"]:
                continue
            score = _cosine_sim(user_vector, m["vector"])
            results.append((score, mid, m["meta"]))
        results.sort(key=lambda x: -x[0])
        return [
            {"id": int(mid), "score": score, **meta}
            for score, mid, meta in results[:top_k]
        ]

    def build_user_vector(self, liked_ids: List[str]) -> List[float]:
        self._rebuild_vocab()
        if not liked_ids or not self._vocab:
            return [0.0] * len(self._vocab)
        vecs = [
            self._movies[mid]["vector"]
            for mid in liked_ids
            if mid in self._movies and self._movies[mid]["vector"]
        ]
        if not vecs:
            return [0.0] * len(self._vocab)
        combined = [sum(v[i] for v in vecs) / len(vecs) for i in range(len(self._vocab))]
        return combined

    def movie_count(self) -> int:
        return len(self._movies)


_fallback = FallbackVectorStore()


# ─── Public API ───────────────────────────────────────────────────────────────

def upsert_movie(movie_id: int, movie: dict) -> bool:
    """Store/update a movie's vector embedding."""
    mid = str(movie_id)
    text = _movie_to_text(movie)
    meta = {
        "title": movie.get("title", ""),
        "vote_average": float(movie.get("vote_average", 0)),
        "genre_ids": json.dumps(movie.get("genre_ids", [])),
        "release_date": (movie.get("release_date", "") or "")[:10],
        "poster_url": movie.get("poster_url", "") or "",
        "backdrop_url": movie.get("backdrop_url", "") or "",
        "overview": (movie.get("overview", "") or "")[:500],
    }

    # Always update fallback
    _fallback.upsert_movie(mid, movie)

    client, movies_col, _ = _get_chroma()
    if movies_col:
        try:
            # ChromaDB uses its own embedding; we pass text documents
            movies_col.upsert(
                ids=[mid],
                documents=[text],
                metadatas=[meta],
            )
            return True
        except Exception as e:
            print(f"[ChromaDB] upsert_movie error: {e}")

    return True  # fallback always works


def record_interaction(user_id: str, movie: dict, action: str = "view") -> None:
    """Record that a user interacted with a movie (view, like, etc.)."""
    # Weight: like=3, view=1, dislike=-1
    weight_map = {"like": 3, "view": 1, "dislike": -1, "watchlist": 2}
    weight = weight_map.get(action, 1)

    # Update fallback user prefs
    movie_id = str(movie.get("id", ""))
    if not movie_id:
        return

    # Ensure movie is in store
    upsert_movie(int(movie_id), movie)

    # Store interaction in user collection
    client, _, users_col = _get_chroma()
    if users_col:
        try:
            interaction_id = f"{user_id}_{movie_id}_{action}"
            text = _movie_to_text(movie) + f" weight:{weight}"
            users_col.upsert(
                ids=[interaction_id],
                documents=[text],
                metadatas=[{
                    "user_id": user_id,
                    "movie_id": movie_id,
                    "action": action,
                    "weight": weight,
                    "title": movie.get("title", ""),
                }],
            )
        except Exception as e:
            print(f"[ChromaDB] record_interaction error: {e}")


def get_user_interactions(user_id: str) -> List[dict]:
    """Get all interactions for a user."""
    client, _, users_col = _get_chroma()
    if users_col:
        try:
            results = users_col.get(
                where={"user_id": user_id},
                include=["metadatas", "documents"],
            )
            interactions = []
            for meta in results.get("metadatas", []):
                interactions.append(meta)
            return interactions
        except Exception as e:
            print(f"[ChromaDB] get_user_interactions error: {e}")
    return []


def get_recommendations_for_user(
    user_id: str,
    candidate_movies: List[dict],
    top_k: int = 10,
) -> List[dict]:
    """
    Get personalized movie recommendations for a user.
    Uses their viewing history to find similar movies from candidates.
    """
    # Get user interactions
    interactions = get_user_interactions(user_id)

    if not interactions:
        # Cold start: return top-rated from candidates
        return sorted(
            candidate_movies, key=lambda m: m.get("vote_average", 0), reverse=True
        )[:top_k]

    # Build genre and keyword preference profile
    liked_genre_ids: Dict[int, float] = defaultdict(float)
    disliked_genre_ids: Dict[int, float] = defaultdict(float)
    liked_movie_ids = set()
    disliked_movie_ids = set()

    for interaction in interactions:
        mid = interaction.get("movie_id", "")
        action = interaction.get("action", "view")
        weight = float(interaction.get("weight", 1))

        if weight > 0:
            liked_movie_ids.add(mid)
        else:
            disliked_movie_ids.add(mid)

    # Score candidates based on genre overlap with liked movies
    # Use fallback vector similarity
    for movie in candidate_movies:
        upsert_movie(movie["id"], movie)

    liked_list = list(liked_movie_ids)
    user_vec = _fallback.build_user_vector(liked_list)
    exclude = liked_movie_ids | disliked_movie_ids

    if any(v != 0 for v in user_vec):
        recs = _fallback.get_recommendations(user_vec, list(exclude), top_k=top_k * 2)
        # Map back to full movie objects from candidates
        candidate_map = {str(m["id"]): m for m in candidate_movies}
        result = []
        seen = set()
        for r in recs:
            mid = str(r["id"])
            if mid in candidate_map and mid not in seen:
                result.append(candidate_map[mid])
                seen.add(mid)
            if len(result) >= top_k:
                break

        # Fill remaining with high-rated candidates
        if len(result) < top_k:
            remaining = [
                m for m in sorted(candidate_movies, key=lambda x: x.get("vote_average", 0), reverse=True)
                if str(m["id"]) not in seen and str(m["id"]) not in exclude
            ]
            result.extend(remaining[: top_k - len(result)])

        return result

    # Fallback: top rated
    return sorted(
        [m for m in candidate_movies if str(m["id"]) not in exclude],
        key=lambda m: m.get("vote_average", 0), reverse=True
    )[:top_k]


def get_similar_to_movie(movie_id: int, candidate_movies: List[dict], top_k: int = 8) -> List[dict]:
    """Find movies similar to a given movie from the candidates."""
    mid = str(movie_id)
    if mid not in _fallback._movies:
        return candidate_movies[:top_k]

    _fallback._rebuild_vocab()
    source = _fallback._movies.get(mid)
    if not source or not source.get("vector"):
        return candidate_movies[:top_k]

    scored = []
    for m in candidate_movies:
        cmid = str(m["id"])
        if cmid == mid:
            continue
        _fallback.upsert_movie(cmid, m)
        _fallback._rebuild_vocab()
        cvec = _fallback._movies.get(cmid, {}).get("vector", [])
        if cvec:
            score = _cosine_sim(source["vector"], cvec)
            scored.append((score, m))

    scored.sort(key=lambda x: -x[0])
    return [m for _, m in scored[:top_k]]


def get_store_stats() -> dict:
    client, movies_col, users_col = _get_chroma()
    movie_count = _fallback.movie_count()
    user_count = 0
    chroma_movies = 0

    if movies_col:
        try:
            chroma_movies = movies_col.count()
        except Exception:
            pass
    if users_col:
        try:
            user_count = users_col.count()
        except Exception:
            pass

    return {
        "chromadb_available": CHROMA_AVAILABLE and client is not None,
        "movies_in_memory": movie_count,
        "movies_in_chromadb": chroma_movies,
        "interactions_in_chromadb": user_count,
    }
