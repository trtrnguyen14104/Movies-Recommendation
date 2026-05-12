"""
Recommendations router – full implementation:

  GET  /recommendations/for-you           Personalized vector-based recommendations
  POST /recommendations/interact          Record user interaction (persistent in ChromaDB)
  GET  /recommendations/similar/{id}      Similar movies via vector similarity
  GET  /recommendations/history           User interaction history
  GET  /recommendations/stats             Vector store statistics
  GET  /recommendations/goi-y             Legacy genre-scoring endpoint (kept for compatibility)

Architecture:
  - Interactions stored in ChromaDB `interactions` collection
  - Movie embeddings stored in ChromaDB `movies` collection
  - Fallback to genre-scoring when ChromaDB is unavailable
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services import tmdb_service
from services.tmdb_service import image_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _enrich(movie: dict) -> dict:
    movie["poster_url"] = image_url(movie.get("poster_path"), "w500")
    movie["backdrop_url"] = image_url(movie.get("backdrop_path"), "w1280")
    return movie


def _get_chroma_interactions():
    try:
        from services.chromadb_service import get_interactions_collection
        return get_interactions_collection()
    except Exception as e:
        logger.warning(f"ChromaDB interactions unavailable: {e}")
        return None


def _get_chroma_movies():
    try:
        from services.chromadb_service import get_movies_collection
        return get_movies_collection()
    except Exception as e:
        logger.warning(f"ChromaDB movies unavailable: {e}")
        return None


ACTION_WEIGHTS = {"like": 3, "trailer": 2, "detail": 1}


# ─── POST /interact ───────────────────────────────────────────────────────────

class InteractionIn(BaseModel):
    session_id: str
    movie_id: int
    action: str                     # "like" | "trailer" | "detail"
    genre_ids: Optional[List[int]] = []
    title: Optional[str] = ""


@router.post("/interact")
async def record_interaction(body: InteractionIn):
    """
    Record a user interaction.
    Stores the movie embedding + metadata in ChromaDB for personalized recommendations.
    """
    if body.action not in ACTION_WEIGHTS:
        raise HTTPException(
            status_code=422,
            detail=f"action must be one of: {list(ACTION_WEIGHTS.keys())}",
        )

    timestamp = datetime.now(timezone.utc).isoformat()
    doc_id = f"{body.session_id}_{body.movie_id}_{body.action}_{timestamp}"

    metadata = {
        "session_id": body.session_id,
        "movie_id": str(body.movie_id),
        "action": body.action,
        "weight": str(ACTION_WEIGHTS[body.action]),
        "title": body.title or "",
        "genre_ids": ",".join(str(g) for g in body.genre_ids),
        "timestamp": timestamp,
    }

    # Try to get/generate movie embedding for vector-based recommendations
    collection = _get_chroma_interactions()
    if collection is not None:
        try:
            # Try to reuse existing movie embedding from movies collection
            movies_col = _get_chroma_movies()
            embedding = None
            if movies_col is not None:
                existing = movies_col.get(ids=[str(body.movie_id)], include=["embeddings"])
                if existing.get("embeddings") and existing["embeddings"][0]:
                    embedding = existing["embeddings"][0]

            # Generate embedding from movie data if not cached
            if embedding is None:
                try:
                    from services.movie_indexing_service import index_single_movie
                    # Index the movie using the unified pipeline which creates rich embeddings and stores in ChromaDB
                    success = await index_single_movie(body.movie_id)
                    if success and movies_col is not None:
                         existing = movies_col.get(ids=[str(body.movie_id)], include=["embeddings"])
                         if existing.get("embeddings") and existing["embeddings"][0]:
                            embedding = existing["embeddings"][0]
                except Exception as e:
                    logger.warning(f"Could not embed movie {body.movie_id}: {e}")

            if embedding:
                collection.upsert(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[f"{body.title} {body.action}"],
                    metadatas=[metadata],
                )
            else:
                # Store without embedding (metadata only via dummy vector)
                collection.upsert(
                    ids=[doc_id],
                    embeddings=[[0.0] * 768],
                    documents=[f"{body.title} {body.action}"],
                    metadatas=[metadata],
                )

            logger.info(f"Recorded interaction: {body.session_id} {body.action} movie {body.movie_id}")
        except Exception as e:
            logger.error(f"Failed to persist interaction in ChromaDB: {e}")

    return {
        "status": "recorded",
        "session_id": body.session_id,
        "movie_id": body.movie_id,
        "action": body.action,
        "timestamp": timestamp,
    }


# ─── GET /history ─────────────────────────────────────────────────────────────

@router.get("/history")
async def get_interaction_history(
    session_id: str = Query(..., description="User session identifier"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Retrieve the interaction history for a session from ChromaDB.
    """
    collection = _get_chroma_interactions()
    if collection is None:
        return {"session_id": session_id, "history": [], "total": 0, "source": "unavailable"}

    try:
        results = collection.get(
            where={"session_id": session_id},
            limit=limit,
            include=["metadatas", "documents"],
        )
        history = []
        for meta in results.get("metadatas", []):
            history.append({
                "movie_id": int(meta.get("movie_id", 0)),
                "action": meta.get("action", ""),
                "title": meta.get("title", ""),
                "timestamp": meta.get("timestamp", ""),
                "weight": int(meta.get("weight", 1)),
            })
        # Sort by timestamp descending
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return {"session_id": session_id, "history": history, "total": len(history), "source": "chromadb"}

    except Exception as e:
        logger.error(f"History retrieval failed: {e}")
        return {"session_id": session_id, "history": [], "total": 0, "source": "error", "detail": str(e)}


