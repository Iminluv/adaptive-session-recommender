# Adaptive Session-Aware Product Recommendation System

This repository contains a university Big Data and Storage project. The contribution rules apply to every milestone and every type of change.

Start with:

1. [Project Rulebook](CONTRIBUTING.md): global branch, commit, review, merge, data, testing, deployment, security, and handoff rules.
2. [Approved Design](docs/designs/adaptive-session-aware-recommender.md): goals, architecture, constraints, and decisions.
3. [Plan1A Implementation Plan](docs/implementation-plan-plan1a.md): implementation waves, contracts, commands, tests, and acceptance gates.
4. [Deferred Work](TODOS.md): intentionally postponed scope.

## Current state

- **Milestone Gate G1 (Complete)**: Batch pipeline generates Silver Parquet and Gold ALS candidates from historical events; FastAPI baseline serves ALS recommendations with cold-start fallbacks.
- **Milestone Gate G2 (Complete)**: Full streaming vertical slice implemented and verified:
  - Local Kafka (KRaft 3.7.0) and Cassandra (4.1) orchestrated via Docker Compose.
  - Deterministic Kafka replay producer with rate limiting and manifest tracking.
  - Spark Structured Streaming pipeline with watermarking (10m), deduplication, DLQ routing for malformed events, and micro-batch Cassandra sink.
  - Cassandra serving repository with real-time adaptive re-ranking (ALS 60% + Session Intent 25% + Popularity 10%).
  - Minimal React + Vite web demo UI with interactive persona switching, clickstream emission, and live shelf updates.
  - End-to-end automation (`make e2e-sample`) verifying rank elevation, DLQ isolation, and capturing evidence to `evidence/commands/e2e-sample.txt`.

## Planned workflow

October history goes through Spark batch and ALS to recommendation candidates and FastAPI serving. November replay and live browser events go through Kafka, Structured Streaming, session intent, Cassandra state, adaptive re-ranking, and the API/minimal web demo.

Use the sample fixture first. Do not run the full dataset or claim production-scale behavior until the sample workflow and evidence gates pass.

## Local setup and runbook

Install Java 17 and Python 3.11, then run `make install` once to create `.venv` and install pinned dependencies.

### Verification & Batch Workflow
1. `make check` - verify code style and git cleanliness
2. `make sample-fixture` - validate deterministic sample data
3. `make test-unit` - run unit and API contract tests
4. `make batch-sample` - execute local Spark batch pipeline (generate Silver Parquet and Gold ALS candidates)

### Streaming & Infrastructure Workflow (Gate G2)
5. `make up` - start Kafka (KRaft mode on `localhost:9092`) and Cassandra (`localhost:9042`) containers
6. `make seed-cassandra` - initialize Cassandra tables and seed with Gold candidates and product stats
7. `make replay-sample RATE=50` - replay events into Kafka topic `ecommerce.replay`
8. `make stream-sample` - execute Spark Structured Streaming job (aggregates session intent to Cassandra and routes bad records to DLQ)
9. `make e2e-sample` - execute complete end-to-end verification (asserts live rank elevation, DLQ routing, and records evidence)

### Serving & Web Demo UI
10. `make api-run` - launch FastAPI development server on port 8000
11. `make ui-build` - build React/Vite production bundle
12. `make ui-dev` - launch Vite development server on port 5173
13. `make down` - stop Docker containers

Java is provided by Homebrew on this Mac and can be selected for one command with `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home make batch-sample`.
