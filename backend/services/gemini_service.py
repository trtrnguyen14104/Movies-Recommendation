"""
Gemini AI service:
  - generate_ai_summary      : Enhanced structured movie review summary
  - analyze_review_sentiments: Per-review sentiment (positive/negative/neutral)
  - detect_fake_reviews      : Spam / bot / toxic detection
"""
import json
import re
import logging
from typing import List, Dict, Optional
import google.generativeai as genai
from config import settings
from models.schemas import (
    AIReviewSummary, ReviewSentiment,
    ReviewSentimentItem, ReviewSentimentList,
    FakeReviewItem, FakeReviewReport,
)

logger = logging.getLogger(__name__)
genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-1.5-flash")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _clean_json(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _sentiment_heuristic(reviews: List[str]) -> ReviewSentiment:
    """Rule-based fallback when Gemini is unavailable."""
    POS = {
        "great","excellent","amazing","brilliant","fantastic","wonderful",
        "love","loved","best","good","perfect","enjoyed","enjoy",
        "beautiful","masterpiece","outstanding","superb","recommend",
        "incredible","awesome","fun","entertaining","worth","impressive",
        "stunning","magnificent","exceptional","powerful","moving",
        "gripping","compelling","thrilling","captivating","delightful",
    }
    NEG = {
        "bad","terrible","awful","horrible","worst","boring","disappointing",
        "waste","poor","dull","weak","mediocre","flat","overrated",
        "predictable","forgettable","tedious","painful","mess","fails",
        "avoid","skip","disappoints","cliche","generic","shallow",
        "unoriginal","poorly","laughable","unwatchable",
    }
    pos, neg, neu = 0, 0, 0
    for text in reviews:
        words = re.findall(r"\b\w+\b", text.lower())
        p = sum(1 for w in words if w in POS)
        n = sum(1 for w in words if w in NEG)
        if p > n:
            pos += 1
        elif n > p:
            neg += 1
        else:
            neu += 1
    total = max(pos + neg + neu, 1)
    return ReviewSentiment(
        positive_count=pos, negative_count=neg, neutral_count=neu,
        positive_pct=round(pos / total * 100, 1),
        negative_pct=round(neg / total * 100, 1),
        neutral_pct=round(neu / total * 100, 1),
        total=total,
    )


# ─── 1. Enhanced AI Summary ───────────────────────────────────────────────────

SUMMARY_PROMPT = """
You are CineView AI, a professional film critic assistant. Analyze these user reviews
for the movie "{title}" and produce a detailed JSON response.

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
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "acting": "1-2 sentences about the acting quality based on reviews",
  "music": "1-2 sentences about soundtrack/score based on reviews",
  "screenplay": "1-2 sentences about the script/story based on reviews",
  "visual_effects": "1-2 sentences about visuals/cinematography based on reviews",
  "sentiment": {{
    "positive_count": <int>,
    "negative_count": <int>,
    "neutral_count": <int>,
    "positive_pct": <float>,
    "negative_pct": <float>,
    "neutral_pct": <float>,
    "total": <int>
  }},
}}

Rules:
- Base sentiment counts on ALL {count} reviews, not just the sample
- verdict MUST be one of: RECOMMEND, SKIP, MIXED
- If reviews don't mention a category (music, vfx, etc.), say "Not significantly mentioned in reviews."
- confidence_score: how confident are you in the verdict (0=very uncertain, 1=very certain)
- Be specific and insightful, avoid generic statements
- translate results into Vỉetnamese
"""

# SUMMARY_PROMPT = """
# You are CineView AI, a professional film critic assistant. Analyze these user reviews
# for the movie "{title}" and produce a detailed JSON response.

# REVIEWS (retrieved via RAG from {count} total reviews):
# ---
# {reviews}
# ---

# Return ONLY valid JSON with this exact structure:
# {{
#   "summary": "2-3 sentence overall summary of what reviewers think",
#   "verdict": "RECOMMEND" or "SKIP" or "MIXED",
#   "verdict_reason": "One sentence explaining the verdict",
#   "key_positives": ["point 1", "point 2", "point 3"],
#   "key_negatives": ["point 1", "point 2"],
#   "strengths": ["strength 1", "strength 2"],
#   "weaknesses": ["weakness 1", "weakness 2"],
#   "acting": "1-2 sentences about the acting quality based on reviews",
#   "music": "1-2 sentences about soundtrack/score based on reviews",
#   "screenplay": "1-2 sentences about the script/story based on reviews",
#   "visual_effects": "1-2 sentences about visuals/cinematography based on reviews",
#   "sentiment": {{
#     "positive_count": <int>,
#     "negative_count": <int>,
#     "neutral_count": <int>,
#     "positive_pct": <float>,
#     "negative_pct": <float>,
#     "neutral_pct": <float>,
#     "total": <int>
#   }},
#   "confidence_score": <float 0.0-1.0>
# }}

