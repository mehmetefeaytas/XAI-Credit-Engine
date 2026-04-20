"""
app/main.py
──────────────────────────────────────────────────────────────────────────────
FastAPI uygulama giriş noktası.

Başlatma: uvicorn app.main:app --reload

Middleware'ler:
    - CORSMiddleware: Frontend (React) erişimi
    - RequestLoggingMiddleware: Her isteği logla

Lifespan hook:
    - Startup: DB bağlantısını doğrula, in-memory state yükle
    - Shutdown: Temiz kapatma
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.api.router import api_router

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Logging Ayarı ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# ── Lifespan (Startup / Shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama yaşam döngüsü hook'u.

    Startup:
        - Konfigürasyon logla
        - (Sonraki adımda) DB bağlantısı doğrula

    Shutdown:
        - Temiz kapatma mesajı
    """
    # ── STARTUP ──────────────────────────────────────────────────────────────
    logger.info("=" * 55)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  Ortam: {settings.ENVIRONMENT}")
    logger.info(f"  DB URL: {settings.DATABASE_URL[:40]}...")
    logger.info(f"  Ağaç max_depth: {settings.TREE_MAX_DEPTH}")
    logger.info("=" * 55)

    yield  # ← uygulama bu noktada çalışır

    # ── SHUTDOWN ─────────────────────────────────────────────────────────────
    logger.info(f"{settings.APP_NAME} kapatılıyor...")


# ── FastAPI Uygulaması ────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Açıklanabilir Yapay Zeka (XAI) tabanlı kredi onay sistemi. "
        "Karar ağacı temelli, Shannon entropi ile sıfırdan inşa edilmiştir."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Timing Middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Her istek için süre ölçer ve X-Process-Time header ekler."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    return response


# ── Global Exception Handler ─────────────────────────────────────────────────
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """İş mantığı hatalarını 422 ile döner."""
    logger.warning(f"ValueError: {exc} | URL: {request.url}")
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "type": "validation_error"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Beklenmedik hataları 500 ile döner."""
    logger.error(f"Beklenmedik hata: {exc} | URL: {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Sunucu hatası. Lütfen tekrar deneyin.", "type": "server_error"},
    )


# ── API Router ────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Sağlık Kontrolü ──────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Servis canlılık kontrolü."""
    return {
        "status":      "healthy",
        "app":         settings.APP_NAME,
        "version":     settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["System"])
async def root():
    """API kök endpoint — API bilgisi döner."""
    return {
        "message": f"{settings.APP_NAME} API'ye hoş geldiniz.",
        "docs":    "/docs",
        "version": settings.APP_VERSION,
    }
