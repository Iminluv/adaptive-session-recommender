-- Keyspace and table schemas for adaptive session recommender serving and state layers.

CREATE KEYSPACE IF NOT EXISTS ecommerce
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE ecommerce;

-- Precomputed ALS candidate recommendations from October batch path.
CREATE TABLE IF NOT EXISTS recommendation_candidates (
  user_id text,
  rank int,
  product_id bigint,
  als_score double,
  updated_at timestamp,
  PRIMARY KEY ((user_id), rank)
);

-- Real-time session intent scores aggregated by Structured Streaming.
CREATE TABLE IF NOT EXISTS session_intent (
  user_id text,
  user_session text,
  category_code text,
  intent_score double,
  last_event_time timestamp,
  updated_at timestamp,
  PRIMARY KEY ((user_id, user_session), category_code)
);

-- Catalog product summary statistics and global popularity scores.
CREATE TABLE IF NOT EXISTS product_stats (
  product_id bigint PRIMARY KEY,
  category_code text,
  brand text,
  event_count bigint,
  unique_users bigint,
  average_price double,
  popularity_score double,
  updated_at timestamp
);

-- Final re-ranked recommendations served to active sessions.
CREATE TABLE IF NOT EXISTS live_recommendations (
  user_id text,
  rank int,
  product_id bigint,
  final_score double,
  reason text,
  updated_at timestamp,
  PRIMARY KEY ((user_id), rank)
);
