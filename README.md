# Adaptive Session-Aware Product Recommendation System

This repository contains a university Big Data and Storage project. The contribution rules apply to every milestone and every type of change.

Start with:

1. [Project Rulebook](CONTRIBUTING.md): global branch, commit, review, merge, data, testing, deployment, security, and handoff rules.
2. [Approved Design](docs/designs/adaptive-session-aware-recommender.md): goals, architecture, constraints, and decisions.
3. [Plan1A Implementation Plan](docs/implementation-plan-plan1a.md): implementation waves, contracts, commands, tests, and acceptance gates.
4. [Deferred Work](TODOS.md): intentionally postponed scope.

## Current state

The event contracts and sample fixture are implemented. The Spark batch sample runner is in progress. Development targets the owner's computer; Oracle is optional for later deployment.

## Planned workflow

October history goes through Spark batch and ALS to recommendation candidates and FastAPI serving. November replay and live browser events go through Kafka, Structured Streaming, session intent, Cassandra state, adaptive re-ranking, and the API/minimal web demo.

Use the sample fixture first. Do not run the full dataset or claim production-scale behavior until the sample workflow and evidence gates pass.
