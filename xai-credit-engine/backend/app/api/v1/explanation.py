"""
app/api/v1/explanation.py
──────────────────────────────────────────────────────────────────────────────
XAI Açıklama endpoint'i.

GET /api/v1/explanation/{inference_id}   → Boolean formülü + NL rapor

İş akışı:
    1. inference_id ile log'da ilgili kaydı bul
    2. ExplanationGenerator.generate() çalıştır
    3. Açıklamayı log'a kaydet (explanation log)
    4. ExplanationResponse döner
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.engine.xai.explanation_generator import ExplanationGenerator
from app.engine.inference.inference_engine import InferenceStep
from app.schemas.explanation_schema import ExplanationResponse
from app.api.v1.inference import get_inference_log

router = APIRouter()

# ── In-Memory Explanation Log ─────────────────────────────────────────────────
_explanation_log: list[dict] = {}  # {inference_id: explanation_dict}

generator = ExplanationGenerator()


# ── GET /explanation/{inference_id} ──────────────────────────────────────────
@router.get("/{inference_id}", response_model=ExplanationResponse,
            summary="XAI açıklama raporu")
async def get_explanation(inference_id: str, language: str = "tr"):
    """
    Belirli bir çıkarım için XAI açıklama raporu döner.

    **Dönen değer:**
    - `boolean_formula`: Boolean AND zinciri (teknik)
    - `dnf_formula`: DNF format (akademik)
    - `natural_language`: Türkçe doğal dil raporu (GDPR uyumu)
    - `technical_log`: Adım adım audit logu

    **Hata:**
    - `404`: inference_id bulunamadı
    """
    global _explanation_log

    # Önce cache'de ara
    if inference_id in _explanation_log:
        return ExplanationResponse(**_explanation_log[inference_id])

    # Inference log'unda ara
    inference_logs = get_inference_log()
    log_entry = next(
        (e for e in inference_logs if e["inference_id"] == inference_id),
        None,
    )

    if not log_entry:
        raise HTTPException(
            status_code=404,
            detail={
                "code":    "INFERENCE_NOT_FOUND",
                "message": f"inference_id '{inference_id}' bulunamadı.",
            },
        )

    # Path'i InferenceStep listesine çevir
    path_steps = [
        InferenceStep(
            node_id=step["node_id"],
            feature=step["feature"],
            threshold=step.get("threshold"),
            operator=step.get("operator"),
            input_value=step["input_value"],
            branch_taken=step["branch_taken"],
            depth=step["depth"],
        )
        for step in log_entry["path"]
    ]

    # Açıklama üret
    output = generator.generate(
        path=path_steps,
        decision=log_entry["decision"],
        language=language,
    )

    explanation_id = str(uuid.uuid4())
    generated_at   = datetime.now(timezone.utc).isoformat()

    result = {
        "explanation_id":   explanation_id,
        "inference_id":     inference_id,
        "decision":         log_entry["decision"],
        "boolean_formula":  output.boolean_formula,
        "dnf_formula":      output.dnf_formula,
        "natural_language": output.natural_language,
        "technical_log":    output.technical_log,
        "language_code":    language,
        "generated_at":     generated_at,
    }

    # Cache'e kaydet (aynı inference için tekrar üretme)
    _explanation_log[inference_id] = result

    return ExplanationResponse(**result)


def get_explanation_log() -> list[dict]:
    """Explanation log'una dışarıdan erişim (logs endpoint için)."""
    return list(_explanation_log.values())
