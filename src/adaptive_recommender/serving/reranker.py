"""Re-ranking and candidate composition engine."""

from __future__ import annotations

from typing import Any

from .fallbacks import RecommendationItem, get_popularity_fallback
from .repositories import BaseServingRepository


DEFAULT_WEIGHTS = {
    "als": 0.60,
    "session_intent": 0.25,
    "popularity": 0.10,
    "brand": 0.05,
}


class RecommenderService:
    """Service that orchestrates candidate retrieval, session-intent weighting, and fallbacks."""

    def __init__(
        self,
        repository: BaseServingRepository,
        weights: dict[str, float] | None = None,
        adaptive_enabled: bool = False,
    ) -> None:
        self.repo = repository
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.adaptive_enabled = adaptive_enabled

    def get_recommendations(
        self,
        user_id: str | None,
        limit: int = 10,
        user_session: str | None = None,
    ) -> tuple[list[RecommendationItem], bool]:
        """Return (recommendations, is_fallback).

        If user_id is None, unknown, or has no candidates, fall back to popularity.
        """
        if not user_id or user_id.strip() in ("", "anonymous", "null", "none"):
            return get_popularity_fallback(self.repo, limit=limit), True

        candidates = self.repo.get_candidates(user_id, limit=limit * 2)
        if not candidates:
            return get_popularity_fallback(self.repo, limit=limit), True

        # Resolve session intents if adaptive mode is active
        intents = self.repo.get_session_intents(user_id, user_session) if self.adaptive_enabled else []
        intent_map = {s.category_code: s.intent_score for s in intents}

        items: list[RecommendationItem] = []
        for c in candidates:
            product = self.repo.get_product(c.product_id)
            category_code = product.category_code if product else None
            brand = product.brand if product else None
            price = product.average_price if product else None
            pop_score = product.popularity_score if product else 0.0

            intent_score = intent_map.get(category_code, 0.0) if category_code else 0.0

            if self.adaptive_enabled and intent_map:
                final_score = (
                    self.weights["als"] * c.als_score
                    + self.weights["session_intent"] * intent_score
                    + self.weights["popularity"] * pop_score
                )
                reason = "adaptive_session_intent" if intent_score > 0 else "long_term_preference"
            else:
                final_score = c.als_score
                reason = "long_term_preference"

            items.append(
                RecommendationItem(
                    product_id=c.product_id,
                    rank=0,  # Assigned after sort
                    score=final_score,
                    score_components={
                        "als": c.als_score,
                        "intent": intent_score,
                        "popularity": pop_score,
                        "brand": 0.0,
                    },
                    category_code=category_code,
                    brand=brand,
                    price=price,
                    reason=reason,
                )
            )

        # Sort by final score descending, tie break by product_id ascending
        items.sort(key=lambda x: (-x.score, x.product_id))

        ranked_items = [
            RecommendationItem(
                product_id=item.product_id,
                rank=idx,
                score=item.score,
                score_components=item.score_components,
                category_code=item.category_code,
                brand=item.brand,
                price=item.price,
                reason=item.reason,
            )
            for idx, item in enumerate(items[:limit], start=1)
        ]

        return ranked_items, False
