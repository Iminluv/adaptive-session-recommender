# Adaptive Session-Aware Product Recommendation System

This repository contains a university Big Data and Storage project. The contribution rules apply to every milestone and every type of change.

Start with:

1. [Project Rulebook](CONTRIBUTING.md): global branch, commit, review, merge, data, testing, deployment, security, and handoff rules.
2. [Approved Design](docs/designs/adaptive-session-aware-recommender.md): goals, architecture, constraints, and decisions.
3. [Plan1A Implementation Plan](docs/implementation-plan-plan1a.md): implementation waves, contracts, commands, tests, and acceptance gates.
4. [Deferred Work](TODOS.md): intentionally postponed scope.

## Current state

The canonical event contracts (G1), Spark batch sample runner (G2), and FastAPI recommendation serving baseline with cold-start fallbacks (Wave 3) are implemented and verified against the sample fixture. Development targets the owner's computer; Oracle is optional for later deployment.

## Planned workflow

October history goes through Spark batch and ALS to recommendation candidates and FastAPI serving. November replay and live browser events go through Kafka, Structured Streaming, session intent, Cassandra state, adaptive re-ranking, and the API/minimal web demo.

Use the sample fixture first. Do not run the full dataset or claim production-scale behavior until the sample workflow and evidence gates pass.

## Local setup

Install Java 17 and Python 3.11, then run `make install` once to create `.venv` and install pinned dependencies. Run:
1. `make check` - verify code style and environment
2. `make sample-fixture` - validate deterministic sample data
3. `make test-unit` - run unit and API contract tests
4. `make batch-sample` - execute local Spark batch pipeline (generate Silver Parquet and Gold ALS candidates)
5. `make api-sample` - verify FastAPI recommendation service and cold-start fallbacks
6. `make api-run` - launch FastAPI development server on port 8000

Java is provided by Homebrew on this Mac and can be selected for one command with `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home make batch-sample`.
