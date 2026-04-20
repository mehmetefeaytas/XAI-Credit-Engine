"""
app/data/models/dataset_model.py
──────────────────────────────────────────────────────────────────────────────
Sentetik kredi başvuru verilerini saklayan tablo.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, JSON
from app.data.database import Base


class DatasetModel(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    income = Column(Float, nullable=False)
    credit_score = Column(Integer, nullable=False)
    has_prior_default = Column(Boolean, nullable=False)
    employment_status = Column(String(50), nullable=False)
    debt_to_income = Column(Float, nullable=False)
    existing_credits = Column(Integer, nullable=False)
    loan_amount = Column(Float, nullable=False)

    # İş kuralı sonucu oluşan etiket
    decision = Column(Boolean, nullable=False)
    
    # Karar ağacı algoritmasına giren Boolean özellikleri JSON olarak tutuyoruz
    feature_vector = Column(JSON, nullable=False)
