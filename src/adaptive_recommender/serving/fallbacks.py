"""Fallback recommendation strategies for new and anonymous users."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .repositories import BaseServingRepository, ProductStat


@dataclass(frozen=True)
class RecommendationItem:
    product_id: int
    rank: int
    score: float
    score_components: dict[str, float]
    category_code: str | None
    brand: str | None
    price: float | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "rank": self.rank,
            "score": round(self.score, 4),
            "score_components": {k: round(v, 4) for k, v in self.score_components.items()},
            "category_code": self.category_code,
            "brand": self.brand,
            "price": self.price,
            "reason": self.reason,
        }


def get_popularity_fallback(
    repo: BaseServingRepository,
    limit: int = 10,
    category_filter: str | None = None,
) -> list[RecommendationItem]:
    """Generate recommendations based on global product popularity."""
    products = repo.get_products(limit=100)
    if category_filter:
        products = [p for p in products if p.category_code == category_filter]

    items: list[RecommendationItem] = []
    for rank, p in enumerate(products[:limit], start=1):
        items.append(
            RecommendationItem(
                product_id=p.product_id,
                rank=rank,
                score=p.popularity_score,
                score_components={
                    "als": 0.0,
                    "intent": 0.0,
                    "popularity": p.popularity_score,
                    "brand": 0.0,
                },
                category_code=p.category_code,
                brand=p.brand,
                price=p.average_price,
                reason="popular_fallback" if not category_filter else "category_fallback",
            )
        )
    return items