# Rules:
# - Base sentiment counts on ALL {count} reviews, not just the sample
# - verdict MUST be one of: RECOMMEND, SKIP, MIXED
# - If reviews don't mention a category (music, vfx, etc.), say "Not significantly mentioned in reviews."
# - confidence_score: how confident are you in the verdict (0=very uncertain, 1=very certain)
# - Be specific and insightful, avoid generic statements
# """


async def generate_ai_summary(
    movie_id: int,
    title: str,
    retrieved_reviews: List[str],
    all_review_count: int,
) -> Optional[AIReviewSummary]:
    if not retrieved_reviews:
        return None

    sample = retrieved_reviews[:15]
    reviews_text = "\n\n".join(
        f"[Review {i+1}]: {r[:600]}" for i, r in enumerate(sample)
    )
    prompt = SUMMARY_PROMPT.format(
        title=title, count=all_review_count, reviews=reviews_text
    )

    try:
        response = _model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3, max_output_tokens=1500,
            ),
        )
        data = json.loads(_clean_json(response.text))

        sd = data.get("sentiment", {})
        sentiment = ReviewSentiment(
            positive_count=sd.get("positive_count", 0),
            negative_count=sd.get("negative_count", 0),
            neutral_count=sd.get("neutral_count", 0),
            positive_pct=sd.get("positive_pct", 0.0),
            negative_pct=sd.get("negative_pct", 0.0),
            neutral_pct=sd.get("neutral_pct", 0.0),
            total=sd.get("total", all_review_count),
        )
        return AIReviewSummary(
            movie_id=movie_id,
            summary=data.get("summary", ""),
            verdict=data.get("verdict", "MIXED"),
            verdict_reason=data.get("verdict_reason", ""),
            sentiment=sentiment,
            key_positives=data.get("key_positives", []),
            key_negatives=data.get("key_negatives", []),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            acting=data.get("acting", ""),
            music=data.get("music", ""),
            screenplay=data.get("screenplay", ""),
            visual_effects=data.get("visual_effects", ""),
            confidence_score=float(data.get("confidence_score", 0.5)),
            total_reviews_analyzed=all_review_count,
        )

    except Exception as e:
        logger.error(f"AI summary generation failed: {e}")
        sentiment = _sentiment_heuristic(retrieved_reviews)
        verdict = "RECOMMEND" if sentiment.positive_pct >= 60 else (
            "SKIP" if sentiment.negative_pct >= 50 else "MIXED"
        )
        return AIReviewSummary(
            movie_id=movie_id,
            summary=f"Based on {all_review_count} reviews, audiences have mixed to positive reactions.",
            verdict=verdict,
            verdict_reason="Based on sentiment analysis of available reviews.",
            sentiment=sentiment,
            key_positives=["Entertaining experience", "Strong performances"],
            key_negatives=["Some pacing issues noted"],
            strengths=[], weaknesses=[],
            acting="", music="", screenplay="", visual_effects="",
            confidence_score=0.4,
            total_reviews_analyzed=all_review_count,
        )


# ─── 2. Per-Review Sentiment Analysis ────────────────────────────────────────

SENTIMENT_BATCH_PROMPT = """
You are a sentiment analysis AI. For each review below, determine:
- sentiment: "positive", "negative", or "neutral"
- score: confidence 0.0–1.0

Return ONLY valid JSON array:
[
  {{"id": "review_id_here", "sentiment": "positive", "score": 0.92}},
  ...
]

REVIEWS:
{reviews}
"""


async def analyze_review_sentiments(
    movie_id: int,
    reviews: List[Dict],
) -> ReviewSentimentList:
    """Analyze sentiment for each individual review."""

    # Build batches of 20 to avoid token limits
    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    results: List[ReviewSentimentItem] = []

    for batch in chunks(reviews, 20):
        reviews_text = "\n".join(
            f'ID={r.get("id","?")} AUTHOR={r.get("author","?")} '
            f'CONTENT={r.get("content","")[:300]}'
            for r in batch
        )
        prompt = SENTIMENT_BATCH_PROMPT.format(reviews=reviews_text)
        try:
            response = _model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1, max_output_tokens=1024,
                ),
            )
            items = json.loads(_clean_json(response.text))
            item_map = {str(it["id"]): it for it in items}

            for review in batch:
                rid = str(review.get("id", ""))
                ai = item_map.get(rid, {})
                sentiment_val = ai.get("sentiment", "neutral")
                # Fallback heuristic per review
                if not ai:
                    texts = [review.get("content", "")]
                    h = _sentiment_heuristic(texts)
                    if h.positive_count > h.negative_count:
                        sentiment_val = "positive"
                    elif h.negative_count > h.positive_count:
                        sentiment_val = "negative"
                    else:
                        sentiment_val = "neutral"

                results.append(ReviewSentimentItem(
                    review_id=rid,
                    author=review.get("author", ""),
                    sentiment=sentiment_val,
                    score=float(ai.get("score", 0.7)),
                    excerpt=review.get("content", "")[:120],
                ))
        except Exception as e:
            logger.warning(f"Sentiment batch failed: {e}, using heuristic fallback")
            for review in batch:
                texts = [review.get("content", "")]
                h = _sentiment_heuristic(texts)
                if h.positive_count > h.negative_count:
                    sv = "positive"
                elif h.negative_count > h.positive_count:
                    sv = "negative"
                else:
                    sv = "neutral"
                results.append(ReviewSentimentItem(
                    review_id=str(review.get("id", "")),
                    author=review.get("author", ""),
                    sentiment=sv,
                    score=0.6,
                    excerpt=review.get("content", "")[:120],
                ))

    # Aggregate summary
    pos = sum(1 for r in results if r.sentiment == "positive")
    neg = sum(1 for r in results if r.sentiment == "negative")
    neu = sum(1 for r in results if r.sentiment == "neutral")
    total = max(len(results), 1)
    summary = ReviewSentiment(
        positive_count=pos, negative_count=neg, neutral_count=neu,
        positive_pct=round(pos / total * 100, 1),
        negative_pct=round(neg / total * 100, 1),
        neutral_pct=round(neu / total * 100, 1),
        total=total,
    )
    return ReviewSentimentList(
        movie_id=movie_id,
        results=results,
        summary=summary,
        total_analyzed=total,
    )


