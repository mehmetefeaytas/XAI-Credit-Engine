"""
app/api/v1/logs.py
──────────────────────────────────────────────────────────────────────────────
Audit log listeleme endpoint'leri (SQLAlchemy Destekli).
"""

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.data.database import get_db
from app.data.models.log_model import InferenceLogModel, ExplanationLogModel

router = APIRouter()

@router.get("", summary="Audit log kayıtlarını listele")
async def list_logs(
    type:  str | None = Query(default=None, description="inference | explanation"),
    page:  int        = Query(default=1, ge=1),
    size:  int        = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    all_logs = []

    # Inference Loglari
    if type is None or type == "inference":
        res = await db.execute(select(InferenceLogModel).order_by(InferenceLogModel.created_at.desc()).limit(100))
        for inf in res.scalars():
            all_logs.append({
                "type":       "inference",
                "id":         inf.id,
                "decision":   inf.decision,
                "confidence": inf.confidence,
                "created_at": inf.created_at.isoformat() if inf.created_at else "",
                "customer":   inf.customer_name or "",
            })

    # Explanation Loglari
    if type is None or type == "explanation":
        res = await db.execute(select(ExplanationLogModel).order_by(ExplanationLogModel.generated_at.desc()).limit(100))
        for exp in res.scalars():
            all_logs.append({
                "type":           "explanation",
                "id":             exp.id,
                "inference_id":   exp.inference_id,
                "decision":       exp.decision,
                "generated_at":   exp.generated_at.isoformat() if exp.generated_at else "",
            })

    # Ortak zamana göre sırala
    all_logs.sort(key=lambda x: x.get("created_at") or x.get("generated_at", ""), reverse=True)

    total  = len(all_logs)
    start  = (page - 1) * size
    end    = start + size

    return {
        "total": total,
        "page":  page,
        "size":  size,
        "items": all_logs[start:end],
    }
