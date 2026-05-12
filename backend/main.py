import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import movies, ai_summary, recommendations
from routers.semantic_search import router as semantic_router
from routers.indexing import router as indexing_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: ensure the movie index has at least 50 documents.
    If not, kick off the indexing pipeline in the background so that
    semantic search works immediately after the server warms up.
    """
    try:
        from services.movie_indexing_service import ensure_minimum_index
        await ensure_minimum_index(min_count=50)
    except Exception as e:
        logger.error(f"Startup indexing check failed: {e}")
    yield
    # Shutdown (nothing to clean up)


app = FastAPI(
    title="CineView API",
    description="Movie preview platform with AI-powered review analysis",
    version="3.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movies.router)
app.include_router(ai_summary.router)
app.include_router(recommendations.router)
app.include_router(semantic_router)
app.include_router(indexing_router)


@app.get("/")
async def root():
    return {"message": "CineView API", "version": "3.1.0"}


@app.get("/health")
async def health():
    """Health check + quick index readiness indicator."""
    try:
        from services.chromadb_service import get_movies_collection
        movies_count = get_movies_collection().count()
        index_ready = movies_count >= 50
    except Exception:
        movies_count = 0
        index_ready = False

    return {
        "status": "ok",
        "movies_indexed": movies_count,
        "semantic_search_ready": index_ready,
    }
