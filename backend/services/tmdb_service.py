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

# lấy danh sách phim theo thể loại
async def get_movies_by_genre_ids(genre_ids: str, page: int = 1) -> Dict:
    """
    Gọi TMDB API để lấy danh sách phim dựa trên thể loại (genre).
    Dùng cho hệ thống gợi ý: user thích Batman (Action, Adventure)
    → hàm này tìm các phim cùng thể loại Action, Adventure.

    Tham số:
        genre_ids (str): Chuỗi các genre_id cách nhau bởi dấu phẩy.
                         Ví dụ: "28,12" nghĩa là Action VÀ Adventure.
                         TMDB sẽ trả về phim thuộc ít nhất 1 trong các genre này.
        page (int):      Trang kết quả muốn lấy. Mặc định là trang 1.
                         Mỗi trang có 20 phim.

    Trả về:
        Dict chứa danh sách phim từ TMDB gồm: id, title, poster, rating...
    """

    # Gọi endpoint /discover/movie của TMDB với các bộ lọc
    data = await _get("/discover/movie", {

        # Lọc phim theo genre — đây là tham số quan trọng nhất
        # Ví dụ: "28,12" → tìm phim Action hoặc Adventure
        "with_genres": genre_ids,

        # Trang kết quả (phân trang), mặc định lấy trang 1
        "page": page,

        # Ngôn ngữ trả về là tiếng Anh
        "language": "en-US",

        # Sắp xếp theo độ phổ biến giảm dần
        # → phim nổi tiếng nhất xuất hiện đầu tiên
        "sort_by": "popularity.desc",

        # Chỉ lấy phim có ít nhất 100 lượt vote
        # → loại bỏ phim vô danh, ít người biết
        "vote_count.gte": 100,
    })

    # Trả về kết quả thô từ TMDB (dict chứa key "results", "total_pages",...)
    return data
