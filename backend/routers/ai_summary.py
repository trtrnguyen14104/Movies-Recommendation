"""
AI endpoints:
  GET  /ai/summary/{movie_id}          – Enhanced structured summary
  GET  /ai/sentiment/{movie_id}        – Per-review sentiment analysis
  GET  /ai/fake-detection/{movie_id}   – Fake/spam/bot/toxic review detection
  GET  /ai/reviews/{movie_id}          – Raw reviews with pagination
  POST /ai/reindex/{movie_id}          – Force re-index
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from services import tmdb_service
from services.rag_service import rag_store
from services.gemini_service import (
    generate_ai_summary,
    analyze_review_sentiments,
    detect_fake_reviews,
)
from cachetools import TTLCache

router = APIRouter(prefix="/ai", tags=["ai"])

_summary_cache: TTLCache = TTLCache(maxsize=200, ttl=1800)
_sentiment_cache: TTLCache = TTLCache(maxsize=200, ttl=1800)
_fake_cache: TTLCache = TTLCache(maxsize=200, ttl=3600)


async def _build_rag_index(movie_id: int):
    """Fetch all reviews and index them into the RAG store."""
    if rag_store.is_indexed(movie_id):
        return
    reviews = await tmdb_service.get_all_reviews(movie_id, max_pages=5)
    if reviews:
        rag_store.index_reviews(movie_id, reviews)


# ─── Enhanced AI Summary ──────────────────────────────────────────────────────

@router.get("/summary/{movie_id}")
async def get_ai_summary(movie_id: int):
    """
    Pipeline:
    1. Fetch reviews from TMDB (up to 5 pages)
    2. Index into RAG store (ChromaDB / TF-IDF)
    3. Retrieve most relevant chunks via semantic search
    4. Send to Gemini for structured AI analysis
    5. Return enhanced AIReviewSummary with acting/music/screenplay/vfx breakdown
    """
    if movie_id in _summary_cache:
        return _summary_cache[movie_id]

    await _build_rag_index(movie_id)

    total = rag_store.count(movie_id)
    if total == 0:
        raise HTTPException(
            status_code=404,
            detail="No reviews found for this movie. Cannot generate AI summary.",
        )

    retrieved = rag_store.retrieve(
        movie_id,
        query="overall quality plot acting music cinematography worth watching",
        top_k=15,
    )

    try:
        detail = await tmdb_service.get_movie_detail(movie_id)
        title = detail.get("title", "this movie")
    except Exception:
        title = "this movie"

    summary = await generate_ai_summary(
        movie_id=movie_id,
        title=title,
        retrieved_reviews=retrieved,
        all_review_count=total,
    )
    if not summary:
        raise HTTPException(status_code=500, detail="Failed to generate AI summary.")

    result = summary.model_dump()
    _summary_cache[movie_id] = result
    return result


# ─── Per-Review Sentiment Analysis ───────────────────────────────────────────

@router.get("/sentiment/{movie_id}")
async def get_review_sentiment(
    movie_id: int,
    page: int = Query(1, ge=1),
):
    """
    Analyze sentiment (positive / negative / neutral) for each review individually.
    Also returns an aggregate summary.
    """
    cache_key = f"{movie_id}_{page}"
    if cache_key in _sentiment_cache:
        return _sentiment_cache[cache_key]

    data = await tmdb_service.get_movie_reviews(movie_id, page)
    reviews = data.get("results", [])

    if not reviews:
        raise HTTPException(
            status_code=404,
            detail="No reviews found for this movie on this page.",
        )

    result = await analyze_review_sentiments(movie_id=movie_id, reviews=reviews)
    out = result.model_dump()
    _sentiment_cache[cache_key] = out
    return out


# ─── Fake Review Detection ────────────────────────────────────────────────────

@router.get("/fake-detection/{movie_id}")
async def get_fake_review_detection(
    movie_id: int,
    page: int = Query(1, ge=1),
):
    """
    Detect spam, bot, and toxic reviews using Gemini NLP.
    Returns per-review labels and aggregate counts.
    """
    cache_key = f"{movie_id}_{page}"
    if cache_key in _fake_cache:
        return _fake_cache[cache_key]

    data = await tmdb_service.get_movie_reviews(movie_id, page)
    reviews = data.get("results", [])

    if not reviews:
        raise HTTPException(
            status_code=404,
            detail="No reviews found for this movie on this page.",
        )

    report = await detect_fake_reviews(movie_id=movie_id, reviews=reviews)
    out = report.model_dump()
    _fake_cache[cache_key] = out
    return out


# ─── Raw reviews ──────────────────────────────────────────────────────────────

@router.get("/reviews/{movie_id}")
async def get_reviews(movie_id: int, page: int = 1):
    """Get raw reviews with pagination."""
    return await tmdb_service.get_movie_reviews(movie_id, page)


# ─── Re-index ─────────────────────────────────────────────────────────────────

@router.post("/reindex/{movie_id}")
async def reindex_movie(movie_id: int, background_tasks: BackgroundTasks):
    """Force re-index reviews for a movie (clears all caches)."""
    _summary_cache.pop(movie_id, None)
    _sentiment_cache.pop(movie_id, None)
    _fake_cache.pop(movie_id, None)
    if movie_id in rag_store._store:
        del rag_store._store[movie_id]
    background_tasks.add_task(_build_rag_index, movie_id)
    return {"message": f"Re-indexing started for movie {movie_id}"}
