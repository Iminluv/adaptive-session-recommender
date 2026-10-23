# PROJECT_CONTEXT_V2.md
# Single Source of Truth — Adaptive Session-Aware Product Recommendation System

> This file is the persistent project context for Codex / AI coding agents.
> It supersedes previous project-context drafts.
> Read it before making architectural, data, ML, streaming, storage, API, frontend, benchmark, or deployment decisions.
>
> **Do not silently change fixed decisions.**
> If implementation constraints require a change, surface the conflict first.

---

# 0. Official Project

## Title

**Adaptive Session-Aware Product Recommendation System for E-Commerce Using Batch and Stream Processing**

Vietnamese:

**Hệ thống gợi ý sản phẩm thích ứng theo hành vi phiên truy cập trong thương mại điện tử sử dụng xử lý Batch và Streaming**

## Course emphasis

This is primarily a:

> **Big Data & Storage project**

The recommender is the application layer used to demonstrate:

- large-scale batch processing;
- stream processing;
- distributed storage;
- stateful stream processing;
- Spark optimization;
- system scalability;
- distributed-system benchmarking;
- fault recovery;
- serving architecture.

The system does **not** need to predict user behavior perfectly.

Recommendation quality matters, but the project is **not** an SOTA recommendation research project.

---

# 1. Core Idea

Combine:

1. **Long-term user preference** learned from historical clickstream data.
2. **Short-term session intent** inferred from recent session behavior.

to produce adaptive **Top-K product recommendations**.

Core interpretation:

```text
Batch layer:
"What does this user usually like?"

Streaming layer:
"What is this user interested in right now?"

Serving layer:
"Combine both and return adaptive Top-K recommendations."
```

Example:

```text
Historical:
- laptop
- SSD
- keyboard

Current session:
- click iPhone
- click Samsung phone
- click Xiaomi phone
- add iPhone to cart
```

A static ALS recommender may still favor computers.
The adaptive system should shift recommendations toward smartphones and related products.

---

# 2. Main Project Question

> **How can long-term user preferences and short-term session behavior be combined to generate adaptive product recommendations at large scale using batch and stream processing?**

The goal is not perfect prediction.

The project is successful if it demonstrates:

- a correct end-to-end recommendation pipeline;
- proper Big Data architecture;
- measurable distributed-system behavior;
- reproducible benchmarks;
- adaptive response to session activity.

---

# 3. Dataset

## Dataset family

REES46 multi-category e-commerce clickstream dataset.

Main files:

```text
2019-Oct.csv
2019-Nov.csv
```

Approximate combined scale:

```text
~14.68 GB CSV
>100 million events
```

Expected schema:

```text
event_time
event_type
product_id
category_id
category_code
brand
price
user_id
user_session
```

Typical event types:

```text
view
cart
remove_from_cart
purchase
```

---

# 4. Fixed Data Split

## October 2019

Use for:

- historical batch processing;
- user profiles;
- product/category statistics;
- implicit-feedback generation;
- ALS training;
- Top-N candidate generation;
- batch/storage optimization benchmarks.

## November 2019

Use for:

- chronological held-out evaluation;
- historical clickstream replay;
- Kafka stream simulation;
- load testing;
- throughput benchmark;
- latency benchmark;
- watermark experiments;
- stateful streaming experiments;
- distributed-system scalability tests.

## Live demo web

Use for:

- actual live clickstream at demo time;
- interactive demonstration;
- proving the system reacts to real user actions;
- optional hybrid demo while November replay runs in the background.

---

# 5. Data Leakage Rule — Mandatory

Primary experiment:

```text
TRAIN / HISTORY = October
TEST / STREAM   = November
LIVE DEMO       = newly generated events
```

Do NOT:

```text
train on October + November
then evaluate on November
```

Do NOT use future November events to build features for an earlier November timestamp.

Temporal integrity must be preserved.

---

# 6. Historical Data vs Real-Time Data

The REES46 dataset is historical.

Do NOT claim:

- the source dataset itself is real-time;
- November 2019 is current production traffic;
- all source data are live.

Correct wording:

> Historical clickstream events are replayed through Kafka in event-time order to simulate a streaming workload.

The demo web generates actual live events.

Therefore:

```text
historical replay = simulated stream
demo web interactions = live clickstream
Spark Structured Streaming = real streaming computation
```

---

# 7. Live Event Semantics — Fixed

## view

A `view` event is generated when:

> the user clicks/opens a product.

Do NOT count:

- hover;
- product merely visible;
- scroll;
- passive impression.

## cart

A `cart` event is generated when:

> the user explicitly adds a product to cart.

## remove_from_cart

A `remove_from_cart` event is generated when:

> the user removes a product from the cart.

## purchase

A `purchase` event is generated when:

> checkout is successfully completed/confirmed.

Opening checkout is not enough.

These semantics must be consistent across:

- historical interpretation;
- demo web;
- Kafka schema;
- Spark streaming;
- evaluation.

