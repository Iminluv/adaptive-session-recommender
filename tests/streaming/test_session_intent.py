"""Unit tests for Spark session intent scoring."""

import unittest
from datetime import datetime, timezone

from pyspark.sql import SparkSession, types as T

from adaptive_recommender.streaming.session_intent import compute_session_intent


class SessionIntentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spark = (
            SparkSession.builder.appName("test-session-intent")
            .master("local[1]")
            .config("spark.sql.session.timeZone", "UTC")
            .getOrCreate()
        )
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.spark.stop()

    def test_session_intent_weights_aggregation(self) -> None:
        schema = T.StructType(
            [
                T.StructField("user_id", T.StringType(), True),
                T.StructField("user_session", T.StringType(), True),
                T.StructField("category_code", T.StringType(), True),
                T.StructField("event_type", T.StringType(), True),
                T.StructField("event_time", T.TimestampType(), True),
            ]
        )
        now = datetime.now(timezone.utc)
        data = [
            ("u1", "s1", "electronics.smartphone", "view", now),
            ("u1", "s1", "electronics.smartphone", "cart", now),
            ("u1", "s1", "electronics.audio", "view", now),
            ("u1", "s1", "electronics.audio", "remove_from_cart", now),  # net negative -> 0.0 intent
        ]
        df = self.spark.createDataFrame(data, schema)
        result = compute_session_intent(df).collect()

        intent_by_cat = {r["category_code"]: r["intent_score"] for r in result}
        self.assertIn("electronics.smartphone", intent_by_cat)
        # raw_score for smartphone = 1 + 4 = 5.0 -> intent_score ~ 0.4621 > 0.4
        self.assertGreater(intent_by_cat["electronics.smartphone"], 0.4)

        # raw_score for audio = 1 - 3 = -2.0 -> intent_score == 0.0
        self.assertEqual(intent_by_cat["electronics.audio"], 0.0)


if __name__ == "__main__":
    unittest.main()