# ─── GET /for-you ─────────────────────────────────────────────────────────────

@router.get("/for-you")
async def personalized_recommendations(
    session_id: str = Query(..., description="User session identifier"),
    limit: int = Query(12, ge=1, le=20),
    exclude_ids: str = Query("", description="Comma-separated movie IDs to exclude"),
):
    """
    Personalized recommendations using vector embeddings from interaction history.
    Falls back to genre-scoring when ChromaDB is unavailable or history is empty.
    """
    exclude_set = {e.strip() for e in exclude_ids.split(",") if e.strip()}

    # ── Step 1: Load interaction history ──────────────────────────────────────
    collection = _get_chroma_interactions()
    movies_col = _get_chroma_movies()

    if collection is not None and movies_col is not None:
        try:
            history_result = collection.get(
                where={"session_id": session_id},
                include=["embeddings", "metadatas"],
            )
            embeddings = history_result.get("embeddings") or []
            metadatas = history_result.get("metadatas") or []

            if embeddings:
                import numpy as np

                # ── Step 2: Build weighted average preference vector ───────────
                weights = [
                    int(m.get("weight", 1)) for m in metadatas
                ]
                weighted_embs = [
                    [v * w for v in emb]
                    for emb, w in zip(embeddings, weights)
                    if emb and max(abs(v) for v in emb) > 0
                ]

                if weighted_embs:
                    pref_vector = np.mean(weighted_embs, axis=0).tolist()
                    interacted_ids = {m.get("movie_id", "") for m in metadatas}

                    # ── Step 3: Query ChromaDB for similar movies ──────────────
                    query_result = movies_col.query(
                        query_embeddings=[pref_vector],
                        n_results=min(limit + 20, 40),
                        include=["metadatas", "distances"],
                    )
                    candidate_ids = []
                    for mid, meta in zip(
                        query_result.get("ids", [[]])[0],
                        query_result.get("metadatas", [[]])[0],
                    ):
                        if mid not in interacted_ids and mid not in exclude_set:
                            candidate_ids.append(int(mid))

                    if candidate_ids:
                        # Fetch enriched movie data from TMDB
                        enriched = []
                        for mid in candidate_ids[:limit]:
                            try:
                                movie = await tmdb_service.get_movie_detail(mid)
                                enriched.append(_enrich(movie))
                            except Exception:
                                pass

                        if enriched:
                            return {
                                "results": enriched,
                                "total": len(enriched),
                                "method": "chromadb_vector",
                                "session_id": session_id,
                            }
        except Exception as e:
            logger.warning(f"Vector-based for-you failed: {e}, falling back to genre scoring")

    # ── Fallback: genre-based using history metadata ───────────────────────────
    genre_scores: dict = {}
    if collection is not None:
        try:
            history_result = collection.get(
                where={"session_id": session_id},
                include=["metadatas"],
            )
            for meta in history_result.get("metadatas", []):
                weight = int(meta.get("weight", 1))
                for gid in meta.get("genre_ids", "").split(","):
                    gid = gid.strip()
                    if gid:
                        genre_scores[gid] = genre_scores.get(gid, 0) + weight
        except Exception:
            pass

    if not genre_scores:
        # No history at all – return trending
        data = await tmdb_service.get_trending_movies("week")
        results = [
            _enrich(m) for m in data.get("results", [])
            if str(m.get("id")) not in exclude_set
        ][:limit]
        return {"results": results, "total": len(results), "method": "trending_fallback", "session_id": session_id}

    sorted_genres = sorted(genre_scores.items(), key=lambda x: -x[1])[:3]
    with_genres_str = ",".join(gid for gid, _ in sorted_genres)
    data = await tmdb_service.get_movies_by_genre_ids(with_genres_str, page=1)
    results = [
        _enrich(m) for m in data.get("results", [])
        if str(m.get("id")) not in exclude_set
    ][:limit]

    return {
        "results": results,
        "total": len(results),
        "method": "genre_scoring_fallback",
        "session_id": session_id,
        "top_genres": [{"genre_id": gid, "score": score} for gid, score in sorted_genres],
    }


