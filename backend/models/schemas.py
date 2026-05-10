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


class AIReviewSummary(BaseModel):
    movie_id: int
    summary: str
    verdict: str  # "RECOMMEND" | "SKIP" | "MIXED"
    verdict_reason: str
    sentiment: ReviewSentiment
    key_positives: List[str]
    key_negatives: List[str]
    confidence_score: float
    total_reviews_analyzed: int


class MovieVideos(BaseModel):
    id: int
    results: List[dict]