---

# 8. Product Catalog for Demo Web

Build the demo catalog from the same product universe as REES46.

Use:

```text
product_id
category_id
category_code
brand
price
```

The original `product_id` must remain unchanged.

It is the key joining:

```text
historical interactions
<-> ALS
<-> product statistics
<-> demo web
<-> live events
<-> serving
<-> recommendation output
```

The dataset may not include polished names/images.

UI-only metadata may be generated, e.g.:

```text
Samsung Smartphone #1004856
Apple Smartphone #1005115
```

Images may be placeholders or generic category assets.

UI metadata is cosmetic only.

---

# 9. High-Level Architecture

```text
                         REES46 DATASET
                               |
                +--------------+--------------+
                |                             |
          2019-Oct.csv                  2019-Nov.csv
          BATCH HISTORY                  STREAM TEST
                |                             |
               HDFS                      Replay Producer
                |                             |
           Spark Batch                  Kafka replay topic
                |                             |
      Clean / Transform                       |
                |                             |
        Silver Parquet                        |
                |                             |
      +---------+---------+                   |
      |                   |                   |
User/Product Stats   Implicit Feedback        |
                          |                    |
                     MLlib ALS                 |
                          |                    |
                  Top-N Candidates             |
                          |                    |
                          +---------+          |
                                    v          v
                                  Cassandra <- Spark Structured Streaming
                                    ^                 ^
                                    |                 |
                                    |         +-------+-------+
                                    |         |               |
                                    |     replay stream     live web
                                    |         |               |
                                    +---------+---------------+
                                              |
                                        Session Intent
                                              |
                                           FastAPI
                                              |
                                         Re-ranking
                                              |
                                   Top-K Recommendations
                                              |
                                      React + Vite UI
```

Monitoring:

```text
Prometheus
Grafana
Spark UI
```

Deployment:

```text
Docker Compose first
Kubernetes later
```

---

# 10. Operating Modes

## MODE 1 — Offline Training

```text
October
-> Spark Batch
-> Features
-> ALS
-> Cassandra
```

## MODE 2 — Replay / Load Test

```text
November
-> Replay Producer
-> Kafka
-> Spark Structured Streaming
```

Candidate replay rates:

```text
1,000 events/s
2,500 events/s
5,000 events/s
10,000 events/s
20,000 events/s
```

## MODE 3 — Live Demo

```text
Browser
-> Demo Web
-> Kafka
-> Spark Streaming
-> Session Intent
-> Re-ranking
-> Browser
```

## MODE 4 — Hybrid Demo

Optional but desirable:

```text
November replay in background
            +
live demo clicks
            |
          Kafka
            |
      Spark Streaming
            |
adaptive recommendations
```

---

# 11. Kafka Design

Recommended topics:

```text
ecommerce.replay
ecommerce.live
ecommerce.dlq
```

Recommended message key:

```text
user_id
```

Canonical event schema:

```json
{
  "event_id": "uuid-or-deterministic-id",
  "event_time": "original or live event time",
  "ingest_time": "current ingestion time",
  "event_type": "view|cart|remove_from_cart|purchase",

  "product_id": 1004856,
  "category_id": 2053013555631882655,
  "category_code": "electronics.smartphone",
  "brand": "samsung",
  "price": 499.0,

  "user_id": "520088904",
  "user_session": "session-id",

  "event_source": "historical_replay|live_demo"
}
```

Use `event_id` for:

- deduplication;
- idempotency;
- recovery validation.

---

# 12. Event Time and Ingest Time — Fixed

For historical November replay:

- preserve original 2019 `event_time`;
- add current runtime `ingest_time`.

Use:

```text
event_time
```

for:

- event-time windows;
- session semantics;
- watermark behavior;
- temporal evaluation.

Use:

```text
ingest_time
```

for:

- system latency;
- replay benchmarking;
- processing delay measurements.

Do NOT overwrite historical `event_time` with current time.

---

# 13. Session Definition — Fixed

Historical data:

```text
use dataset user_session
```

Live demo:

```text
generate a compatible live session_id
```

Historical and live session semantics should remain conceptually compatible.

---

# 14. Batch Pipeline

```text
2019-Oct.csv
     |
HDFS Bronze
     |
PySpark Cleaning / Validation
     |
Silver Parquet
     |
     +--> User Profiles
     +--> Product Statistics
     +--> Category Statistics
     +--> Implicit Feedback
                   |
               MLlib ALS
                   |
         Top-50 / Top-100 Candidates
                   |
               Cassandra
```

---

# 15. Storage Layers

## Bronze

Raw historical data:

```text
/data/bronze/ecommerce/
```

## Silver

Cleaned standardized events.

Format:

```text
Parquet
```

Derived fields:

```text
event_date
event_hour
year
month
day
```

Recommended layout:

```text
/data/silver/events/
    year=2019/
        month=10/
            day=01/
            day=02/
```

