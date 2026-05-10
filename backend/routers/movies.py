from fastapi import APIRouter, Query, HTTPException
from services import tmdb_service
from services.tmdb_service import image_url

router = APIRouter(prefix="/movies", tags=["movies"])


def _enrich(movie: dict) -> dict:
    movie["poster_url"] = image_url(movie.get("poster_path"), "w500")
    movie["backdrop_url"] = image_url(movie.get("backdrop_path"), "w1280")
    return movie


@router.get("/popular")
async def popular_movies(page: int = Query(1, ge=1)):
    data = await tmdb_service.get_popular_movies(page)
    data["results"] = [_enrich(m) for m in data.get("results", [])]
    return data


@router.get("/trending")
async def trending_movies(time_window: str = Query("week", pattern="^(day|week)$")):
    data = await tmdb_service.get_trending_movies(time_window)
    data["results"] = [_enrich(m) for m in data.get("results", [])]
    return data


@router.get("/top-rated")
async def top_rated(page: int = Query(1, ge=1)):
    data = await tmdb_service.get_top_rated_movies(page)
    data["results"] = [_enrich(m) for m in data.get("results", [])]
    return data


@router.get("/now-playing")
async def now_playing(page: int = Query(1, ge=1)):
    data = await tmdb_service.get_now_playing(page)
    data["results"] = [_enrich(m) for m in data.get("results", [])]
    return data


@router.get("/upcoming")
async def upcoming(page: int = Query(1, ge=1)):
    data = await tmdb_service.get_upcoming(page)
    data["results"] = [_enrich(m) for m in data.get("results", [])]
    return data


@router.get("/search")
async def search(q: str = Query(..., min_length=1), page: int = Query(1, ge=1)):
    data = await tmdb_service.search_movies(q, page)
    data["results"] = [_enrich(m) for m in data.get("results", [])]
    return data


@router.get("/genres")
async def genres():
    return await tmdb_service.get_genres()


@router.get("/by-genre/{genre_id}")
async def by_genre(genre_id: int, page: int = Query(1, ge=1)):
    data = await tmdb_service.get_movies_by_genre(genre_id, page)
    data["results"] = [_enrich(m) for m in data.get("results", [])]
    return data


@router.get("/{movie_id}")
async def movie_detail(movie_id: int):
    data = await tmdb_service.get_movie_detail(movie_id)
    data = _enrich(data)
    # Enrich cast images
    credits = data.get("credits", {})
    for person in credits.get("cast", [])[:20]:
        person["profile_url"] = image_url(person.get("profile_path"), "w185")
    # Enrich similar
    similar = data.get("similar", {})
    similar["results"] = [_enrich(m) for m in similar.get("results", [])[:12]]
    return data


@router.get("/{movie_id}/videos")
async def movie_videos(movie_id: int):
    return await tmdb_service.get_movie_videos(movie_id)