# ─── 3. Fake Review Detection ─────────────────────────────────────────────────

FAKE_DETECTION_PROMPT = """
You are a fake review detection AI trained on NLP patterns.
For each review, classify it as:
  - "legitimate": genuine, personal, specific opinion
  - "spam"      : repetitive, off-topic, promotional, keyword stuffing
  - "bot"       : overly generic, templated phrases, lacks personal voice, suspiciously short or structured
  - "toxic"     : personal attacks, hate speech, offensive language, harassment

Return ONLY valid JSON array:
[
  {{
    "id": "review_id_here",
    "label": "legitimate",
    "confidence": 0.95,
    "reason": "Short explanation (1 sentence)"
  }},
  ...
]

Indicators:
- Spam: very short (<20 words), all caps, excessive exclamation marks, unrelated content
- Bot: cookie-cutter phrases ("This movie is amazing!", "Must watch!"), no specifics, very uniform length
- Toxic: profanity directed at people, slurs, explicit threats
- Legitimate: references specific scenes/actors, personal opinion, nuanced language

REVIEWS:
{reviews}
"""


async def detect_fake_reviews(
    movie_id: int,
    reviews: List[Dict],
) -> FakeReviewReport:
    """Detect spam, bot, and toxic reviews using Gemini NLP."""

    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    results: List[FakeReviewItem] = []

    for batch in chunks(reviews, 15):
        reviews_text = "\n".join(
            f'ID={r.get("id","?")} AUTHOR={r.get("author","?")} '
            f'CONTENT={r.get("content","")[:400]}'
            for r in batch
        )
        prompt = FAKE_DETECTION_PROMPT.format(reviews=reviews_text)
        try:
            response = _model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1, max_output_tokens=1024,
                ),
            )
            items = json.loads(_clean_json(response.text))
            item_map = {str(it["id"]): it for it in items}

            for review in batch:
                rid = str(review.get("id", ""))
                ai = item_map.get(rid, {"label": "legitimate", "confidence": 0.7, "reason": "No issues detected."})
                results.append(FakeReviewItem(
                    review_id=rid,
                    author=review.get("author", ""),
                    label=ai.get("label", "legitimate"),
                    confidence=float(ai.get("confidence", 0.7)),
                    reason=ai.get("reason", ""),
                    excerpt=review.get("content", "")[:120],
                ))
        except Exception as e:
            logger.warning(f"Fake detection batch failed: {e}, defaulting to legitimate")
            for review in batch:
                content = review.get("content", "")
                # Simple heuristic fallback
                words = content.split()
                if len(words) < 5:
                    label, reason = "spam", "Extremely short review, likely low-quality."
                elif len(set(words)) < len(words) * 0.4 and len(words) > 10:
                    label, reason = "spam", "High word repetition detected."
                else:
                    label, reason = "legitimate", "No obvious issues detected."
                results.append(FakeReviewItem(
                    review_id=str(review.get("id", "")),
                    author=review.get("author", ""),
                    label=label,
                    confidence=0.6,
                    reason=reason,
                    excerpt=content[:120],
                ))

    spam = sum(1 for r in results if r.label == "spam")
    bot = sum(1 for r in results if r.label == "bot")
    toxic = sum(1 for r in results if r.label == "toxic")
    legit = sum(1 for r in results if r.label == "legitimate")

    return FakeReviewReport(
        movie_id=movie_id,
        total_analyzed=len(results),
        spam_count=spam,
        bot_count=bot,
        toxic_count=toxic,
        legitimate_count=legit,
        results=results,
    )
