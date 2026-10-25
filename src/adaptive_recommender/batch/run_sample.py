"""Run the small October Spark batch path and emit reproducible artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from pyspark.ml.feature import StringIndexer
from pyspark.ml.recommendation import ALS
from pyspark.sql import SparkSession, Window, functions as F, types as T


EVENT_SCHEMA = T.StructType(
    [
        T.StructField("schema_version", T.IntegerType(), True),
        T.StructField("event_id", T.StringType(), True),
        T.StructField("event_time", T.TimestampType(), True),
        T.StructField("ingest_time", T.TimestampType(), True),
        T.StructField("event_type", T.StringType(), True),
        T.StructField("product_id", T.LongType(), True),
        T.StructField("category_id", T.LongType(), True),
        T.StructField("category_code", T.StringType(), True),
        T.StructField("brand", T.StringType(), True),
        T.StructField("price", T.DoubleType(), True),
        T.StructField("user_id", T.StringType(), True),
        T.StructField("user_session", T.StringType(), True),
        T.StructField("event_source", T.StringType(), True),
    ]
)

EVENT_TYPES = ("view", "cart", "remove_from_cart", "purchase")
INTERACTION_WEIGHTS = {"view": 1.0, "cart": 3.0, "purchase": 5.0}


def git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def config_hash() -> str:
    encoded = json.dumps(
        {"weights": INTERACTION_WEIGHTS, "als_rank": 4, "als_max_iter": 5},
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_sample(input_path: Path, output_root: Path) -> dict:
    started = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    spark = (
        SparkSession.builder.appName("adaptive-recommender-batch-sample")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    raw = spark.read.schema(EVENT_SCHEMA).json(str(input_path))
    valid_condition = F.coalesce(
        (
        F.col("schema_version").eqNullSafe(1)
        & F.col("event_id").isNotNull()
        & (F.length(F.trim(F.col("event_id"))) > 0)
        & F.col("event_time").isNotNull()
        & F.col("ingest_time").isNotNull()
        & F.col("event_source").isNotNull()
        & (F.length(F.trim(F.col("event_source"))) > 0)
        & F.col("event_type").isin(*EVENT_TYPES)
        & (F.col("product_id") > 0)
        & (F.col("price").isNull() | (F.col("price") >= 0))
        & (F.col("event_time") <= F.col("ingest_time"))
        ),
        F.lit(False),
    )
    classified = raw.withColumn(
        "quality_error",
        F.when(F.col("schema_version").isNull(), "missing_schema_version")
        .when(F.col("schema_version") != 1, "unsupported_schema_version")
        .when(F.col("event_id").isNull() | (F.length(F.trim(F.col("event_id"))) == 0), "missing_event_id")
        .when(F.col("event_time").isNull(), "missing_or_invalid_event_time")
        .when(F.col("ingest_time").isNull(), "missing_or_invalid_ingest_time")
        .when(F.col("event_source").isNull() | (F.length(F.trim(F.col("event_source"))) == 0), "missing_event_source")
        .when(F.col("event_type").isNull() | ~F.col("event_type").isin(*EVENT_TYPES), "invalid_event_type")
        .when(F.col("product_id").isNull() | (F.col("product_id") <= 0), "invalid_product_id")
        .when(F.col("price").isNotNull() & (F.col("price") < 0), "negative_price")
        .when(F.col("event_time") > F.col("ingest_time"), "event_time_after_ingest_time"),
    )
    invalid = classified.filter(~valid_condition)
    valid = classified.filter(valid_condition).drop("quality_error")

    # Keep October history only. November remains held out for evaluation/replay.
    october = valid.filter(
        (F.year("event_time") == 2019) & (F.month("event_time") == 10)
    )
    october_input_count = october.count()
    invalid_count = invalid.count()
    duplicate_count = october_input_count - october.dropDuplicates(["event_id"]).count()
    deduped = october.dropDuplicates(["event_id"])
    silver_path = output_root / "silver" / "events"
    (
        deduped.withColumn("year", F.year("event_time"))
        .withColumn("month", F.month("event_time"))
        .withColumn("day", F.dayofmonth("event_time"))
        .write.mode("overwrite")
        .partitionBy("year", "month", "day")
        .parquet(str(silver_path))
    )

    invalid_path = output_root / "quality" / "invalid_events"
    invalid.write.mode("overwrite").parquet(str(invalid_path))

    silver = spark.read.parquet(str(silver_path))
    product_stats = (
        silver.groupBy("product_id", "category_code", "brand")
        .agg(
            F.count(F.lit(1)).alias("event_count"),
            F.countDistinct("user_id").alias("unique_users"),
            F.avg("price").alias("average_price"),
        )
    )
    product_stats_path = output_root / "gold" / "product_stats"
    product_stats.write.mode("overwrite").parquet(str(product_stats_path))

    positive = silver.filter(F.col("user_id").isNotNull() & F.col("event_type").isin(*INTERACTION_WEIGHTS))
    weight_expr = F.when(F.col("event_type") == "view", F.lit(INTERACTION_WEIGHTS["view"]))
    weight_expr = weight_expr.when(F.col("event_type") == "cart", F.lit(INTERACTION_WEIGHTS["cart"]))
    weight_expr = weight_expr.when(F.col("event_type") == "purchase", F.lit(INTERACTION_WEIGHTS["purchase"]))
    feedback = positive.withColumn("weight", weight_expr)
    interactions = feedback.groupBy("user_id", "product_id").agg(F.sum("weight").alias("rating"))
    interactions_path = output_root / "gold" / "implicit_feedback"
    interactions.write.mode("overwrite").parquet(str(interactions_path))

    users_indexer = StringIndexer(inputCol="user_id", outputCol="user_idx", handleInvalid="skip").fit(interactions)
    products_indexer = StringIndexer(inputCol="product_id", outputCol="product_idx", handleInvalid="skip").fit(interactions)
    indexed = products_indexer.transform(users_indexer.transform(interactions))
    train = indexed.select(
        F.col("user_idx").cast("int").alias("user_idx"),
        F.col("product_idx").cast("int").alias("product_idx"),
        F.col("rating").cast("float").alias("rating"),
    )
    als = ALS(
        userCol="user_idx",
        itemCol="product_idx",
        ratingCol="rating",
        implicitPrefs=True,
        rank=4,
        maxIter=5,
        regParam=0.1,
        alpha=1.0,
        coldStartStrategy="drop",
        seed=42,
    )
    model = als.fit(train)
    user_map = spark.createDataFrame(
        [(i, label) for i, label in enumerate(users_indexer.labels)],
        T.StructType([T.StructField("user_idx", T.IntegerType()), T.StructField("user_id", T.StringType())]),
    )
    product_map = spark.createDataFrame(
        [(i, int(label)) for i, label in enumerate(products_indexer.labels)],
        T.StructType([T.StructField("product_idx", T.IntegerType()), T.StructField("product_id", T.LongType())]),
    )
    candidate_rows = (
        model.recommendForAllUsers(50)
        .select("user_idx", F.explode("recommendations").alias("rec"))
        .select("user_idx", F.col("rec.product_idx").alias("product_idx"), F.col("rec.rating").alias("als_score"))
        .join(user_map, "user_idx")
        .join(product_map, "product_idx")
    )
    rank_window = Window.partitionBy("user_id").orderBy(F.desc("als_score"), F.asc("product_id"))
    candidates = candidate_rows.withColumn("rank", F.row_number().over(rank_window)).select(
        "user_id", "rank", "product_id", "als_score"
    )
    candidates_path = output_root / "gold" / "als_candidates"
    candidates.write.mode("overwrite").parquet(str(candidates_path))

    output_count = spark.read.parquet(str(silver_path)).count()
    candidate_count = spark.read.parquet(str(candidates_path)).count()
    finished = datetime.now(timezone.utc)
    manifest = {
        "run_id": started.strftime("%Y%m%dT%H%M%S%fZ"),
        "git_commit": git_revision(),
        "config_hash": config_hash(),
        "input_path": str(input_path),
        "october_input_rows_before_dedup": october_input_count,
        "invalid_rows": invalid_count,
        "duplicate_rows_removed": duplicate_count,
        "silver_rows_after_dedup": output_count,
        "candidate_rows": candidate_count,
        "silver_path": str(silver_path),
        "invalid_path": str(invalid_path),
        "product_stats_path": str(product_stats_path),
        "implicit_feedback_path": str(interactions_path),
        "candidates_path": str(candidates_path),
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "elapsed_seconds": round(time.monotonic() - started_clock, 3),
        "als": {"rank": 4, "max_iter": 5, "implicit_prefs": True, "seed": 42},
    }
    manifest_path = output_root / "manifests" / f"batch-{manifest['run_id']}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    spark.stop()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_sample(args.input, args.output)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

