"""
app/schemas/inference_schema.py
──────────────────────────────────────────────────────────────────────────────
Çıkarım API Pydantic şemaları.
"""

from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    """
    POST /inference isteği.

    Müşteri ham verileri (ham sayısal değerler).
    Servis katmanında Boolean vektöre dönüştürülür.
    """
    age:               int   = Field(..., ge=18, le=100,  description="Müşteri yaşı")
    income:            float = Field(..., gt=0,           description="Yıllık gelir (TL)")
    credit_score:      int   = Field(..., ge=300, le=850, description="Kredi puanı")
    has_prior_default: bool  = Field(...,                 description="Geçmiş icra/temerrüt")
    employment_status: str   = Field(...,                 description="EMPLOYED|SELF_EMPLOYED|UNEMPLOYED")
    debt_to_income:    float = Field(..., ge=0.0, le=1.0, description="Borç/gelir oranı")
    existing_credits:  int   = Field(..., ge=0,           description="Mevcut aktif kredi sayısı")
    loan_amount:       float = Field(..., gt=0,           description="Talep edilen kredi tutarı (TL)")
    full_name:         str   = Field(default="",          description="Müşteri adı (opsiyonel)")

    model_config = {"json_schema_extra": {"example": {
        "age": 34, "income": 72000, "credit_score": 742,
        "has_prior_default": False, "employment_status": "EMPLOYED",
        "debt_to_income": 0.28, "existing_credits": 1,
        "loan_amount": 50000, "full_name": "Mehmet Yılmaz"
    }}}


class PathStep(BaseModel):
    """Tek karar adımı."""
    node_id:      str
    feature:      str
    threshold:    float | None
    operator:     str | None
    input_value:  bool
    branch_taken: bool
    depth:        int


class InferenceResponse(BaseModel):
    """POST /inference çıktısı."""
    inference_id:    str
    decision:        str          # "APPROVED" | "REJECTED"
    confidence:      float        # 0.5 – 1.0
    depth_reached:   int
    path:            list[PathStep]
    feature_vector:  dict[str, bool]
    tree_version_id: str
    created_at:      str
