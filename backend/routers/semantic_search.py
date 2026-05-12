"""
Semantic search router.
  GET /search/semantic?q=phim buồn về không gian

Uses Gemini embeddings + ChromaDB to understand query intent,
falling back to TMDB keyword search.
"""
import logging
from fastapi import APIRouter, Query, HTTPException
from services import tmdb_service
from services.tmdb_service import image_url
from cachetools import TTLCache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

_cache: TTLCache = TTLCache(maxsize=500, ttl=600)


def _enrich(movie: dict) -> dict:
    movie["poster_url"] = image_url(movie.get("poster_path"), "w500")
    movie["backdrop_url"] = image_url(movie.get("backdrop_path"), "w1280")
    return movie


@router.get("/semantic")
async def semantic_search(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    limit: int = Query(12, ge=1, le=20),
):
    """
    Semantic movie search using Gemini embeddings + ChromaDB vector store.

    Understands natural language like:
      - "phim buồn về không gian"  (sad movie about space)
      - "romantic comedy with time travel"
      - "superhero movie with family themes"

    Falls back to TMDB keyword search when ChromaDB is unavailable
    or no indexed movies are found.
    """
    cache_key = f"{q.lower().strip()}_{limit}"
    if cache_key in _cache:
        return _cache[cache_key]

    # ── Step 1: Try ChromaDB semantic search ──────────────────────────────────
    try:
        from services.chromadb_service import get_movies_collection
        from services.embedding_service import embed_query
        import google.generativeai as genai
        from config import settings

        movies_col = get_movies_collection()
        count = movies_col.count()

        if count > 0:
            q_embedding = embed_query(q)
            if q_embedding is not None:
                results = movies_col.query(
                    query_embeddings=[q_embedding],
                    n_results=min(limit, count),
                    include=["metadatas", "distances"],
                )
                candidate_ids = [int(mid) for mid in results.get("ids", [[]])[0]]

                if candidate_ids:
                    enriched = []
                    for mid in candidate_ids:
                        try:
                            movie = await tmdb_service.get_movie_detail(mid)
                            enriched.append(_enrich(movie))
                        except Exception:
                            pass

                    if enriched:
                        out = {
                            "query": q,
                            "results": enriched,
                            "total": len(enriched),
                            "method": "chromadb_semantic",
                        }
                        _cache[cache_key] = out
                        return out
    except Exception as e:
        logger.warning(f"Semantic search via ChromaDB failed: {e}, falling back")

    # ── Step 2: AI-enhanced TMDB keyword search ───────────────────────────────
    # Use Gemini to extract English search keywords from the query,
    # then forward to TMDB's text search.
    search_query = q
    try:
        import google.generativeai as genai
        from config import settings
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            f"Extract 3-5 concise English movie search keywords from this query "
            f"(output ONLY the keywords, nothing else): {q}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.1, max_output_tokens=50,
            ),
        )
        search_query = resp.text.strip()
    except Exception:
        pass  # use original query

    data = await tmdb_service.search_movies(search_query, page=1)
    results = [_enrich(m) for m in data.get("results", [])[:limit]]

    out = {
        "query": q,
        "interpreted_as": search_query if search_query != q else None,
        "results": results,
        "total": len(results),
        "method": "ai_keyword_tmdb",
    }
    _cache[cache_key] = out
    return out
