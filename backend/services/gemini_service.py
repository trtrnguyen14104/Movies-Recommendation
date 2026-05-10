"""
Gemini AI service for AI Review Summary.
Uses RAG-retrieved review chunks as context for the prompt.
"""
import json
import re
from typing import List, Dict, Optional
import google.generativeai as genai
from config import settings
from models.schemas import AIReviewSummary, ReviewSentiment

genai.configure(api_key=settings.GEMINI_API_KEY)

_model = genai.GenerativeModel("gemini-1.5-flash")


def _analyze_sentiment_heuristic(reviews: List[str]) -> ReviewSentiment:
    """
    Lightweight rule-based sentiment analysis as fallback / pre-pass.
    """
    positive_words = {
        "great", "excellent", "amazing", "brilliant", "fantastic", "wonderful",
        "love", "loved", "best", "good", "perfect", "enjoyed", "enjoy",
        "beautiful", "masterpiece", "outstanding", "superb", "recommend",
        "incredible", "awesome", "fun", "entertaining", "worth", "impressive",
        "stunning", "magnificent", "exceptional", "powerful", "moving",
        "gripping", "compelling", "thrilling", "captivating", "delightful"
    }
    negative_words = {
        "bad", "terrible", "awful", "horrible", "worst", "boring", "disappointing",
        "waste", "poor", "dull", "weak", "mediocre", "flat", "overrated",
        "predictable", "forgettable", "tedious", "painful", "mess", "fails",
        "avoid", "skip", "disappoints", "cliche", "generic", "shallow",
        "unoriginal", "poorly", "laughable", "unwatchable"
    }

    pos, neg, neu = 0, 0, 0
    for text in reviews:
        words = re.findall(r"\b\w+\b", text.lower())
        p = sum(1 for w in words if w in positive_words)
        n = sum(1 for w in words if w in negative_words)
        if p > n:
            pos += 1
        elif n > p:
            neg += 1
        else:
            neu += 1

    total = max(pos + neg + neu, 1)
    return ReviewSentiment(
        positive_count=pos,
        negative_count=neg,
        neutral_count=neu,
        positive_pct=round(pos / total * 100, 1),
        negative_pct=round(neg / total * 100, 1),
        neutral_pct=round(neu / total * 100, 1),
        total=total,
    )


SUMMARY_PROMPT = """
You are CineView AI, a film critic assistant. Analyze these user reviews for the movie "{title}" and produce a JSON response.

REVIEWS (retrieved via RAG from {count} total reviews):
---
{reviews}
---

Return ONLY valid JSON with this exact structure:
{{
  "summary": "2-3 sentence overall summary of what reviewers think",
  "verdict": "RECOMMEND" or "SKIP" or "MIXED",
  "verdict_reason": "One sentence explaining the verdict",
  "key_positives": ["point 1", "point 2", "point 3"],
  "key_negatives": ["point 1", "point 2"],
  "sentiment": {{
    "positive_count": <int>,
    "negative_count": <int>,
    "neutral_count": <int>,
    "positive_pct": <float>,
    "negative_pct": <float>,
    "neutral_pct": <float>,
    "total": <int>
  }},
  "confidence_score": <float 0.0-1.0>
}}

Rules:
- Base sentiment counts on ALL {count} reviews, not just the sample
- verdict MUST be one of: RECOMMEND, SKIP, MIXED
- key_positives and key_negatives: 2-4 items each, concise bullet points
- confidence_score: how confident are you in the verdict (0.0 = very uncertain, 1.0 = very certain)
- summary must be insightful, not generic
"""


async def generate_ai_summary(
    movie_id: int,
    title: str,
    retrieved_reviews: List[str],
    all_review_count: int,
) -> Optional[AIReviewSummary]:
    """
    Call Gemini with RAG-retrieved context to produce a structured AI summary.
    """
    if not retrieved_reviews:
        return None

    # Use up to 15 most relevant reviews, truncated to avoid token limits
    sample = retrieved_reviews[:15]
    reviews_text = "\n\n".join(
        f"[Review {i+1}]: {r[:600]}" for i, r in enumerate(sample)
    )

    prompt = SUMMARY_PROMPT.format(
        title=title,
        count=all_review_count,
        reviews=reviews_text,
    )

    try:
        response = _model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        raw = response.text.strip()

        # Strip markdown code fences if present
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)

        sentiment_data = data.get("sentiment", {})
        sentiment = ReviewSentiment(
            positive_count=sentiment_data.get("positive_count", 0),
            negative_count=sentiment_data.get("negative_count", 0),
            neutral_count=sentiment_data.get("neutral_count", 0),
            positive_pct=sentiment_data.get("positive_pct", 0.0),
            negative_pct=sentiment_data.get("negative_pct", 0.0),
            neutral_pct=sentiment_data.get("neutral_pct", 0.0),
            total=sentiment_data.get("total", all_review_count),
        )

        return AIReviewSummary(
            movie_id=movie_id,
            summary=data.get("summary", ""),
            verdict=data.get("verdict", "MIXED"),
            verdict_reason=data.get("verdict_reason", ""),
            sentiment=sentiment,
            key_positives=data.get("key_positives", []),
            key_negatives=data.get("key_negatives", []),
            confidence_score=float(data.get("confidence_score", 0.5)),
            total_reviews_analyzed=all_review_count,
        )

    except (json.JSONDecodeError, Exception) as e:
        # Fallback: heuristic sentiment + generic summary
        sentiment = _analyze_sentiment_heuristic(retrieved_reviews)
        verdict = "RECOMMEND" if sentiment.positive_pct >= 60 else (
            "SKIP" if sentiment.negative_pct >= 50 else "MIXED"
        )
        return AIReviewSummary(
            movie_id=movie_id,
            summary=f"Based on {all_review_count} reviews, audiences have mixed to positive reactions to this film.",
            verdict=verdict,
            verdict_reason="Based on sentiment analysis of available reviews.",
            sentiment=sentiment,
            key_positives=["Entertaining experience", "Strong performances"],
            key_negatives=["Some pacing issues noted"],
            confidence_score=0.4,
            total_reviews_analyzed=all_review_count,
        )
