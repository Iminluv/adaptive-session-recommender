"""Unit tests for the serving repository and recommender service."""

import unittest

from adaptive_recommender.serving.fallbacks import get_popularity_fallback
from adaptive_recommender.serving.repositories import (
    Candidate,
    InMemoryServingRepository,
    ProductStat,
    SessionIntent,
)
from adaptive_recommender.serving.reranker import RecommenderService


class ServingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            ProductStat(product_id=101, category_code="phones", brand="apple", event_count=10, unique_users=5, average_price=999.0, popularity_score=1.0),
            ProductStat(product_id=102, category_code="phones", brand="samsung", event_count=5, unique_users=3, average_price=799.0, popularity_score=0.5),
            ProductStat(product_id=103, category_code="audio", brand="sony", event_count=2, unique_users=2, average_price=199.0, popularity_score=0.2),
        ]
        self.candidates = [
            Candidate(user_id="user-A", rank=1, product_id=102, als_score=0.95),
            Candidate(user_id="user-A", rank=2, product_id=103, als_score=0.80),
            Candidate(user_id="user-A", rank=3, product_id=101, als_score=0.10),
        ]
        self.repo = InMemoryServingRepository(
            candidates=self.candidates,
            products=self.products,
        )
        self.service = RecommenderService(repository=self.repo)

    def test_known_user_returns_als_candidates(self) -> None:
        recs, is_fallback = self.service.get_recommendations("user-A", limit=2)
        self.assertFalse(is_fallback)
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0].product_id, 102)
        self.assertEqual(recs[0].rank, 1)
        self.assertEqual(recs[0].reason, "long_term_preference")
        self.assertAlmostEqual(recs[0].score, 0.95)

    def test_unknown_user_falls_back_to_popularity(self) -> None:
        recs, is_fallback = self.service.get_recommendations("unknown-user", limit=2)
        self.assertTrue(is_fallback)
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0].product_id, 101)  # Highest popularity
        self.assertEqual(recs[0].reason, "popular_fallback")
        self.assertAlmostEqual(recs[0].score, 1.0)

    def test_anonymous_user_falls_back_to_popularity(self) -> None:
        for anon_id in ("", "anonymous", "none", None):
            recs, is_fallback = self.service.get_recommendations(anon_id, limit=3)
            self.assertTrue(is_fallback)
            self.assertEqual(len(recs), 3)
            self.assertEqual(recs[0].product_id, 101)

    def test_category_filter_in_fallback(self) -> None:
        recs = get_popularity_fallback(self.repo, limit=10, category_filter="audio")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].product_id, 103)
        self.assertEqual(recs[0].reason, "category_fallback")

    def test_adaptive_intent_reranking(self) -> None:
        # User-A with strong audio intent
        intents = [SessionIntent(user_id="user-A", user_session="sess-1", category_code="audio", intent_score=1.0)]
        repo_with_intent = InMemoryServingRepository(
            candidates=self.candidates,
            products=self.products,
            session_intents=intents,
        )
        service = RecommenderService(
            repository=repo_with_intent,
            adaptive_enabled=True,
        )
        recs, is_fallback = service.get_recommendations("user-A", limit=3, user_session="sess-1")
        self.assertFalse(is_fallback)
        # Check that score composition incorporates intent
        audio_rec = next(r for r in recs if r.product_id == 103)
        self.assertEqual(audio_rec.reason, "adaptive_session_intent")
        self.assertGreater(audio_rec.score_components["intent"], 0.0)


if __name__ == "__main__":
    unittest.main()
