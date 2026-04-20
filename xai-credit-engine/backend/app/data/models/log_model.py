"""
app/data/models/log_model.py
──────────────────────────────────────────────────────────────────────────────
Müşteri değerlendirmeleri (Inference) ve Açıklamalar (Explanation) için Log tabloları.
"""

from sqlalchemy import Column, String, Integer, Float, JSON, ForeignKey, DateTime
from datetime import datetime, timezone

from app.data.database import Base


class InferenceLogModel(Base):
    """Tek bir müşterinin karar adım (inference) sonucunu saklar."""
    __tablename__ = "inference_logs"

    id = Column(String(36), primary_key=True)
    tree_version_id = Column(String(36), nullable=False, index=True)
    customer_name = Column(String(100), nullable=True)
    
    decision = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    depth_reached = Column(Integer, nullable=False)
    
    feature_vector = Column(JSON, nullable=False)
    path = Column(JSON, nullable=False)  # PathStep dict'lerini JSON string olarak tutacağız
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ExplanationLogModel(Base):
    """Bir inference için üretilmiş XAI açıklamasını saklar."""
    __tablename__ = "explanation_logs"

    id = Column(String(36), primary_key=True)
    inference_id = Column(String(36), ForeignKey("inference_logs.id"), nullable=False, index=True, unique=True)
    
    decision = Column(String(20), nullable=False)
    boolean_formula = Column(String(500), nullable=False)
    dnf_formula = Column(String(1000), nullable=False)
    natural_language = Column(String(2000), nullable=False)
    technical_log = Column(String(3000), nullable=False)
    language_code = Column(String(5), nullable=False)
    
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