Do NOT partition by:

```text
user_id
product_id
```

because of high cardinality.

## Gold

Possible outputs:

```text
gold/user_profiles
gold/product_stats
gold/category_stats
gold/implicit_feedback
gold/als_candidates
gold/evaluation
```

---

# 16. Data Quality

Minimum validation:

```text
event_time IS NOT NULL
user_id IS NOT NULL
product_id IS NOT NULL
price >= 0
event_type IN ('view', 'cart', 'remove_from_cart', 'purchase')
```

Inspect:

- duplicates;
- malformed timestamps;
- null brand;
- null category_code;
- schema drift;
- invalid prices;
- unexpected event types.

Streaming:

```text
valid -> main pipeline
invalid -> ecommerce.dlq
```

Do not silently drop bad records.

---

# 17. Implicit Feedback

ALS input:

```text
user_id
product_id
interaction_score
```

Initial weights:

```text
view      = 1
cart      = 3
purchase  = 5
```

`remove_from_cart` should not be fed as a negative ALS score by default.

Preferred:

```text
remove_from_cart
-> negative session signal
```

Weights are configurable.

---

# 18. ALS — Fixed Role

Use:

```text
Spark MLlib ALS
```

ALS represents:

> long-term user preference.

Do NOT retrain ALS after every live click.

Flow:

```text
October historical data
-> ALS
-> Top-50 / Top-100 candidate products
```

Live events affect:

```text
session state
+
session intent
+
re-ranking
```

Possible parameters:

```text
rank
regParam
alpha
maxIter
implicitPrefs
cold-start handling
```

Do not over-tune before the full system works.

---

# 19. Historical User Profile

Candidate features:

```text
total_views
total_carts
total_purchases
total_spending
favorite_category
favorite_brand
average_viewed_price
median_viewed_price
historical_conversion_rate
cart_rate
category_distribution
brand_distribution
activity_frequency
```

---

# 20. Streaming Pipeline

```text
Kafka replay/live
       |
Parse event
       |
Schema validation
       |
       +--> invalid -> DLQ
       |
Deduplication
       |
Watermark / event-time handling
       |
Enrichment
       |
Window / stateful aggregation
       |
Session features
       |
Session intent
       |
Cassandra
```

Important concepts:

- event time;
- ingest time;
- processing time;
- watermark;
- state;
- checkpoint;
- micro-batch;
- late data;
- deduplication;
- restart/recovery.

---

# 21. Session Intent

Start simple.

This is a Big Data & Storage course, not a session-model research paper.

Example:

```text
view iPhone
view iPhone
view Samsung
view Xiaomi
cart iPhone
```

Possible intent:

```text
smartphone = 0.91
audio      = 0.06
computer   = 0.03
```

Initial session weights:

```text
view             +1
repeated view    +2
cart             +4
remove_from_cart -3
purchase         +5
```

Use time decay:

```text
decayed_weight
=
base_weight * exp(-lambda * delta_time)
```

Do not overcomplicate the first implementation.

---

# 22. Session Window Features

Candidate windows:

```text
5 min
15 min
30 min
```

Possible features:

```text
views_last_5m
views_last_30m
cart_count_last_30m
unique_products_last_30m
unique_categories_last_30m
repeat_view_ratio
events_per_minute
minutes_since_last_cart
session_duration
recent_category_distribution
recent_brand_distribution
```

---

# 23. Watermark

Initial candidate:

```text
10 minutes
```

Benchmark:

```text
2 min
5 min
10 min
```

Measure:

- accepted late events;
- dropped late events;
- state size;
- memory;
- latency.

---

# 24. Score Normalization — Important

Before combining:

```text
ALSScore
SessionIntentScore
PopularityScore
BrandPreferenceScore
```

make them comparable.

Possible strategies:

- min-max normalization;
- per-user normalization;
- percentile/rank-based normalization;
- bounded score transformation.

Do NOT blindly add raw scores.

---

# 25. Re-ranking

Base formula:

```text
FinalScore =
    w1 * normalized_ALS
  + w2 * normalized_session_intent
  + w3 * normalized_popularity
  + w4 * normalized_brand_preference
```

Initial candidate weights:

```text
w1 = 0.50
w2 = 0.35
w3 = 0.10
w4 = 0.05
```

These are hypotheses, not fixed truths.

Main hypothesis:

> Session-aware re-ranking adapts faster and can improve recommendation relevance compared with static ALS.

---

# 26. Cold Start — Required

## Known historical user

```text
ALS candidates
+
session re-ranking
```

## New user with current clicks

```text
session intent
+
category popularity
+
trending products
```

## Completely new user

```text
global popularity
or
category popularity if context exists
```

The API must not fail simply because ALS does not know a user.

---

# 27. Demo Persona Strategy

Preferred demo:

1. pick a user known in October;
2. load historical ALS recommendations;
3. presenter browses another category;
4. live clicks go to Kafka;
5. session intent changes;
6. Top-K changes.