# ─── GET /similar/{id} ────────────────────────────────────────────────────────

@router.get("/similar/{movie_id}")
async def similar_movies(
    movie_id: int,
    limit: int = Query(12, ge=1, le=20),
):
    """
    Find movies similar to the given one using vector embeddings in ChromaDB.
    Falls back to TMDB's own similar endpoint when ChromaDB is unavailable.
    """
    movies_col = _get_chroma_movies()

    if movies_col is not None:
        try:
            # Get or generate embedding for this movie
            existing = movies_col.get(ids=[str(movie_id)], include=["embeddings"])
            embedding = None
            if existing.get("embeddings") and existing["embeddings"][0]:
                embedding = existing["embeddings"][0]

            if embedding is None:
                from services.movie_indexing_service import index_single_movie
                # Index the movie using the unified pipeline which creates rich embeddings and stores in ChromaDB
                success = await index_single_movie(movie_id)
                if success:
                    existing = movies_col.get(ids=[str(movie_id)], include=["embeddings"])
                    if existing.get("embeddings") and existing["embeddings"][0]:
                        embedding = existing["embeddings"][0]

            if embedding and max(abs(v) for v in embedding) > 0:
                results = movies_col.query(
                    query_embeddings=[embedding],
                    n_results=limit + 5,
                    include=["metadatas", "distances"],
                )
                candidate_ids = [
                    int(mid) for mid in results.get("ids", [[]])[0]
                    if int(mid) != movie_id
                ][:limit]

                enriched = []
                for mid in candidate_ids:
                    try:
                        movie = await tmdb_service.get_movie_detail(mid)
                        enriched.append(_enrich(movie))
                    except Exception:
                        pass

                if enriched:
                    return {
                        "movie_id": movie_id,
                        "results": enriched,
                        "total": len(enriched),
                        "method": "chromadb_vector",
                    }
        except Exception as e:
            logger.warning(f"ChromaDB similar failed: {e}, falling back to TMDB")

    # Fallback: TMDB similar endpoint
    detail = await tmdb_service.get_movie_detail(movie_id)
    similar = detail.get("similar", {}).get("results", [])[:limit]
    return {
        "movie_id": movie_id,
        "results": [_enrich(m) for m in similar],
        "total": len(similar),
        "method": "tmdb_similar",
    }


