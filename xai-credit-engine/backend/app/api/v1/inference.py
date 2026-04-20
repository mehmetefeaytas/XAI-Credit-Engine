"""
app/api/v1/inference.py
──────────────────────────────────────────────────────────────────────────────
Müşteri kredi değerlendirmesi endpoint'i.

POST /api/v1/inference   → Müşteri verisini alır, karar + path döner

İş akışı:
    1. Müşteri verisi doğrula (Pydantic + domain validate)
    2. Boolean özellik vektörüne dönüştür
    3. Aktif ağacı yükle (409 → ağaç yoksa)
    4. InferenceEngine.predict() çalıştır
    5. Sonucu in-memory log'a yaz
    6. InferenceResponse döner
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.domain.models.customer import Customer, EmploymentStatus
from app.engine.inference.inference_engine import InferenceEngine
from app.schemas.inference_schema import InferenceRequest, InferenceResponse, PathStep
from app.api.v1.tree import get_active_tree

router = APIRouter()

# ── In-Memory Inference Log ───────────────────────────────────────────────────
_inference_log: list[dict] = []


def get_inference_log() -> list[dict]:
    """Inference log'una dışarıdan erişim (logs endpoint için)."""
    return _inference_log


# ── POST /inference ──────────────────────────────────────────────────────────
@router.post("", response_model=InferenceResponse, status_code=200,
             summary="Müşteri kredi değerlendirmesi")
async def run_inference(req: InferenceRequest):
    """
    Müşteri bilgilerini alır ve karar ağacı üzerinden değerlendirir.

    **Ön koşul:** Aktif bir ağaç versiyonu olmalı (`/tree/build` çağrısından sonra).

    **Dönen değer:**
    - `decision`: APPROVED veya REJECTED
    - `confidence`: Güven skoru (0.5–1.0)
    - `path`: Her karar adımını gösteren liste
    - `feature_vector`: Dönüştürülmüş Boolean özellikler

    **Hata:**
    - `409`: Aktif ağaç yok
    - `422`: Geçersiz müşteri verisi
    """
    # ── Aktif ağacı yükle ─────────────────────────────────────────────────────
    tree_data = get_active_tree()
    if not tree_data:
        raise HTTPException(
            status_code=409,
            detail={
                "code":    "NO_ACTIVE_TREE",
                "message": "Değerlendirme için aktif bir karar ağacı yok. "
                           "Önce /tree/build çağırın.",
            },
        )

    # ── Müşteri domain modeli oluştur ─────────────────────────────────────────
    try:
        employment = EmploymentStatus(req.employment_status.upper())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={
                "code":    "INVALID_EMPLOYMENT",
                "message": f"Geçersiz employment_status: '{req.employment_status}'. "
                           "EMPLOYED, SELF_EMPLOYED veya UNEMPLOYED olmalı.",
            },
        )

    customer = Customer(
        full_name=req.full_name,
        age=req.age,
        income=req.income,
        credit_score=req.credit_score,
        has_prior_default=req.has_prior_default,
        employment_status=employment,
        debt_to_income=req.debt_to_income,
        existing_credits=req.existing_credits,
        loan_amount=req.loan_amount,
    )

    try:
        customer.validate()
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": str(e)})

    # ── Feature vektörüne dönüştür ────────────────────────────────────────────
    feature_vector = customer.to_feature_vector()

    # ── Çıkarım yap ───────────────────────────────────────────────────────────
    root = tree_data["root"]
    engine = InferenceEngine(root_node=root)

    try:
        result = engine.predict(feature_vector)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "INFERENCE_ERROR", "message": f"Çıkarım hatası: {str(e)}"},
        )

    # ── Sonucu logla ──────────────────────────────────────────────────────────
    inference_id    = str(uuid.uuid4())
    version_id      = tree_data["metadata"]["version_id"]
    created_at      = datetime.now(timezone.utc).isoformat()

    log_entry = {
        "inference_id":    inference_id,
        "tree_version_id": version_id,
        "customer_name":   req.full_name,
        "decision":        result.decision,
        "confidence":      result.confidence,
        "depth_reached":   result.depth_reached,
        "feature_vector":  feature_vector,
        "path":            result.path_as_dicts(),
        "created_at":      created_at,
        "type":            "inference",
    }
    _inference_log.append(log_entry)

    # ── Response döner ────────────────────────────────────────────────────────
    path_steps = [
        PathStep(
            node_id=step.node_id,
            feature=step.feature,
            threshold=step.threshold,
            operator=step.operator,
            input_value=step.input_value,
            branch_taken=step.branch_taken,
            depth=step.depth,
        )
        for step in result.path
    ]

    return InferenceResponse(
        inference_id=inference_id,
        decision=result.decision,
        confidence=round(result.confidence, 4),
        depth_reached=result.depth_reached,
        path=path_steps,
        feature_vector=feature_vector,
        tree_version_id=version_id,
        created_at=created_at,
    )