This best demonstrates:

```text
long-term preference
+
short-term intent
```

---

# 28. Replay Users vs Demo User

Historical replay and live demo should remain distinguishable.

Recommended:

- replay historical users normally;
- use dedicated demo session/user identity;
- if using historical persona, create a fresh live `user_session`;
- preserve `event_source`.

This supports:

```text
background load
+
clean live demo
```

---

# 29. Cassandra

Use Apache Cassandra as the serving NoSQL store.

Suggested tables:

## recommendation_candidates

```text
user_id
rank
product_id
als_score
updated_at
```

## session_intent

```text
user_id
user_session
category_code
intent_score
updated_at
```

## product_stats

```text
product_id
category_code
brand
popularity_score
trend_score
updated_at
```

Optional:

## live_recommendations

```text
user_id
rank
product_id
final_score
updated_at
```

Model Cassandra around access patterns.

---

# 30. Consistency Model — Fixed

Strong transactional consistency is not required for recommendation serving.

Accept:

> **eventual consistency**

A recommendation update may appear after a small delay.

Do not introduce unnecessary distributed transaction complexity.

---

# 31. Idempotency / Exactly-Once Caution

Do NOT casually claim:

> end-to-end exactly-once

Kafka + Spark checkpointing does not automatically guarantee exactly-once semantics for every Cassandra write pattern.

Instead:

- use `event_id`;
- deduplicate;
- use deterministic/upsert-friendly keys;
- test restart behavior;
- measure duplicates/loss.

Only claim exactly-once if experimentally and architecturally justified.

---

# 32. FastAPI

Responsibilities:

- product/catalog API;
- live event ingestion;
- recommendation API;
- Cassandra access;
- re-ranking;
- health/metrics endpoints.

Minimum endpoints:

```text
GET  /products
GET  /products/{product_id}
POST /events
GET  /recommendations/{user_id}
```

Optional:

```text
GET /users/{user_id}/intent
GET /health
GET /metrics
```

Do not invoke Spark jobs directly for every web request.

---

# 33. Demo Web

Use:

```text
React + Vite
```

Required:

```text
Home / Product Listing
Product Detail
Cart
Recommended For You
Current Session Intent
Recent Events (optional)
```

Generated events:

```text
click/open product  -> view
add to cart         -> cart
remove item         -> remove_from_cart
successful checkout -> purchase
```

Not required:

- real payments;
- shipping;
- seller portal;
- admin CMS;
- coupons;
- full-text search;
- complex authentication.

Goal:

> prove end-to-end system behavior.

---

# 34. Demo Scope — Fixed

The web is not the main project.

It only needs to:

- display dataset-backed products;
- generate live clickstream;
- display adaptive recommendations;
- optionally show session intent.

---

# 35. Tech Stack — Fixed Baseline

| Layer | Technology | Role |
|---|---|---|
| Core language | Python | data / producer / backend |
| Distributed compute | Apache Spark / PySpark | batch |
| Streaming | Spark Structured Streaming | stream processing |
| ML | Spark MLlib ALS | long-term candidates |
| Broker | Apache Kafka | replay + live stream |
| Distributed storage | HDFS | raw/history |
| Analytical format | Parquet | optimized analytics |
| Serving database | Apache Cassandra | state/candidates |
| Backend | FastAPI | API/re-ranking |
| Frontend | React + Vite | demo |
| Monitoring | Prometheus | metrics |
| Monitoring UI | Grafana | dashboards |
| Profiling | Spark UI | diagnostics |
| Local orchestration | Docker Compose | development |
| Final orchestration | Kubernetes | scaling/demo |
| Version control | Git + GitHub | source control |

Avoid adding:

```text
Flink
MongoDB
Redis
Elasticsearch
Airflow
```

unless a real requirement appears.

---

# 36. Spark Coursework Mapping

Use:

- complex aggregation;
- window functions;
- pivot;
- native Spark transformations;
- multi-stage Bronze -> Silver -> Gold;
- Broadcast Join;
- Sort-Merge Join;
- partition pruning;
- caching/persistence;
- AQE;
- skew handling.

Prefer native Spark SQL functions over Python UDFs where possible.

---

# 37. Benchmark Framework — Important

A benchmark must follow:

```text
fixed workload
-> change one controlled factor
-> measure metrics
-> compare
```

Do not change many variables at once.

---

# 38. Benchmark Family 1 — Recommendation Quality

Compare:

```text
Popularity baseline
ALS
ALS + Session-Aware Re-ranking
```

Metrics:

```text
HitRate@K
Recall@K
NDCG@K
optional MRR@K
```

Recommended:

```text
K = 5
K = 10
optional K = 20
```

Primary metric:

```text
NDCG@10
```

---

# 39. Purchase Hit Rate

Use:

```text
Purchase HitRate@K
```

Question:

> Before purchase, is the purchased item already in Top-K?

---

# 40. Time-to-Adapt — Project-Specific Benchmark

