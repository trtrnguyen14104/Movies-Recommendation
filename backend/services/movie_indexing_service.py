"""
Movie Indexing Pipeline
=======================
Builds the semantic movie corpus in ChromaDB so that semantic search
and vector-based recommendations actually work.

What this does
--------------
1. Fetches popular / top-rated / trending / now-playing / upcoming movies
   from TMDB (configurable, default ~300 movies across 5 sources).
2. For each movie, builds a *rich* text representation that fuses:
     - title, tagline, overview
     - genre names
     - cast & director names
     - release year, vote average
3. Generates a Gemini embedding (768-dim) for that text.
4. Upserts into the ChromaDB `movies` collection.

The pipeline is:
  - **Idempotent** – already-indexed movies are skipped via a local
    seen-set; ChromaDB upsert handles the rest.
  - **Rate-limited** – configurable per-batch sleep to avoid hitting
    Gemini / TMDB rate limits.
  - **Resumable** – if interrupted, re-running picks up where it left
    off because upsert is safe.
  - **Enriched metadata** – stores title, genres, vote_average,
    release_year, popularity so downstream queries can filter/sort.

Usage
-----
  # In Python (e.g. startup hook)
  from services.movie_indexing_service import run_indexing_pipeline
  await run_indexing_pipeline()

  # Via REST API
  POST /indexing/start          – async background job
  GET  /indexing/status         – check progress / counts
  POST /indexing/movie/{id}     – index a single movie immediately
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from services import tmdb_service
from services.embedding_service import embed_text
from services.chromadb_service import get_movies_collection

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

PAGES_PER_SOURCE = 3          # 20 movies/page × 3 pages × 5 sources ≈ 300 movies
BATCH_SIZE = 10               # embed N movies before upserting to ChromaDB
BATCH_SLEEP_SEC = 1.0         # sleep between batches (Gemini rate-limit safety)
MOVIE_SLEEP_SEC = 0.15        # sleep between individual TMDB detail fetches


# ── Progress tracking ─────────────────────────────────────────────────────────

@dataclass
class IndexingProgress:
    status: str = "idle"          # idle | running | completed | failed
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    total_fetched: int = 0
    total_indexed: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    current_source: str = ""
    error: Optional[str] = None
    sources_completed: List[str] = field(default_factory=list)


_progress = IndexingProgress()


def get_progress() -> IndexingProgress:
    return _progress


# ── Rich text builder ─────────────────────────────────────────────────────────

def _build_movie_document(detail: dict) -> str:
    """
    Build a rich natural-language document for a movie.
    More information → better embeddings → better search quality.
    """
    title = detail.get("title", "")
    original_title = detail.get("original_title", "")
    tagline = detail.get("tagline", "")
    overview = detail.get("overview", "")
    release_date = detail.get("release_date", "")
    release_year = release_date[:4] if release_date else ""
    vote_avg = detail.get("vote_average", 0)
    runtime = detail.get("runtime", 0)

    # Genres
    genres = " ".join(g.get("name", "") for g in detail.get("genres", []))

    # Top cast (up to 8)
    credits = detail.get("credits", {})
    cast_names = [
        p.get("name", "") for p in credits.get("cast", [])[:8]
    ]
    cast_str = ", ".join(cast_names)

    # Director(s)
    directors = [
        p.get("name", "") for p in credits.get("crew", [])
        if p.get("job") == "Director"
    ]
    director_str = ", ".join(directors)

    # Keywords (if present – TMDB detail can include these)
    keywords = detail.get("keywords", {})
    kw_names = [k.get("name", "") for k in keywords.get("keywords", [])[:10]]
    kw_str = " ".join(kw_names)

    parts = [
        f"Title: {title}",
    ]
    if original_title and original_title != title:
        parts.append(f"Original title: {original_title}")
    if tagline:
        parts.append(f"Tagline: {tagline}")
    if overview:
        parts.append(f"Overview: {overview}")
    if genres:
        parts.append(f"Genres: {genres}")
    if release_year:
        parts.append(f"Year: {release_year}")
    if vote_avg:
        parts.append(f"Rating: {vote_avg:.1f}/10")
    if runtime:
        parts.append(f"Runtime: {runtime} minutes")
    if director_str:
        parts.append(f"Director: {director_str}")
    if cast_str:
        parts.append(f"Cast: {cast_str}")
    if kw_str:
        parts.append(f"Keywords: {kw_str}")

    return "\n".join(parts)


def _build_metadata(detail: dict) -> dict:
    """Flat metadata dict for ChromaDB (all values must be str/int/float/bool)."""
    release_date = detail.get("release_date", "")
    genres = detail.get("genres", [])
    genre_names = " | ".join(g.get("name", "") for g in genres)
    genre_ids = ",".join(str(g.get("id", "")) for g in genres)

    credits = detail.get("credits", {})
    directors = [
        p.get("name", "") for p in credits.get("crew", [])
        if p.get("job") == "Director"
    ]

    return {
        "movie_id": str(detail.get("id", "")),
        "title": detail.get("title", ""),
        "original_title": detail.get("original_title", ""),
        "release_year": release_date[:4] if release_date else "",
        "release_date": release_date,
        "vote_average": float(detail.get("vote_average", 0)),
        "vote_count": int(detail.get("vote_count", 0)),
        "popularity": float(detail.get("popularity", 0)),
        "genres": genre_names,
        "genre_ids": genre_ids,
        "director": " | ".join(directors),
        "runtime": int(detail.get("runtime") or 0),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Core indexer ──────────────────────────────────────────────────────────────

async def index_single_movie(movie_id: int, force: bool = False) -> bool:
    """
    Index one movie into ChromaDB.
    Returns True if successfully indexed, False otherwise.
    If the movie is already indexed and force=False, skips it.
    """
    col = get_movies_collection()

    # Check if already indexed
    if not force:
        try:
            existing = col.get(ids=[str(movie_id)], include=["embeddings"])
            embs = existing.get("embeddings") or []
            if embs and embs[0] and max(abs(v) for v in embs[0]) > 0:
                logger.debug(f"Movie {movie_id} already indexed – skipping")
                return False  # already done
        except Exception:
            pass  # ChromaDB error → re-index

    try:
        # Fetch full detail (includes credits, similar, videos)
        detail = await tmdb_service.get_movie_detail(movie_id)

        # Build rich document + embedding
        document = _build_movie_document(detail)
        metadata = _build_metadata(detail)
        embedding = embed_text(document, task_type="retrieval_document")

        if embedding is None:
            logger.warning(f"Could not generate embedding for movie {movie_id}")
            return False

        col.upsert(
            ids=[str(movie_id)],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata],
        )
        logger.debug(f"Indexed movie {movie_id}: {detail.get('title', '')}")
        return True

    except Exception as e:
        logger.error(f"Failed to index movie {movie_id}: {e}")
        return False


async def _fetch_movie_ids_from_source(source: str, pages: int) -> List[int]:
    """Fetch raw movie ID lists from a TMDB endpoint."""
    ids: List[int] = []
    for page in range(1, pages + 1):
        try:
            if source == "popular":
                data = await tmdb_service.get_popular_movies(page)
            elif source == "top_rated":
                data = await tmdb_service.get_top_rated_movies(page)
            elif source == "trending":
                data = await tmdb_service.get_trending_movies("week")
            elif source == "now_playing":
                data = await tmdb_service.get_now_playing(page)
            elif source == "upcoming":
                data = await tmdb_service.get_upcoming(page)
            else:
                break

            for m in data.get("results", []):
                mid = m.get("id")
                if mid:
                    ids.append(mid)

            # Trending endpoint doesn't support pagination
            if source == "trending":
                break

        except Exception as e:
            logger.warning(f"Failed fetching {source} page {page}: {e}")

    return ids


# ── Full pipeline ─────────────────────────────────────────────────────────────

async def run_indexing_pipeline(
    pages_per_source: int = PAGES_PER_SOURCE,
    force: bool = False,
) -> IndexingProgress:
    """
    Run the full movie indexing pipeline.
    Safe to call concurrently – if already running, returns current progress.
    """
    global _progress

    if _progress.status == "running":
        logger.info("Indexing already running – skipping duplicate call")
        return _progress

    _progress = IndexingProgress(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    sources = ["popular", "top_rated", "trending", "now_playing", "upcoming"]
    seen_ids: set = set()

    try:
        col = get_movies_collection()
        # Pre-populate seen_ids from what's already in ChromaDB
        if not force:
            try:
                existing = col.get(include=[])
                for eid in (existing.get("ids") or []):
                    seen_ids.add(int(eid))
                logger.info(f"Found {len(seen_ids)} already-indexed movies in ChromaDB")
            except Exception as e:
                logger.warning(f"Could not pre-load existing IDs: {e}")

        batch_ids: List[int] = []
        batch_details = []
        batch_documents = []
        batch_metadata = []
        batch_embeddings = []

        async def _flush_batch():
            """Upsert the current batch into ChromaDB."""
            if not batch_ids:
                return
            try:
                col.upsert(
                    ids=[str(i) for i in batch_ids],
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadata,
                )
                _progress.total_indexed += len(batch_ids)
                logger.info(
                    f"Upserted batch of {len(batch_ids)} movies "
                    f"(total indexed: {_progress.total_indexed})"
                )
            except Exception as e:
                logger.error(f"Batch upsert failed: {e}")
                _progress.total_failed += len(batch_ids)
            batch_ids.clear()
            batch_documents.clear()
            batch_metadata.clear()
            batch_embeddings.clear()

        for source in sources:
            _progress.current_source = source
            logger.info(f"Fetching movie IDs from source: {source}")

            movie_ids = await _fetch_movie_ids_from_source(source, pages_per_source)
            _progress.total_fetched += len(movie_ids)

            for movie_id in movie_ids:
                if movie_id in seen_ids:
                    _progress.total_skipped += 1
                    continue
                seen_ids.add(movie_id)

                try:
                    await asyncio.sleep(MOVIE_SLEEP_SEC)
                    detail = await tmdb_service.get_movie_detail(movie_id)
                    document = _build_movie_document(detail)
                    metadata = _build_metadata(detail)
                    embedding = embed_text(document, task_type="retrieval_document")

                    if embedding is None:
                        _progress.total_failed += 1
                        continue

                    batch_ids.append(movie_id)
                    batch_documents.append(document)
                    batch_metadata.append(metadata)
                    batch_embeddings.append(embedding)

                    if len(batch_ids) >= BATCH_SIZE:
                        await _flush_batch()
                        await asyncio.sleep(BATCH_SLEEP_SEC)

                except Exception as e:
                    logger.warning(f"Error processing movie {movie_id}: {e}")
                    _progress.total_failed += 1

            # Flush remaining in batch after each source
            await _flush_batch()
            _progress.sources_completed.append(source)
            logger.info(f"Completed source: {source}")

        _progress.status = "completed"
        _progress.finished_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Indexing pipeline completed. "
            f"Indexed: {_progress.total_indexed}, "
            f"Skipped: {_progress.total_skipped}, "
            f"Failed: {_progress.total_failed}"
        )

    except Exception as e:
        _progress.status = "failed"
        _progress.error = str(e)
        _progress.finished_at = datetime.now(timezone.utc).isoformat()
        logger.error(f"Indexing pipeline failed: {e}")

    return _progress


async def ensure_minimum_index(min_count: int = 50) -> None:
    """
    Called at startup: if fewer than `min_count` movies are indexed,
    kick off the pipeline in the background.
    """
    try:
        col = get_movies_collection()
        count = col.count()
        logger.info(f"ChromaDB movies collection has {count} documents")
        if count < min_count:
            logger.info(
                f"Only {count} movies indexed (minimum {min_count}). "
                "Starting background indexing pipeline..."
            )
            asyncio.create_task(run_indexing_pipeline())
        else:
            logger.info(f"Movie index healthy ({count} movies). Skipping auto-indexing.")
    except Exception as e:
        logger.error(f"ensure_minimum_index failed: {e}")
