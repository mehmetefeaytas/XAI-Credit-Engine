"""
app/data/models/tree_model.py
──────────────────────────────────────────────────────────────────────────────
Ağaç yapısını (versiyonlar, düğümler, kenarlar) saklayan SQLAlchemy tabloları.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.data.database import Base


class TreeVersionModel(Base):
    """Karar ağacının versiyon metadasını tutar."""
    __tablename__ = "tree_versions"

    id = Column(String(36), primary_key=True)
    built_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    training_size = Column(Integer, nullable=False)
    total_nodes = Column(Integer, nullable=False)
    leaf_nodes = Column(Integer, nullable=False)
    inner_nodes = Column(Integer, nullable=False)
    max_depth_reached = Column(Integer, nullable=False)
    is_valid = Column(Boolean, nullable=False)
    description = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Kök düğüm referansı (Nodes çekildikten sonra atanabilir)
    root_node_id = Column(String(36), nullable=True)

    nodes = relationship("DecisionNodeModel", back_populates="tree_version", cascade="all, delete-orphan")
    edges = relationship("TreeEdgeModel", back_populates="tree_version", cascade="all, delete-orphan")


class DecisionNodeModel(Base):
    """Ağaç düğümlerini tutar (İç düğüm veya Yaprak)."""
    __tablename__ = "decision_nodes"

    id = Column(String(36), primary_key=True)
    tree_version_id = Column(String(36), ForeignKey("tree_versions.id"), nullable=False, index=True)
    
    feature_name = Column(String(100), nullable=True)
    threshold = Column(Float, nullable=True)
    operator = Column(String(20), nullable=True)
    
    is_leaf = Column(Boolean, nullable=False)
    leaf_label = Column(String(50), nullable=True)  # APPROVED veya REJECTED
    
    depth = Column(Integer, nullable=False)
    entropy = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    
    tree_version = relationship("TreeVersionModel", back_populates="nodes")


class TreeEdgeModel(Base):
    """Düğümler arası geçişleri (kenarları) tutar."""
    __tablename__ = "tree_edges"

    id = Column(String(36), primary_key=True)
    tree_version_id = Column(String(36), ForeignKey("tree_versions.id"), nullable=False, index=True)
    
    source_node_id = Column(String(36), ForeignKey("decision_nodes.id"), nullable=False)
    target_node_id = Column(String(36), ForeignKey("decision_nodes.id"), nullable=False)
    
    # Hangi koşulda o yola gidildi? (True/False)
    branch_value = Column(Boolean, nullable=False)
    
    tree_version = relationship("TreeVersionModel", back_populates="edges")
