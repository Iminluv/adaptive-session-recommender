"""FastAPI HTTP service for serving recommendations and accepting events."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from adaptive_recommender.common.validation import validate_event
from adaptive_recommender.serving.repositories import (
    BaseServingRepository,
    InMemoryServingRepository,
    ParquetServingRepository,
)
from adaptive_recommender.serving.reranker import RecommenderService


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    fix: str = "Check request parameters and try again",
    recovery: str = "Contact system operator or verify service health",
    request_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "code": code,
        "message": message,
        "fix": fix,
        "recovery": recovery,
        "request_id": request_id or str(uuid.uuid4()),
    }
    if extra:
        content.update(extra)
    return JSONResponse(status_code=status_code, content=content)


def create_app(repository: BaseServingRepository | None = None) -> FastAPI:
    app = FastAPI(
        title="Adaptive Session-Aware Recommender API",
        version="0.1.0",
        description="Serving API exposing ALS candidates, real-time re-ranking, and cold-start fallbacks.",
    )

    data_dir = os.environ.get("DATA_DIR", "data/generated")
    repo = repository or ParquetServingRepository(data_root=Path(data_dir))
    recommender = RecommenderService(repository=repo)
    app.state.repo = repo
    app.state.recommender = recommender

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="REQUEST_VALIDATION_ERROR",
            message="Request body or query parameter failed validation",
            fix="Correct the payload schema or parameter types",
            recovery="Review the API documentation at /docs",
            request_id=req_id,
            extra={"errors": exc.errors()},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        code = "HTTP_ERROR"
        if exc.status_code == 400:
            code = "BAD_REQUEST"
        elif exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 503:
            code = "SERVICE_UNAVAILABLE"
        return create_error_response(
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail),
            request_id=req_id,
        )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next: Any) -> Any:
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    @app.get("/health", status_code=status.HTTP_200_OK)
    def health_check(request: Request) -> Any:
        is_healthy, message = app.state.repo.is_healthy()
        if not is_healthy:
            return create_error_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="STORAGE_UNAVAILABLE",
                message=f"Serving storage is unavailable: {message}",
                fix="Run `make batch-sample` to generate gold candidate artifacts",
                recovery="Check file permissions and data/generated directory",
                request_id=request.state.request_id,
            )
        return {
            "status": "ok",
            "version": "0.1.0",
            "storage": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/products", status_code=status.HTTP_200_OK)
    def list_products(request: Request, limit: int = Query(default=20)) -> Any:
        if limit <= 0 or limit > 1000:
            return create_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_LIMIT",
                message="Limit must be a positive integer between 1 and 1000",
                fix="Provide ?limit=20 with a positive number",
                recovery="Omit limit parameter to use default 20",
                request_id=request.state.request_id,
            )

        is_healthy, message = app.state.repo.is_healthy()
        if not is_healthy:
            return create_error_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="STORAGE_UNAVAILABLE",
                message=f"Serving storage is unavailable: {message}",
                fix="Run `make batch-sample` to populate product data",
                recovery="Check storage health at /health",
                request_id=request.state.request_id,
            )

        products = app.state.repo.get_products(limit=limit)
        return {
            "products": [
                {
                    "product_id": p.product_id,
                    "category_code": p.category_code,
                    "brand": p.brand,
                    "event_count": p.event_count,
                    "unique_users": p.unique_users,
                    "average_price": p.average_price,
                    "popularity_score": p.popularity_score,
                }
                for p in products
            ],
            "count": len(products),
        }

    @app.post("/events", status_code=status.HTTP_202_ACCEPTED)
    async def receive_event(request: Request) -> Any:
        try:
            payload = await request.json()
        except Exception:
            return create_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_JSON",
                message="Request body must be valid JSON",
                fix="Send a well-formed JSON object",
                recovery="Verify JSON quotes and syntax",
                request_id=request.state.request_id,
            )

        event, errors = validate_event(payload)
        if errors:
            error_details = [{"code": e.code, "message": e.message, "field": e.field} for e in errors]
            return create_error_response(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="VALIDATION_FAILED",
                message="Event failed canonical schema validation",
                fix="Ensure all required fields (schema_version, event_id, event_time, ingest_time, event_type, product_id, event_source) are valid",
                recovery="Check data contracts in docs/designs/PROJECT_CONTEXT_V2.md",
                request_id=request.state.request_id,
                extra={"errors": error_details},
            )

        assert event is not None
        return {
            "status": "accepted",
            "event_id": event.event_id,
            "event_type": event.event_type,
            "ingest_time": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/recommendations/{user_id}", status_code=status.HTTP_200_OK)
    def get_recommendations(
        user_id: str,
        request: Request,
        limit: int = Query(default=10),
        user_session: str | None = Query(default=None),
    ) -> Any:
        if limit <= 0 or limit > 100:
            return create_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_LIMIT",
                message="Limit must be a positive integer between 1 and 100",
                fix="Provide a limit parameter such as ?limit=10",
                recovery="Omit limit parameter to use default 10",
                request_id=request.state.request_id,
            )

        is_healthy, message = app.state.repo.is_healthy()
        if not is_healthy:
            return create_error_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code="STORAGE_UNAVAILABLE",
                message=f"Serving storage is unavailable: {message}",
                fix="Run `make batch-sample` to generate recommendations candidates",
                recovery="Check storage health at /health",
                request_id=request.state.request_id,
            )

        recs, is_fallback = app.state.recommender.get_recommendations(
            user_id=user_id,
            limit=limit,
            user_session=user_session,
        )

        return {
            "user_id": user_id,
            "recommendations": [r.to_dict() for r in recs],
            "count": len(recs),
            "fallback": is_fallback,
        }

    return app


app = create_app()
