from pydantic import BaseModel
from typing import Optional, List


class Movie(BaseModel):
    id: int
    title: str
    overview: Optional[str] = ""
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: Optional[str] = ""
    vote_average: Optional[float] = 0.0
    vote_count: Optional[int] = 0
    genre_ids: Optional[List[int]] = []
    genres: Optional[List[dict]] = []
    runtime: Optional[int] = None
    tagline: Optional[str] = ""
    status: Optional[str] = ""


class Review(BaseModel):
    id: str
    author: str
    author_details: Optional[dict] = {}
    content: str
    created_at: Optional[str] = ""
    url: Optional[str] = ""


class ReviewSentiment(BaseModel):
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    total: int


# ── Per-review sentiment ──────────────────────────────────────────────────────

class ReviewSentimentItem(BaseModel):
    review_id: str
    author: str
    sentiment: str          # "positive" | "negative" | "neutral"
    score: float            # 0.0 – 1.0 confidence
    excerpt: str            # first 120 chars for display


class ReviewSentimentList(BaseModel):
    movie_id: int
    results: List[ReviewSentimentItem]
    summary: ReviewSentiment
    total_analyzed: int


# ── Enhanced AI Summary ───────────────────────────────────────────────────────

class AIReviewSummary(BaseModel):
    movie_id: int
    summary: str
    verdict: str            # "RECOMMEND" | "SKIP" | "MIXED"
    verdict_reason: str
    sentiment: ReviewSentiment
    key_positives: List[str]
    key_negatives: List[str]
    # Enhanced breakdown
    strengths: List[str] = []
    weaknesses: List[str] = []
    acting: str = ""
    music: str = ""
    screenplay: str = ""
    visual_effects: str = ""
    confidence_score: float
    total_reviews_analyzed: int


# ── Fake Review Detection ─────────────────────────────────────────────────────

class FakeReviewItem(BaseModel):
    review_id: str
    author: str
    label: str              # "legitimate" | "spam" | "bot" | "toxic"
    confidence: float       # 0.0 – 1.0
    reason: str
    excerpt: str


class FakeReviewReport(BaseModel):
    movie_id: int
    total_analyzed: int
    spam_count: int
    bot_count: int
    toxic_count: int
    legitimate_count: int
    results: List[FakeReviewItem]


# ── Interaction / Recommendations ─────────────────────────────────────────────

class InteractionRequest(BaseModel):
    session_id: str
    movie_id: int
    action: str             # "like" | "trailer" | "detail"
    genre_ids: Optional[List[int]] = []
    title: Optional[str] = ""


class InteractionRecord(BaseModel):
    session_id: str
    movie_id: int
    action: str
    title: str
    timestamp: str


class RecommendationResult(BaseModel):
    results: List[dict]
    total: int
    method: str             # "chromadb_vector" | "genre_scoring" | "tmdb_similar"
    top_genres: Optional[List[dict]] = []


class VectorStoreStats(BaseModel):
    movies_indexed: int
    reviews_indexed: int
    interactions_logged: int
    collections: List[str]


# ── Misc ──────────────────────────────────────────────────────────────────────

class MovieVideos(BaseModel):
    id: int
    results: List[dict]