# ─── GET /stats ───────────────────────────────────────────────────────────────

@router.get("/stats")
async def vector_store_stats():
    """
    Return statistics about the ChromaDB vector store.
    """
    stats = {
        "movies_indexed": 0,
        "reviews_indexed": 0,
        "interactions_logged": 0,
        "collections": [],
        "source": "chromadb",
    }
    try:
        from services.chromadb_service import get_client
        client = get_client()

        movies_col = _get_chroma_movies()
        reviews_col = None
        interactions_col = _get_chroma_interactions()

        try:
            from services.chromadb_service import get_reviews_collection
            reviews_col = get_reviews_collection()
        except Exception:
            pass

        if movies_col:
            stats["movies_indexed"] = movies_col.count()
            stats["collections"].append("movies")
        if reviews_col:
            stats["reviews_indexed"] = reviews_col.count()
            stats["collections"].append("reviews")
        if interactions_col:
            stats["interactions_logged"] = interactions_col.count()
            stats["collections"].append("interactions")

    except Exception as e:
        stats["source"] = "error"
        stats["detail"] = str(e)

    return stats


# ─── GET /goi-y (legacy, kept for compatibility) ─────────────────────────────

@router.get("/goi-y")
async def recommend_by_genres(
    genre_scores: str = Query(
        ...,
        description=(
            "Diem tung genre, dinh dang 'genre_id:diem' cach nhau bang dau phay. "
            "Vi du: '28:6,12:3,878:2,14:1'"
        ),
    ),
    exclude_ids: str = Query("", description="Cac movie_id can bo qua"),
    limit: int = Query(12, ge=1, le=20),
):
    """
    Legacy genre-scoring recommendations.
    Frontend tính điểm rồi gửi lên, backend dùng điểm để chọn genre và tìm phim.
    """
    genre_weight_map = {}
    for item in genre_scores.split(","):
        item = item.strip()
        if ":" not in item:
            continue
        parts = item.split(":")
        if len(parts) != 2:
            continue
        genre_id, score_str = parts[0].strip(), parts[1].strip()
        if genre_id and score_str.lstrip("-").isdigit():
            score = int(score_str)
            if score > 0:
                genre_weight_map[genre_id] = score

    if not genre_weight_map:
        return {"results": [], "total": 0, "top_genres": []}

    sorted_genres = sorted(genre_weight_map.items(), key=lambda x: -x[1])
    top_3 = sorted_genres[:3]
    top_genre_ids = [gid for gid, _ in top_3]
    with_genres_str = ",".join(top_genre_ids)

    data = await tmdb_service.get_movies_by_genre_ids(with_genres_str, page=1)
    raw_results = data.get("results", [])

    exclude_set = {e.strip() for e in exclude_ids.split(",") if e.strip()}
    filtered = [m for m in raw_results if str(m["id"]) not in exclude_set]

    scored_movies = []
    for movie in filtered:
        movie_genre_ids = [str(gid) for gid in movie.get("genre_ids", [])]
        match_score = sum(genre_weight_map.get(gid, 0) for gid in movie_genre_ids)
        scored_movies.append((match_score, movie))
    scored_movies.sort(key=lambda x: -x[0])

    enriched = []
    for match_score, movie in scored_movies[:limit]:
        movie["poster_url"] = image_url(movie.get("poster_path"), "w500")
        movie["backdrop_url"] = image_url(movie.get("backdrop_path"), "w1280")
        movie["match_score"] = match_score
        enriched.append(movie)

    return {
        "results": enriched,
        "total": len(enriched),
        "top_genres": [{"genre_id": gid, "score": score} for gid, score in top_3],
    }
