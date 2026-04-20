"""
app/api/v1/dataset.py
──────────────────────────────────────────────────────────────────────────────
Dataset yönetimi endpoint'leri (SQLAlchemy Veritabanı Destekli).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.config import get_settings
from app.data.database import get_db
from app.data.models.dataset_model import DatasetModel
from app.domain.models.customer import EmploymentStatus, Customer
from app.domain.services.dataset_service import DatasetService, DatasetRecord
from app.schemas.dataset_schema import (
    DatasetGenerateRequest,
    DatasetRecordResponse,
    DatasetSummaryResponse,
    DatasetListResponse,
)

router  = APIRouter()
settings = get_settings()

def _record_to_response(db_record: DatasetModel) -> DatasetRecordResponse:
    return DatasetRecordResponse(
        id=db_record.id,
        full_name=db_record.full_name,
        age=db_record.age,
        income=db_record.income,
        credit_score=db_record.credit_score,
        has_prior_default=db_record.has_prior_default,
        employment_status=db_record.employment_status,
        debt_to_income=db_record.debt_to_income,
        existing_credits=db_record.existing_credits,
        loan_amount=db_record.loan_amount,
        decision=db_record.decision,
        feature_vector=db_record.feature_vector,
    )


@router.get("", response_model=DatasetListResponse, summary="Dataset kayıtlarını listele")
async def list_dataset(
    page: int = Query(default=1,  ge=1),
    size: int = Query(default=50, ge=1, le=500),
    decision: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    query = select(DatasetModel)
    if decision is not None:
        query = query.where(DatasetModel.decision == decision)
        
    # Toplam sayıyı bul
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Sayfalamayı uygula
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    records = result.scalars().all()

    return DatasetListResponse(
        total=total or 0,
        page=page,
        size=size,
        items=[_record_to_response(r) for r in records],
    )


@router.post("/generate", response_model=DatasetSummaryResponse, status_code=201,
             summary="Sentetik veri üret")
async def generate_dataset(req: DatasetGenerateRequest, db: AsyncSession = Depends(get_db)):
    """Mevcut dataset'i siler ve yeni kayıtlar üretir."""
    
    # Önce eski verileri sil
    await db.execute(delete(DatasetModel))
    
    # Yeni verileri üret
    service = DatasetService(seed=req.seed)
    records = service.generate(count=req.count, approval_ratio=req.approval_ratio)
    
    db_records = []
    for r in records:
        db_model = DatasetModel(
            id=str(r.customer.id),
            full_name=r.customer.full_name,
            age=r.customer.age,
            income=r.customer.income,
            credit_score=r.customer.credit_score,
            has_prior_default=r.customer.has_prior_default,
            employment_status=r.customer.employment_status.value,
            debt_to_income=r.customer.debt_to_income,
            existing_credits=r.customer.existing_credits,
            loan_amount=r.customer.loan_amount,
            decision=r.decision,
            feature_vector=r.feature_vector
        )
        db_records.append(db_model)
        db.add(db_model)
        
    await db.commit()
    
    balance = DatasetService.class_balance(records)
    
    # Önizleme için ilk 100 kaydı dön
    preview_records = db_records[:100]

    return DatasetSummaryResponse(
        total=balance["total"],
        approved=balance["approved"],
        rejected=balance["rejected"],
        approval_rate=balance["approval_rate"],
        records=[_record_to_response(r) for r in preview_records],
    )


@router.delete("", status_code=200, summary="Tüm dataset'i temizle")
async def clear_dataset(db: AsyncSession = Depends(get_db)):
    result = await db.execute(delete(DatasetModel))
    await db.commit()
    return {"deleted_count": result.rowcount, "message": "Dataset temizlendi."}


@router.get("/stats", summary="Dataset istatistikleri")
async def dataset_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(DatasetModel.id)))
    if not total:
        return {"total": 0, "message": "Henüz dataset üretilmedi."}
        
    approved = await db.scalar(select(func.count(DatasetModel.id)).where(DatasetModel.decision == True))
    rejected = total - (approved or 0)
    
    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "approval_rate": round((approved or 0) / total, 4) if total else 0.0,
        "rejection_rate": round(rejected / total, 4) if total else 0.0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "features": DatasetService.feature_names(),
    }
