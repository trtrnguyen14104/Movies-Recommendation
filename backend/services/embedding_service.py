"""
Embedding service using Gemini text-embedding-004.
Generates 768-dim vectors for semantic search and similarity.
"""
import logging
from typing import List, Optional
import google.generativeai as genai
from config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)

EMBEDDING_MODEL = "models/text-embedding-004"


def embed_text(text: str, task_type: str = "retrieval_document") -> Optional[List[float]]:
    """
    Generate a single embedding vector for the given text.
    task_type: "retrieval_document" | "retrieval_query" | "semantic_similarity"
    Returns None on failure.
    """
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text[:2000],   # truncate to avoid token limits
            task_type=task_type,
        )
        return result["embedding"]
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return None


def embed_movie(movie: dict) -> Optional[List[float]]:
    """
    Build a rich text representation of a movie and embed it.
    Used for semantic search and similar-movie lookups.
    """
    genres = " ".join(g.get("name", "") for g in movie.get("genres", []))
    genre_ids = " ".join(str(g) for g in movie.get("genre_ids", []))
    text = (
        f"Title: {movie.get('title', '')}\n"
        f"Overview: {movie.get('overview', '')}\n"
        f"Genres: {genres or genre_ids}\n"
        f"Tagline: {movie.get('tagline', '')}"
    )
    return embed_text(text, task_type="retrieval_document")


def embed_query(query: str) -> Optional[List[float]]:
    """Embed a user search query for semantic retrieval."""
    return embed_text(query, task_type="retrieval_query")