Definition:

> Number of new session events required before a newly dominant interest/category appears meaningfully in Top-K.

Compare:

```text
Static ALS
vs
ALS + Session-Aware Re-ranking
```

This directly proves the word:

> Adaptive

---

# 41. Benchmark Family 2 — Distributed System

This answers:

> How well does the distributed system behave as workload and resources change?

Focus on:

```text
throughput
latency
scalability
Kafka lag
resource utilization
fault recovery
shuffle
I/O
state size
```

---

# 42. Throughput Benchmark

Replay rates:

```text
1k
2.5k
5k
10k
20k events/s
```

Capture:

```text
input rate
Spark processing rate
Kafka lag
```

Find saturation point.

Saturation:

```text
input rate > sustained processing rate
and
Kafka lag keeps growing
```

---

# 43. Streaming Latency — Separate Metric

Measure:

```text
Kafka ingestion
->
Spark state/result available
```

Report:

```text
P50
P95
P99
```

Do not report average only.

---

# 44. End-to-End Application Latency — Separate Metric

Measure:

```text
browser click
-> event accepted
-> Kafka
-> Spark
-> Cassandra
-> FastAPI
-> recommendation rendered
```

Keep this separate from pure streaming latency.

---

# 45. Throughput vs Latency

Main graph:

```text
x-axis = input events/s
y-axis = P95/P99 latency
```

At saturation:

```text
latency rises sharply
Kafka lag grows
```

---

# 46. Scalability

Test:

```text
1 executor
2 executors
4 executors
8 executors
```

Measure:

```text
throughput
P95 latency
CPU
memory
executor utilization
```

---

# 47. Strong Scaling

Keep workload fixed.

Increase resources.

Question:

> How much faster does the same workload run?

---

# 48. Weak Scaling

Increase workload together with resources.

Example:

```text
1 executor -> 2.5k events/s
2 executors -> 5k events/s
4 executors -> 10k events/s
8 executors -> 20k events/s
```

Question:

> Does latency stay reasonably stable?

---

# 49. Speedup and Efficiency

```text
Speedup(N) = T1 / TN
Efficiency(N) = Speedup(N) / N
```

Use for batch/distributed scaling analysis.

---

# 50. Kafka Lag

Interpretation:

```text
lag grows continuously
-> system cannot sustain input rate

lag spikes then returns to zero
-> system can catch up
```

---

# 51. Resource Efficiency

Measure:

```text
CPU
RAM
network
disk I/O
shuffle
```

Optional:

```text
throughput per executor
```

Do not assume "more executors = automatically best".

---

# 52. Benchmark Family 3 — Spark Optimization

## Storage

Compare:

```text
CSV
Parquet
Partitioned Parquet
```

Measure:

```text
runtime
bytes read
scan size
CPU
```

## Partition pruning

Same date-filtered query:

```text
non-partitioned
vs
date-partitioned Parquet
```

## Join

Compare:

```text
SortMergeJoin
vs
BroadcastHashJoin
```

Measure:

```text
runtime
shuffle read/write
max task duration
```

Inspect:

```python
df.explain("formatted")
```

## Data skew

Compare:

```text
default
AQE skew handling
salting if needed
```

Measure:

```text
runtime
max task duration
median task duration
shuffle spill
partition imbalance
```

## Cache

Compare:

```text
no cache
cache()
persist(MEMORY_AND_DISK)
```

Only for reused DataFrames.

---

# 53. Watermark Benchmark

Compare:

```text
2 min
5 min
10 min
```

Measure:

```text
late events accepted
late events dropped
state size
memory
latency
```

---

# 54. Fault Recovery Benchmark

Procedure:

```text
1. start streaming
2. process known events
3. kill Spark streaming job
4. restart from checkpoint
5. continue
6. validate output
```

Measure:

```text
recovery time
lost events
duplicate outputs
Kafka lag recovery
```

---

# 55. Benchmark Priorities

If time is limited, prioritize:

## Recommendation
1. Popularity vs ALS vs Session-Aware
2. NDCG@10
3. HitRate@10
4. Time-to-Adapt
5. Purchase HitRate@10 if feasible

## Distributed system
1. input rate vs P95/P99 latency
2. Kafka lag
3. 1/2/4/8 executor scaling
4. CSV vs Parquet/partitioning
5. Broadcast vs SortMerge
6. fault recovery if time permits

Reminder:

This is a Big Data & Storage project.

Do not spend disproportionate time chasing tiny recommender metric gains.

---

# 56. Pre-Code Check — Required

Before major infrastructure coding, inspect October/November overlap.

Measure:

```text
user overlap
product overlap
category overlap
brand overlap
```

Especially:

```text
users in November also seen in October
products in November also seen in October
```

Reason:

ALS cannot directly score unknown users/products.

Cold-start severity must be measured, not guessed.

---

# 57. Pre-Code Data Profiling

Before infrastructure:

