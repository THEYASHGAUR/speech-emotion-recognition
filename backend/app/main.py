"""
AutoAce AI — FastAPI application entry point.

Responsibilities:
- Application factory with lifespan management
- Model preloading at startup
- CORS, exception handlers, structured logging
- Router registration
- API documentation metadata
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, batch, upload
from app.config import get_settings
from app.services.emotion.recognizer import EmotionRecognizer
from app.services.noise.detector import NoiseDetector
from app.services.overlap.detector import OverlapDetector
from app.services.quality.analyzer import QualityAnalyzer
from app.services.silence.detector import SilenceDetector
from app.utils.logging_config import configure_logging

# ─────────────────────────── Logging Setup ───────────────────────────────────
configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────── Lifespan ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan events.
    Models are loaded ONCE at startup and reused for every request.
    """
    logger.info("AutoAce AI starting up — loading ML models...")
    start = time.perf_counter()

    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.emotion_model_cache_dir, exist_ok=True)

    # ── Load ML models into app state (shared across all requests) ──
    try:
        app.state.emotion_recognizer = EmotionRecognizer(settings)
        await app.state.emotion_recognizer.load()
        logger.info("Emotion model loaded successfully")
    except Exception as exc:
        logger.error(f"Failed to load emotion model: {exc}", exc_info=True)
        app.state.emotion_recognizer = None

    app.state.noise_detector = NoiseDetector(settings)
    app.state.quality_analyzer = QualityAnalyzer(settings)
    app.state.overlap_detector = OverlapDetector(settings)
    app.state.silence_detector = SilenceDetector(settings)

    # In-memory batch store (production: replace with Redis/DB)
    app.state.batch_store: dict = {}

    elapsed = time.perf_counter() - start
    logger.info(f"Startup complete in {elapsed:.2f}s — AutoAce AI is ready")

    yield

    # ── Shutdown ──
    logger.info("AutoAce AI shutting down...")


# ─────────────────────────── App Factory ─────────────────────────────────────
def create_application() -> FastAPI:
    app = FastAPI(
        title="AutoAce AI",
        description=(
            "Production-ready AI API for customer call recording analysis. "
            "Predicts emotional tone, background noise, audio quality, "
            "speaker overlap, and silence detection."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request timing middleware ─────────────────────────────────────────────
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response

    # ── Global exception handlers ─────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled exception on {request.method} {request.url}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred.",
                "path": str(request.url),
            },
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(auth.router, prefix=settings.api_prefix, tags=["Authentication"])
    app.include_router(upload.router, prefix=settings.api_prefix, tags=["Upload"])
    app.include_router(batch.router, prefix=settings.api_prefix, tags=["Batch"])

    # ── Root & Health check ───────────────────────────────────────────────────
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.app_name,
            "status": "healthy",
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
            "api_prefix": settings.api_prefix,
        }

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
        }

    return app


app = create_application()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
