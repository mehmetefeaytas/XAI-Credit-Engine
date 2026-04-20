"""
app/config.py
──────────────────────────────────────────────────────────────────────────────
Ortam tabanlı uygulama konfigürasyonu.

pydantic-settings ile .env dosyasından veya ortam değişkenlerinden okur.
Tüm ayarlar test ortamında kolayca override edilebilir.

Kullanım:
    from app.config import get_settings
    settings = get_settings()
    settings.DATABASE_URL
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Uygulama konfigürasyon modeli.
    .env dosyasından veya ortam değişkenlerinden okunur.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Uygulama ────────────────────────────────────────────────────────────
    APP_NAME:    str = "XAI Credit Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = False
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"

    # ── API ─────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS:  list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Veritabanı ───────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./xai_credit.db"
    # PostgreSQL için örnek:
    # DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/xai_credit"

    DB_POOL_SIZE:     int = 10
    DB_MAX_OVERFLOW:  int = 20
    DB_ECHO:          bool = False  # SQL sorgularını logla (debug için True)

    # ── Karar Ağacı Motor Ayarları ───────────────────────────────────────────
    TREE_MAX_DEPTH:         int   = 8
    TREE_MIN_SAMPLES_SPLIT: int   = 5
    TREE_MIN_SAMPLES_LEAF:  int   = 2
    TREE_USE_GAIN_RATIO:    bool  = False

    # ── Dataset ──────────────────────────────────────────────────────────────
    DATASET_DEFAULT_COUNT:          int   = 500
    DATASET_DEFAULT_APPROVAL_RATIO: float = 0.55
    DATASET_RANDOM_SEED:            int   = 42

    # ── XAI ─────────────────────────────────────────────────────────────────
    EXPLANATION_DEFAULT_LANGUAGE: str = "tr"

    # ── Loglama ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """
    LRU cache ile singleton Settings örneği döner.
    Test override için: get_settings.cache_clear()
    """
    return Settings()
