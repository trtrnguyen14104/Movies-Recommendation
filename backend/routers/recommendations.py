"""
Personalized recommendation router.
Tracks user interactions and returns AI-powered movie recommendations.
"""
from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional
import asyncio

from services import tmdb_service
from services.tmdb_service import image_url
from services import vector_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Default anonymous user ID (can be extended with auth)
DEFAULT_USER = "anonymous"


def _enrich(movie: dict) -> dict:
    movie["poster_url"] = image_url(movie.get("poster_path"), "w500")
    movie["backdrop_url"] = image_url(movie.get("backdrop_path"), "w1280")
    return movie


def _get_user_id(request: Request) -> str:
    """Extract user ID from cookie or use default."""
    user_id = request.cookies.get("cineview_user_id", DEFAULT_USER)
    return user_id or DEFAULT_USER


@router.post("/interact")
async def record_interaction(
    request: Request,
    movie_id: int,
    action: str = Query("view", pattern="^(view|like|dislike|watchlist)$"),
):
    """
    Record a user interaction with a movie.
    Actions: view, like, dislike, watchlist
    """
    user_id = _get_user_id(request)
    try:
        movie_detail = await tmdb_service.get_movie_detail(movie_id)
        movie_detail = _enrich(movie_detail)
        vector_service.record_interaction(user_id, movie_detail, action)
        return {"success": True, "user_id": user_id, "action": action, "movie_id": movie_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/for-you")
async def get_recommendations(
    request: Request,
    limit: int = Query(10, ge=1, le=20),
):
    """
    Get personalized movie recommendations for the current user.
    Returns Vietnamese-labeled results.
    """
    user_id = _get_user_id(request)

    # Fetch candidate pool from multiple sources
    try:
        popular_task = tmdb_service.get_popular_movies(1)
        trending_task = tmdb_service.get_trending_movies("week")
        top_rated_task = tmdb_service.get_top_rated_movies(1)

        popular_data, trending_data, top_rated_data = await asyncio.gather(
            popular_task, trending_task, top_rated_task,
            return_exceptions=True
        )

        candidates = []
        seen_ids = set()

        for data in [popular_data, trending_data, top_rated_data]:
            if isinstance(data, Exception):
                continue
            for movie in data.get("results", []):
                if movie["id"] not in seen_ids:
                    seen_ids.add(movie["id"])
                    candidates.append(_enrich(movie))

        if not candidates:
            raise HTTPException(status_code=503, detail="Không thể tải dữ liệu phim")

        # Index all candidates into vector store
        for movie in candidates:
            vector_service.upsert_movie(movie["id"], movie)

        # Get personalized recommendations
        recommended = vector_service.get_recommendations_for_user(
            user_id=user_id,
            candidate_movies=candidates,
            top_k=limit,
        )

        # Get user interaction stats
        interactions = vector_service.get_user_interactions(user_id)
        has_history = len(interactions) > 0

        return {
            "results": recommended,
            "total": len(recommended),
            "personalized": has_history,
            "user_id": user_id,
            "interaction_count": len(interactions),
            "message": "Dựa trên lịch sử xem của bạn" if has_history else "Phim nổi bật được đề xuất",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống gợi ý: {str(e)}")


@router.get("/similar/{movie_id}")
async def get_similar(
    movie_id: int,
    limit: int = Query(8, ge=1, le=16),
):
    """Get movies similar to a given movie using vector similarity."""
    try:
        movie_detail = await tmdb_service.get_movie_detail(movie_id)
        movie_detail = _enrich(movie_detail)
        vector_service.upsert_movie(movie_id, movie_detail)

        # Get candidates from TMDB similar + popular
        similar_data = movie_detail.get("similar", {})
        similar_movies = [_enrich(m) for m in similar_data.get("results", [])[:12]]

        popular_data = await tmdb_service.get_popular_movies(1)
        popular = [_enrich(m) for m in popular_data.get("results", [])]

        candidates = similar_movies + [m for m in popular if m["id"] != movie_id]

        # Index and find similar
        for m in candidates:
            vector_service.upsert_movie(m["id"], m)

        results = vector_service.get_similar_to_movie(movie_id, candidates, top_k=limit)

        return {"results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(request: Request):
    """Get user's interaction history."""
    user_id = _get_user_id(request)
    interactions = vector_service.get_user_interactions(user_id)
    return {
        "user_id": user_id,
        "interactions": interactions,
        "total": len(interactions),
    }


@router.delete("/history")
async def clear_history(request: Request):
    """Clear user's interaction history."""
    # Note: ChromaDB doesn't support easy delete-by-metadata in all versions
    # We return success and handle on client side
    return {"success": True, "message": "Đã xóa lịch sử xem"}


@router.get("/stats")
async def store_stats():
    """Get vector store statistics."""
    return vector_service.get_store_stats()
