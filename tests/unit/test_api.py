"""Unit and contract tests for FastAPI recommendation endpoints."""

import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from adaptive_recommender.serving.repositories import (
    Candidate,
    InMemoryServingRepository,
    ProductStat,
)
from api.main import create_app


class ApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = [
            ProductStat(product_id=1001, category_code="electronics.smartphone", brand="samsung", event_count=3, unique_users=2, average_price=499.0, popularity_score=1.0),
            ProductStat(product_id=1002, category_code="electronics.smartphone", brand="apple", event_count=2, unique_users=2, average_price=799.0, popularity_score=0.67),
            ProductStat(product_id=1003, category_code="electronics.audio", brand="sony", event_count=1, unique_users=1, average_price=149.0, popularity_score=0.33),
        ]
        self.candidates = [
            Candidate(user_id="user-1", rank=1, product_id=1002, als_score=0.98),
            Candidate(user_id="user-1", rank=2, product_id=1001, als_score=0.85),
        ]
        self.repo = InMemoryServingRepository(
            candidates=self.candidates,
            products=self.products,
        )
        self.app = create_app(repository=self.repo)
        self.client = TestClient(self.app)

    def test_health_endpoint_healthy(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("storage", data)
        self.assertIn("timestamp", data)

    def test_products_endpoint_success_and_limit(self) -> None:
        resp = self.client.get("/products?limit=2")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["products"]), 2)
        # Should be sorted by popularity (1001 first with pop=1.0)
        self.assertEqual(data["products"][0]["product_id"], 1001)

    def test_products_endpoint_invalid_limit(self) -> None:
        resp = self.client.get("/products?limit=0")
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data["code"], "INVALID_LIMIT")
        self.assertIn("fix", data)
        self.assertIn("request_id", data)

    def test_events_endpoint_valid_event(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "schema_version": 1,
            "event_id": "test-event-123",
            "event_time": now,
            "ingest_time": now,
            "event_type": "view",
            "product_id": 1001,
            "category_id": 2053013555631882655,
            "category_code": "electronics.smartphone",
            "brand": "samsung",
            "price": 499.0,
            "user_id": "520088904",
            "user_session": "session-123",
            "event_source": "browser",
        }
        resp = self.client.post("/events", json=payload)
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertEqual(data["status"], "accepted")
        self.assertEqual(data["event_id"], "test-event-123")

    def test_events_endpoint_invalid_event(self) -> None:
        # Missing required field event_id and negative price
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "schema_version": 1,
            "event_time": now,
            "ingest_time": now,
            "event_type": "invalid_type",
            "product_id": -5,
            "price": -10.0,
            "event_source": "browser",
        }
        resp = self.client.post("/events", json=payload)
        self.assertEqual(resp.status_code, 422)
        data = resp.json()
        self.assertEqual(data["code"], "VALIDATION_FAILED")
        self.assertIn("errors", data)
        self.assertIn("request_id", data)

    def test_recommendations_known_user(self) -> None:
        resp = self.client.get("/recommendations/user-1?limit=2")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["user_id"], "user-1")
        self.assertFalse(data["fallback"])
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["recommendations"][0]["product_id"], 1002)
        self.assertEqual(data["recommendations"][0]["rank"], 1)
        self.assertEqual(data["recommendations"][0]["reason"], "long_term_preference")

    def test_recommendations_unknown_user_fallback(self) -> None:
        resp = self.client.get("/recommendations/unknown-user-999?limit=2")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["user_id"], "unknown-user-999")
        self.assertTrue(data["fallback"])
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["recommendations"][0]["product_id"], 1001)  # Most popular product
        self.assertEqual(data["recommendations"][0]["reason"], "popular_fallback")

    def test_recommendations_invalid_limit(self) -> None:
        resp = self.client.get("/recommendations/user-1?limit=-1")
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertEqual(data["code"], "INVALID_LIMIT")


if __name__ == "__main__":
    unittest.main()
