"""
ChromaDB Cloud service.
Manages three collections:
  - movies      : movie embeddings (title + overview + genres) for semantic search & similar
  - reviews     : review embeddings per movie for persistent RAG
  - interactions: user session interaction log for personalized recommendations
"""
import logging
from typing import Optional
import chromadb
from config import settings

logger = logging.getLogger(__name__)

_client: Optional[chromadb.ClientAPI] = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        try:
            _client = chromadb.CloudClient(
                api_key=settings.CHROMADB_API_KEY,
                tenant=settings.CHROMADB_TENANT,
                database=settings.CHROMADB_DATABASE,
            )
            logger.info("ChromaDB Cloud client connected.")
        except Exception as e:
            logger.error(f"ChromaDB connection failed: {e}. Falling back to in-memory.")
            _client = chromadb.Client()
    return _client


def get_movies_collection():
    """Collection for movie semantic embeddings."""
    client = get_client()
    return client.get_or_create_collection(
        name="movies",
        metadata={"hnsw:space": "cosine"},
    )


def get_reviews_collection():
    """Collection for per-review embeddings (persistent RAG)."""
    client = get_client()
    return client.get_or_create_collection(
        name="reviews",
        metadata={"hnsw:space": "cosine"},
    )


def get_interactions_collection():
    """Collection for user interaction history."""
    client = get_client()
    return client.get_or_create_collection(
        name="interactions",
        metadata={"hnsw:space": "cosine"},
    )
