"""
app/api/v1/dataset.py
──────────────────────────────────────────────────────────────────────────────
Dataset yönetimi endpoint'leri.

GET    /api/v1/dataset               → Tüm kayıtları listele (sayfalı)
POST   /api/v1/dataset/generate      → Sentetik veri üret
DELETE /api/v1/dataset               → Tüm dataset'i temizle

Bu endpoint'ler şu an in-memory store kullanır.
Adım 4'te (DB katmanı) SQLAlchemy ile değiştirilecek.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.domain.models.customer import EmploymentStatus
from app.domain.services.dataset_service import DatasetService, DatasetRecord
from app.schemas.dataset_schema import (
    DatasetGenerateRequest,
    DatasetRecordResponse,
    DatasetSummaryResponse,
    DatasetListResponse,
)

router  = APIRouter()
settings = get_settings()

# ── In-Memory Veri Deposu (Adım 4'te DB ile değiştirilecek) ─────────────────
_dataset_store: list[DatasetRecord] = []
_dataset_generated_at: str | None   = None


def _record_to_response(rec: DatasetRecord, idx: int) -> DatasetRecordResponse:
    """DatasetRecord → DatasetRecordResponse dönüşümü."""
    c = rec.customer
    return DatasetRecordResponse(
        id=str(c.id),
        full_name=c.full_name,
        age=c.age,
        income=c.income,
        credit_score=c.credit_score,
        has_prior_default=c.has_prior_default,
        employment_status=c.employment_status.value,
        debt_to_income=c.debt_to_income,
        existing_credits=c.existing_credits,
        loan_amount=c.loan_amount,
        decision=rec.decision,
        feature_vector=rec.feature_vector,
    )


# ── GET /dataset ─────────────────────────────────────────────────────────────
@router.get("", response_model=DatasetListResponse, summary="Dataset kayıtlarını listele")
async def list_dataset(
    page: int = Query(default=1,  ge=1,  description="Sayfa numarası"),
    size: int = Query(default=50, ge=1, le=500, description="Sayfa başına kayıt"),
    decision: bool | None = Query(default=None, description="Karar filtresi (true=APPROVED)"),
):
    """
    Mevcut dataset kayıtlarını sayfalı olarak döner.

    - **page**: Sayfa numarası (1'den başlar)
    - **size**: Sayfa başına kayıt sayısı (maks 500)
    - **decision**: True=APPROVED, False=REJECTED filtresi
    """
    global _dataset_store

    if not _dataset_store:
        return DatasetListResponse(total=0, page=page, size=size, items=[])

    filtered = _dataset_store
    if decision is not None:
        filtered = [r for r in _dataset_store if r.decision == decision]

    total = len(filtered)
    start = (page - 1) * size
    end   = start + size
    page_items = filtered[start:end]

    return DatasetListResponse(
        total=total,
        page=page,
        size=size,
        items=[_record_to_response(r, i) for i, r in enumerate(page_items)],
    )


# ── POST /dataset/generate ───────────────────────────────────────────────────
@router.post("/generate", response_model=DatasetSummaryResponse, status_code=201,
             summary="Sentetik veri üret")
async def generate_dataset(req: DatasetGenerateRequest):
    """
    Sentetik kredi başvurusu verisi üretir.

    - **count**: Üretilecek kayıt sayısı (10–10.000)
    - **approval_ratio**: APPROVED oranı (0.1–0.9), önerilen 0.5–0.6
    - **seed**: Rastgelelik tohumu (reproducibility için)

    Her çağrı mevcut dataset'i **tamamen siler** ve yeniden üretir.
    """
    global _dataset_store, _dataset_generated_at

    service = DatasetService(seed=req.seed)
    records = service.generate(
        count=req.count,
        approval_ratio=req.approval_ratio,
    )

    _dataset_store = records
    _dataset_generated_at = datetime.now(timezone.utc).isoformat()

    balance = DatasetService.class_balance(records)

    # İlk 100 kaydı döndür (büyük dataset'lerde bandwidth tasarrufu)
    preview_records = records[:100]

    return DatasetSummaryResponse(
        total=balance["total"],
        approved=balance["approved"],
        rejected=balance["rejected"],
        approval_rate=balance["approval_rate"],
        records=[_record_to_response(r, i) for i, r in enumerate(preview_records)],
    )


# ── DELETE /dataset ──────────────────────────────────────────────────────────
@router.delete("", status_code=200, summary="Tüm dataset'i temizle")
async def clear_dataset():
    """
    Mevcut in-memory dataset'i tamamen siler.

    **Uyarı:** Ağaç inşası için gerekli veri kaybolur.
    """
    global _dataset_store, _dataset_generated_at
    count = len(_dataset_store)
    _dataset_store = []
    _dataset_generated_at = None
    return {"deleted_count": count, "message": "Dataset temizlendi."}


# ── GET /dataset/stats ───────────────────────────────────────────────────────
@router.get("/stats", summary="Dataset istatistikleri")
async def dataset_stats():
    """Dataset özet istatistiklerini döner."""
    global _dataset_store, _dataset_generated_at

    if not _dataset_store:
        return {"total": 0, "message": "Henüz dataset üretilmedi."}

    balance = DatasetService.class_balance(_dataset_store)
    return {
        **balance,
        "generated_at": _dataset_generated_at,
        "features": DatasetService.feature_names(),
    }


# ── Dataset Store Getter (diğer modüller için) ───────────────────────────────
def get_dataset_store() -> list[DatasetRecord]:
    """Dataset store'a dışarıdan erişim (diğer endpoint'ler için)."""
    return _dataset_store
