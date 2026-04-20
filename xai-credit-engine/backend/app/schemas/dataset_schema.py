"""
app/schemas/dataset_schema.py
──────────────────────────────────────────────────────────────────────────────
Dataset API giriş/çıkış Pydantic şemaları.
"""

from pydantic import BaseModel, Field, field_validator


class DatasetGenerateRequest(BaseModel):
    """POST /dataset/generate isteği."""
    count:          int   = Field(default=500, ge=10, le=10_000, description="Üretilecek kayıt sayısı")
    approval_ratio: float = Field(default=0.55, ge=0.1, le=0.9,  description="APPROVED oranı")
    seed:           int | None = Field(default=42, description="Rastgelelik tohumu")

    model_config = {"json_schema_extra": {"example": {"count": 500, "approval_ratio": 0.55, "seed": 42}}}


class DatasetRecordResponse(BaseModel):
    """Tek dataset kaydı çıktısı."""
    id:                  str
    full_name:           str
    age:                 int
    income:              float
    credit_score:        int
    has_prior_default:   bool
    employment_status:   str
    debt_to_income:      float
    existing_credits:    int
    loan_amount:         float
    decision:            bool
    feature_vector:      dict[str, bool]


class DatasetSummaryResponse(BaseModel):
    """Dataset üretimi özet çıktısı."""
    total:         int
    approved:      int
    rejected:      int
    approval_rate: float
    records:       list[DatasetRecordResponse]


class DatasetListResponse(BaseModel):
    """Mevcut dataset kayıtları listesi (sayfalı)."""
    total:  int
    page:   int
    size:   int
    items:  list[DatasetRecordResponse]