```text
1. schema validation
2. row counts
3. event type distribution
4. null distribution
5. user cardinality
6. product cardinality
7. category cardinality
8. user_session cardinality
9. user overlap Oct/Nov
10. product overlap Oct/Nov
11. category overlap Oct/Nov
12. skew analysis
```

Write findings to:

```text
docs/dataset.md
```

---

# 58. Small Sample Dataset — Required

Create:

```text
data/sample/
```

Use for:

- local development;
- Codex iteration;
- unit/integration tests;
- fast Spark experiments;
- API/frontend integration.

Modes:

```text
DEV MODE  -> sample data
FULL MODE -> full October/November data
```

---

# 59. Configuration — Fixed Principle

Externalize:

```text
Kafka bootstrap servers
Kafka topic names
replay rate
HDFS paths
checkpoint paths
Cassandra hosts
ALS hyperparameters
session windows
watermark
interaction weights
ranking weights
Top-K
Top-N candidates
```

Use `.env`, config files, or typed settings.

Provide:

```text
.env.example
```

---

# 60. Infrastructure Order — Fixed

Do NOT start by building Kubernetes.

Preferred order:

```text
1. data understanding
2. sample data
3. batch pipeline
4. ALS baseline
5. minimal serving
6. Kafka replay
7. Spark streaming
8. session intent
9. re-ranking
10. live web
11. benchmarks
12. monitoring
13. Docker Compose hardening
14. Kubernetes
```

---

# 61. Vertical-Slice Development

First slice:

```text
October sample
-> Spark clean
-> implicit interactions
-> ALS
-> Top-N candidates
-> FastAPI
```

Second slice:

```text
web click
-> Kafka
-> Spark Streaming
-> session intent
-> Cassandra
-> FastAPI re-ranking
-> web update
```

Do not build many half-working services before one end-to-end path works.

---

# 62. Demo vs Evaluation

Live demo clicks are for:

```text
demonstration
integration
interactive proof
```

They are NOT the primary evaluation dataset.

Main reproducible evaluation:

```text
October train
November temporal test
```

---

# 63. Latency Measurement Contract

Maintain explicit timestamps.

For historical replay:

```text
event_time
ingest_time
processed_time
served_time if needed
```

Streaming latency:

```text
processed_time - ingest_time
```

End-to-end latency:

```text
browser_render_time - browser_click_time
```

Do not use historical 2019 `event_time` to calculate current system latency.

---

# 64. Definition of Done — Fixed

The project is not complete just because the website displays recommendations.

Minimum completion criteria:

1. October batch pipeline works.
2. HDFS storage works.
3. Silver Parquet exists.
4. ALS baseline works.
5. Top-N candidates are generated.
6. November replay producer works.
7. Kafka replay topic works.
8. Live Kafka topic works.
9. Spark Structured Streaming works.
10. Session intent works.
11. Cassandra serving state works.
12. Adaptive re-ranking works.
13. FastAPI serving works.
14. Minimal React/Vite demo works.
15. Live demo clickstream works.
16. Cold-start fallback works.
17. Recommendation benchmark exists.
18. Spark optimization benchmark exists.
19. Distributed-system benchmark exists.
20. Streaming latency and end-to-end latency are measured separately.
21. Recovery behavior is documented/tested where feasible.
22. Reproduction commands/documentation exist.

---

# 65. Recommended Repository Structure

```text
project-root/
|
|-- README.md
|-- PROJECT_CONTEXT_V2.md
|-- AGENTS.md
|-- .env.example
|-- docker-compose.yml
|
|-- data/
|   |-- sample/
|   |-- schemas/
|   |-- catalog/
|
|-- producer/
|   |-- replay_producer.py
|   |-- replay_config.py
|   |-- event_schema.py
|
|-- spark/
|   |-- batch/
|   |   |-- ingest_bronze.py
|   |   |-- build_silver.py
|   |   |-- build_user_profiles.py
|   |   |-- build_product_stats.py
|   |   |-- build_interactions.py
|   |   |-- train_als.py
|   |   |-- generate_candidates.py
|   |
|   |-- streaming/
|   |   |-- stream_events.py
|   |   |-- session_features.py
|   |   |-- session_intent.py
|   |   |-- sinks.py
|   |
|   |-- common/
|       |-- config.py
|       |-- schemas.py
|       |-- transforms.py
|       |-- utils.py
|
|-- serving/
|   |-- api/
|   |   |-- main.py
|   |   |-- routes/
|   |   |-- recommender.py
|   |   |-- ranking.py
|   |   |-- cassandra_client.py
|   |   |-- catalog_service.py
|
|-- frontend/
|   |-- package.json
|   |-- src/
|       |-- pages/
|       |-- components/
|       |-- api/
|       |-- hooks/
|       |-- state/
|
|-- evaluation/
|   |-- metrics.py
|   |-- temporal_eval.py
|   |-- purchase_hit_eval.py
|   |-- adaptation_eval.py
|
|-- benchmarks/
|   |-- storage_benchmark.py
|   |-- join_benchmark.py
|   |-- skew_benchmark.py
|   |-- cache_benchmark.py
|   |-- streaming_load_test.py
|   |-- scaling_benchmark.py
|   |-- watermark_benchmark.py
|   |-- recovery_test.py
|
|-- infra/
|   |-- kafka/
|   |-- spark/
|   |-- hdfs/
|   |-- cassandra/
|   |-- prometheus/
|   |-- grafana/
|   |-- k8s/
|
|-- tests/
|   |-- unit/
|   |-- integration/
|
|-- docs/
    |-- architecture.md
    |-- dataset.md
    |-- benchmark-plan.md
    |-- experiments.md
    |-- demo.md
```

