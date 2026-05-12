"""
Indexing Router
===============
REST endpoints to trigger and monitor the movie indexing pipeline.

  POST /indexing/start                   – trigger full pipeline (background)
  GET  /indexing/status                  – current progress & ChromaDB stats
  POST /indexing/movie/{movie_id}        – index a single movie immediately
  DELETE /indexing/movie/{movie_id}      – remove a movie from the index
  POST /indexing/reindex                 – force re-index all (ignores cache)
"""

import logging
import asyncio
from fastapi import APIRouter, HTTPException, Query

from services.movie_indexing_service import (
    run_indexing_pipeline,
    index_single_movie,
    get_progress,
    ensure_minimum_index,
)
from services.chromadb_service import get_movies_collection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/indexing", tags=["indexing"])


# ── POST /start ───────────────────────────────────────────────────────────────

@router.post("/start")
async def start_indexing(
    pages_per_source: int = Query(3, ge=1, le=10, description="TMDB pages per source (20 movies each)"),
    force: bool = Query(False, description="Re-index movies that are already indexed"),
):
    """
    Trigger the full movie indexing pipeline as a background task.
    Returns immediately; poll /indexing/status to track progress.
    """
    progress = get_progress()
    if progress.status == "running":
        return {
            "message": "Indexing already in progress",
            "progress": _serialize_progress(progress),
        }

    asyncio.create_task(run_indexing_pipeline(pages_per_source=pages_per_source, force=force))

    return {
        "message": "Indexing pipeline started in background",
        "pages_per_source": pages_per_source,
        "estimated_movies": pages_per_source * 20 * 5,
        "tip": "Poll GET /indexing/status to track progress",
    }


# ── GET /status ───────────────────────────────────────────────────────────────

@router.get("/status")
async def indexing_status():
    """
    Returns current pipeline progress + live ChromaDB collection counts.
    """
    progress = get_progress()

    # Live ChromaDB counts
    chroma_stats = {"movies": 0, "reviews": 0, "interactions": 0}
    try:
        from services.chromadb_service import (
            get_movies_collection,
            get_reviews_collection,
            get_interactions_collection,
        )
        chroma_stats["movies"] = get_movies_collection().count()
        chroma_stats["reviews"] = get_reviews_collection().count()
        chroma_stats["interactions"] = get_interactions_collection().count()
    except Exception as e:
        chroma_stats["error"] = str(e)

    return {
        "pipeline": _serialize_progress(progress),
        "chromadb": chroma_stats,
        "semantic_search_ready": chroma_stats["movies"] > 0,
    }


# ── POST /movie/{movie_id} ────────────────────────────────────────────────────

@router.post("/movie/{movie_id}")
async def index_movie(
    movie_id: int,
    force: bool = Query(False, description="Re-index even if already indexed"),
):
    """
    Index a single movie immediately (synchronous).
    Useful for indexing a movie the moment a user views its detail page.
    """
    indexed = await index_single_movie(movie_id, force=force)

    try:
        col = get_movies_collection()
        doc = col.get(ids=[str(movie_id)], include=["metadatas"])
        meta = (doc.get("metadatas") or [None])[0]
    except Exception:
        meta = None

    return {
        "movie_id": movie_id,
        "action": "indexed" if indexed else "skipped",
        "metadata": meta,
    }


# ── DELETE /movie/{movie_id} ──────────────────────────────────────────────────

@router.delete("/movie/{movie_id}")
async def remove_movie(movie_id: int):
    """Remove a movie from the ChromaDB movies index."""
    try:
        col = get_movies_collection()
        col.delete(ids=[str(movie_id)])
        return {"movie_id": movie_id, "action": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /reindex ─────────────────────────────────────────────────────────────

@router.post("/reindex")
async def reindex_all(
    pages_per_source: int = Query(3, ge=1, le=10),
):
    """
    Force full re-index of all movies (ignores already-indexed cache).
    WARNING: This will re-generate embeddings for all movies and may be slow.
    """
    progress = get_progress()
    if progress.status == "running":
        raise HTTPException(status_code=409, detail="Indexing already in progress")

    asyncio.create_task(
        run_indexing_pipeline(pages_per_source=pages_per_source, force=True)
    )

    return {
        "message": "Full re-indexing started",
        "pages_per_source": pages_per_source,
        "tip": "Poll GET /indexing/status to track progress",
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_progress(p) -> dict:
    return {
        "status": p.status,
        "started_at": p.started_at,
        "finished_at": p.finished_at,
        "total_fetched": p.total_fetched,
        "total_indexed": p.total_indexed,
        "total_skipped": p.total_skipped,
        "total_failed": p.total_failed,
        "current_source": p.current_source,
        "sources_completed": p.sources_completed,
        "error": p.error,
    }
