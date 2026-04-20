"""
app/api/v1/logs.py
──────────────────────────────────────────────────────────────────────────────
Audit log listeleme endpoint'leri.

GET /api/v1/logs   → Tüm logları listele (tip filtresi + sayfalama)

Log tipleri: "inference" | "explanation" | "build"
"""

from fastapi import APIRouter, Query

from app.api.v1.inference import get_inference_log
from app.api.v1.explanation import get_explanation_log

router = APIRouter()


@router.get("", summary="Audit log kayıtlarını listele")
async def list_logs(
    type:  str | None = Query(default=None, description="inference | explanation"),
    page:  int        = Query(default=1, ge=1),
    size:  int        = Query(default=50, ge=1, le=200),
):
    """
    Tüm işlem loglarını döner.

    - **type**: `inference` veya `explanation` filtresi
    - **page**: Sayfa numarası
    - **size**: Sayfa başına kayıt
    """
    all_logs: list[dict] = []

    if type is None or type == "inference":
        for entry in get_inference_log():
            all_logs.append({
                "type":       "inference",
                "id":         entry["inference_id"],
                "decision":   entry["decision"],
                "confidence": entry["confidence"],
                "created_at": entry["created_at"],
                "customer":   entry.get("customer_name", ""),
            })

    if type is None or type == "explanation":
        for entry in get_explanation_log():
            all_logs.append({
                "type":           "explanation",
                "id":             entry["explanation_id"],
                "inference_id":   entry["inference_id"],
                "decision":       entry["decision"],
                "generated_at":   entry["generated_at"],
            })

    # Zamana göre sırala (yeniden eskiye)
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