---

# 66. Implementation Phases

## Phase 0 — Preflight
- profile data;
- measure Oct/Nov overlap;
- inspect skew;
- create sample dataset;
- freeze event schema.

## Phase 1 — Batch ETL
- ingest October;
- Bronze;
- Silver;
- Parquet;
- validation.

## Phase 2 — Historical Analytics
- user profiles;
- product stats;
- category stats;
- windows;
- pivots;
- joins.

## Phase 3 — ALS
- interaction weighting;
- train ALS;
- generate candidates;
- basic evaluation.

## Phase 4 — Serving Baseline
- Cassandra;
- FastAPI;
- return static candidates.

## Phase 5 — Replay Streaming
- replay producer;
- Kafka topics;
- configurable rate;
- Structured Streaming.

## Phase 6 — Session Intent
- event-time logic;
- watermark;
- state;
- time decay;
- Cassandra state sink.

## Phase 7 — Adaptive Ranking
- normalization;
- re-ranking;
- cold start.

## Phase 8 — Demo Web
- catalog;
- detail;
- cart;
- checkout;
- live events;
- recommendation display.

## Phase 9 — Evaluation
- Popularity;
- ALS;
- Session-aware;
- NDCG;
- HitRate;
- Time-to-Adapt;
- Purchase HitRate if feasible.

## Phase 10 — Performance Benchmarks
- storage;
- partition pruning;
- joins;
- skew;
- cache;
- throughput;
- latency;
- scaling;
- watermark;
- recovery.

## Phase 11 — Monitoring / Deployment
- Prometheus;
- Grafana;
- Docker Compose;
- Kubernetes last.

---

# 67. MUST / SHOULD / NICE TO HAVE

## MUST HAVE
- October batch processing;
- HDFS;
- Parquet;
- Spark Batch;
- ALS;
- Top-N candidates;
- November replay;
- Kafka;
- Spark Structured Streaming;
- session intent;
- Cassandra;
- FastAPI;
- React/Vite demo;
- live clickstream;
- adaptive re-ranking;
- cold-start fallback;
- recommendation benchmark;
- distributed-system benchmark;
- Spark optimization benchmark.

## SHOULD HAVE
- Prometheus;
- Grafana;
- AQE;
- skew handling;
- recovery demo;
- Docker Compose.

## NICE TO HAVE
- Kubernetes scale demo;
- hybrid replay + live demo;
- richer frontend;
- advanced tuning;
- GraphFrames.

---

# 68. Non-Goals

This project is not primarily:

- a production marketplace;
- payment system;
- inventory system;
- cart-rescue system;
- deep-learning recommender;
- reinforcement-learning system;
- full MLOps platform;
- search engine;
- marketing automation platform.

Main focus:

```text
Big Data Engineering
+
Storage
+
Batch Processing
+
Stream Processing
+
Distributed System Benchmarking
+
Adaptive Recommendation
```

---

# 69. Codex Rules

1. Read this file before large changes.
2. Preserve October=train/history.
3. Preserve November=test/replay.
4. Preserve original `product_id`.
5. Preserve fixed event semantics.
6. Keep replay and live events distinguishable.
7. Keep original replay `event_time`; add current `ingest_time`.
8. Do not retrain ALS per click.
9. Cold-start fallback is mandatory.
10. Normalize scores before re-ranking.
11. Do not expand frontend scope.
12. Do not silently replace Spark/Kafka/Cassandra/ALS/FastAPI/React.
13. Do not fabricate benchmark results.
14. Do not claim exactly-once without proof.
15. Keep streaming latency and end-to-end latency separate.
16. Prefer correctness before optimization.
17. Prefer vertical slices before infrastructure complexity.
18. Update docs/config/tests when interfaces change.

---

# 70. Codex Start-of-Task Checklist

Before changing code:

```text
1. Which project layer am I changing?
2. Does this preserve October=train?
3. Does this preserve November=test/replay?
4. Does this preserve product_id?
5. Does this preserve event semantics?
6. Does this change Kafka schema?
7. Does this introduce data leakage?
8. Does this affect score normalization?
9. Does this affect benchmark validity?
10. Is this MUST / SHOULD / NICE TO HAVE?
11. Do docs/config/tests need updates?
```

