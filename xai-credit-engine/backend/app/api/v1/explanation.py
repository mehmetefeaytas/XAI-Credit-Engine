"""
app/api/v1/explanation.py
──────────────────────────────────────────────────────────────────────────────
XAI Açıklama endpoint'i (SQLAlchemy Destekli).
"""

import uuid

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.data.database import get_db
from app.data.models.log_model import InferenceLogModel, ExplanationLogModel
from app.engine.xai.explanation_generator import ExplanationGenerator
from app.engine.inference.inference_engine import InferenceStep
from app.schemas.explanation_schema import ExplanationResponse

router = APIRouter()
generator = ExplanationGenerator()

@router.get("/{inference_id}", response_model=ExplanationResponse, summary="XAI açıklama raporu")
async def get_explanation(inference_id: str, language: str = "tr", db: AsyncSession = Depends(get_db)):
    """
    Belirli bir çıkarım için XAI açıklama raporu döner.
    Eğer ExplanationLogModel'de zaten varsa veritabanından getir.
    Yoksa InferenceLogModel'den oku, üret ve DB'ye cache'le.
    """
    
    # 1. Önce DB'de cache var mı bak
    res_exp = await db.execute(select(ExplanationLogModel).where(ExplanationLogModel.inference_id == inference_id))
    existing_exp = res_exp.scalars().first()
    
    if existing_exp and existing_exp.language_code == language:
        return ExplanationResponse(
            explanation_id=existing_exp.id,
            inference_id=existing_exp.inference_id,
            decision=existing_exp.decision,
            boolean_formula=existing_exp.boolean_formula,
            dnf_formula=existing_exp.dnf_formula,
            natural_language=existing_exp.natural_language,
            technical_log=existing_exp.technical_log,
            language_code=existing_exp.language_code,
            generated_at=existing_exp.generated_at.isoformat()
        )

    # 2. Inference log'unda ara
    res_inf = await db.execute(select(InferenceLogModel).where(InferenceLogModel.id == inference_id))
    log_entry = res_inf.scalars().first()

    if not log_entry:
        raise HTTPException(
            status_code=404,
            detail={"code": "INFERENCE_NOT_FOUND", "message": f"inference_id '{inference_id}' bulunamadı."}
        )

    # 3. Path'i InferenceStep listesine çevir
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
        for step in log_entry.path
    ]

    # 4. Açıklama üret
    output = generator.generate(
        path=path_steps,
        decision=log_entry.decision,
        language=language,
    )

    # 5. Yeni açıklamayı DB'ye kaydet
    explanation_id = str(uuid.uuid4())
    
    db_exp = ExplanationLogModel(
        id=explanation_id,
        inference_id=inference_id,
        decision=log_entry.decision,
        boolean_formula=output.boolean_formula,
        dnf_formula=output.dnf_formula,
        natural_language=output.natural_language,
        technical_log=output.technical_log,
        language_code=language
    )
    db.add(db_exp)
    await db.commit()
    await db.refresh(db_exp)

    return ExplanationResponse(
        explanation_id=db_exp.id,
        inference_id=db_exp.inference_id,
        decision=db_exp.decision,
        boolean_formula=db_exp.boolean_formula,
        dnf_formula=db_exp.dnf_formula,
        natural_language=db_exp.natural_language,
        technical_log=db_exp.technical_log,
        language_code=db_exp.language_code,
        generated_at=db_exp.generated_at.isoformat()
    )
