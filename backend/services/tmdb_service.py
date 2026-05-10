import httpx
from typing import Optional, List, Dict, Any
from config import settings

HEADERS = {"Accept": "application/json"}


async def _get(path: str, params: dict = {}) -> Dict[str, Any]:
    params["api_key"] = settings.TMDB_API_KEY
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{settings.TMDB_BASE_URL}{path}", params=params, headers=HEADERS)
        r.raise_for_status()
        return r.json()


def image_url(path: Optional[str], size: str = "w500") -> Optional[str]:
    if not path:
        return None
    return f"{settings.TMDB_IMAGE_BASE}/{size}{path}"


async def get_popular_movies(page: int = 1) -> Dict:
    data = await _get("/movie/popular", {"page": page, "language": "en-US"})
    return data


async def get_trending_movies(time_window: str = "week") -> Dict:
    data = await _get(f"/trending/movie/{time_window}", {"language": "en-US"})
    return data


async def get_top_rated_movies(page: int = 1) -> Dict:
    data = await _get("/movie/top_rated", {"page": page, "language": "en-US"})
    return data


async def get_now_playing(page: int = 1) -> Dict:
    data = await _get("/movie/now_playing", {"page": page, "language": "en-US"})
    return data


async def get_upcoming(page: int = 1) -> Dict:
    data = await _get("/movie/upcoming", {"page": page, "language": "en-US"})
    return data


async def search_movies(query: str, page: int = 1) -> Dict:
    data = await _get("/search/movie", {"query": query, "page": page, "language": "en-US"})
    return data


async def get_movie_detail(movie_id: int) -> Dict:
    data = await _get(f"/movie/{movie_id}", {"language": "en-US", "append_to_response": "credits,videos,similar"})
    return data


async def get_movie_reviews(movie_id: int, page: int = 1) -> Dict:
    data = await _get(f"/movie/{movie_id}/reviews", {"page": page, "language": "en-US"})
    return data


async def get_all_reviews(movie_id: int, max_pages: int = 5) -> List[Dict]:
    """Fetch multiple pages of reviews for RAG training."""
    all_reviews = []
    page = 1
    while page <= max_pages:
        data = await _get(f"/movie/{movie_id}/reviews", {"page": page, "language": "en-US"})
        results = data.get("results", [])
        if not results:
            break
        all_reviews.extend(results)
        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
    return all_reviews


async def get_genres() -> Dict:
    data = await _get("/genre/movie/list", {"language": "en-US"})
    return data


async def get_movies_by_genre(genre_id: int, page: int = 1) -> Dict:
    data = await _get("/discover/movie", {
        "with_genres": genre_id,
        "page": page,
        "language": "en-US",
        "sort_by": "popularity.desc"
    })
    return data


async def get_movie_videos(movie_id: int) -> Dict:
    data = await _get(f"/movie/{movie_id}/videos", {"language": "en-US"})
    return data