---

# 71. Codex End-of-Task Checklist

After a substantial task:

```text
1. List files changed.
2. Explain behavior changed.
3. Explain how to run/test.
4. State assumptions.
5. State limitations.
6. Do not claim tests passed unless they ran.
7. Update this context if architecture changes.
8. Update README/docs/config if needed.
```

---

# 72. Fixed Decisions Log

## D001 — Project focus
Final: Big Data & Storage first; recommender does not need perfect prediction.

## D002 — Topic
Final: Adaptive Session-Aware Product Recommendation System for E-Commerce Using Batch and Stream Processing.

## D003 — Dataset split
Final: October=train/history, November=test/replay.

## D004 — Dual stream source
Final: historical replay + actual live web clickstream.

## D005 — Event semantics
Final:
```text
view = click/open product
cart = add to cart
remove_from_cart = remove product
purchase = successful checkout
```

## D006 — Session
Final: historical `user_session`, compatible live `session_id`.

## D007 — Canonical event schema
Final baseline:
```text
event_id
event_time
ingest_time
event_type
product_id
category_id
category_code
brand
price
user_id
user_session
event_source
```

## D008 — Product IDs
Final: never replace dataset `product_id`.

## D009 — ALS role
Final: offline long-term recommender only; no per-click retraining.

## D010 — Session intent
Final: simple weighted events + time decay first.

## D011 — Cold start
Final: fallback required.

## D012 — Score normalization
Final: normalize components before weighted re-ranking.

## D013 — Demo scope
Final: simple web only; prove end-to-end operation.

## D014 — Main evaluation
Final: November temporal evaluation; live clicks are demo data.

## D015 — Benchmark
Final: use recommendation + Spark optimization + distributed-system benchmarks in this file.

## D016 — Latency
Final: streaming latency and end-to-end application latency measured separately.

## D017 — Consistency
Final: eventual consistency acceptable.

## D018 — Exactly-once
Final: do not overclaim; use event IDs, idempotent/upsert design, recovery tests.

## D019 — Replay timestamps
Final: keep original historical `event_time`, add current `ingest_time`.

## D020 — Replay/demo isolation
Final: background replay and demo user must remain distinguishable.

## D021 — Infrastructure order
Final: Docker Compose first, Kubernetes later.

## D022 — Development data
Final: create small sample dataset.

## D023 — Configuration
Final: externalize configurable parameters.

## D024 — Definition of Done
Final: use the full minimum criteria in section 64.

---

# 73. Pre-Code Action List

Before major coding:

```text
1. inspect October schema
2. inspect November schema
3. count event types
4. count users
5. count products
6. count categories
7. count sessions
8. calculate Oct/Nov user overlap
9. calculate Oct/Nov product overlap
10. calculate category overlap
11. inspect nulls
12. inspect data skew
13. create sample dataset
14. freeze canonical event schema
15. document findings
```

Only then begin the full batch implementation.

---

# 74. First Implementation Slice

Recommended first working slice:

```text
October sample
   |
Spark clean
   |
implicit interactions
   |
ALS
   |
Top-N candidates
   |
FastAPI
   |
return recommendation
```

Second slice:

```text
live web click
   |
Kafka
   |
Spark Streaming
   |
Session Intent
   |
Cassandra
   |
FastAPI re-ranking
   |
Web recommendation update
```

---

# 75. Final Report Narrative

Do not frame the report as:

> We used Spark because the data are large.

Preferred framing:

> Historical recommendation preferences may become stale during a browsing session. The system separates long-term preference learning from short-term session-intent processing. Historical October data are processed in batch with Spark and used to generate ALS candidates. November events are replayed through Kafka to evaluate and benchmark streaming behavior, while a lightweight web application produces actual live clickstream events. Spark Structured Streaming maintains recent session state, and a serving layer combines long-term candidates with short-term intent to produce adaptive recommendations. The project is evaluated both as a recommendation application and as a distributed Big Data system.

---

# 76. Final Benchmark Story

## Recommendation

```text
Popularity
vs
ALS
vs
ALS + Session-Aware Re-ranking
```

using:

```text
NDCG@10
HitRate@10
Time-to-Adapt
Purchase HitRate@10 if feasible
```

## Spark optimization

```text
CSV
vs
Parquet
vs
Partitioned Parquet

SortMerge
vs
Broadcast

Default
vs
AQE/skew optimization
```

## Distributed system

```text
Input events/s
vs
P95/P99 latency

Kafka lag

1/2/4/8 executor scaling

Fault recovery if feasible
```

---

# 77. Final One-Sentence Summary

> Build a scalable e-commerce recommendation system that learns long-term preferences from historical clickstream data and adapts recommendations using both replayed and live session-level events, while primarily demonstrating Big Data storage, batch processing, streaming, scalability, and distributed-system performance.

---

# END OF PROJECT CONTEXT V2
