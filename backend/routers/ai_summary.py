from fastapi import APIRouter, HTTPException, BackgroundTasks
from services import tmdb_service
from services.rag_service import rag_store
from services.gemini_service import generate_ai_summary
from cachetools import TTLCache

router = APIRouter(prefix="/ai", tags=["ai"])

# Cache summaries for 30 minutes to avoid repeated Gemini calls
_summary_cache: TTLCache = TTLCache(maxsize=200, ttl=1800)


async def _build_rag_index(movie_id: int):
    """Fetch all reviews and index them into the RAG store."""
    if rag_store.is_indexed(movie_id):
        return
    reviews = await tmdb_service.get_all_reviews(movie_id, max_pages=5)
    if reviews:
        rag_store.index_reviews(movie_id, reviews)


@router.get("/summary/{movie_id}")
async def get_ai_summary(movie_id: int):
    """
    Pipeline:
    1. Fetch reviews from TMDB (up to 5 pages)
    2. Index into RAG store (TF-IDF vectors)
    3. Retrieve most relevant chunks via semantic search
    4. Send to Gemini for structured AI analysis
    5. Return AIReviewSummary
    """
    if movie_id in _summary_cache:
        return _summary_cache[movie_id]

    # Step 1 & 2: Fetch and index
    await _build_rag_index(movie_id)

    total = rag_store.count(movie_id)
    if total == 0:
        raise HTTPException(
            status_code=404,
            detail="No reviews found for this movie. Cannot generate AI summary."
        )

    # Step 3: Retrieve relevant reviews
    retrieved = rag_store.retrieve(
        movie_id,
        query="overall quality plot acting cinematography worth watching",
        top_k=15,
    )

    # Get movie title
    try:
        detail = await tmdb_service.get_movie_detail(movie_id)
        title = detail.get("title", "this movie")
    except Exception:
        title = "this movie"

    # Step 4: Generate AI summary
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


@router.post("/reindex/{movie_id}")
async def reindex_movie(movie_id: int, background_tasks: BackgroundTasks):
    """Force re-index reviews for a movie (clears cache)."""
    _summary_cache.pop(movie_id, None)
    # Remove from rag store to force re-fetch
    if movie_id in rag_store._store:
        del rag_store._store[movie_id]
    background_tasks.add_task(_build_rag_index, movie_id)
    return {"message": f"Re-indexing started for movie {movie_id}"}


@router.get("/reviews/{movie_id}")
async def get_reviews(movie_id: int, page: int = 1):
    """Get raw reviews with pagination."""
    data = await tmdb_service.get_movie_reviews(movie_id, page)
    return data
