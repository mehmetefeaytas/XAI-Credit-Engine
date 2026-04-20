"""
domain/models/decision_node.py
──────────────────────────────────────────────────────────────────────────────
Karar Ağacı Düğümü ve Kenar modelleri.

Grafik teorisi açısından:
    - Ağaç T = (V, E): yönlü asiklik graf (DAG)
    - V (vertices): DecisionTreeNode listesi
    - E (edges):    DecisionTreeEdge listesi

Düğüm türleri:
    1. İç Düğüm (is_leaf=False): Bir özelliği test eder, 2 çocuğu vardır
    2. Yaprak Düğüm (is_leaf=True): Karar verir (APPROVED/REJECTED)

Kenar türleri:
    - branch_value=True  → "Evet/Sol" dalı (özellik koşulu sağlanıyor)
    - branch_value=False → "Hayır/Sağ" dalı (özellik koşulu sağlanmıyor)
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4


VALID_OPERATORS = {"GTE", "LTE", "GT", "LT", "EQ", "NEQ"}
VALID_LABELS    = {"APPROVED", "REJECTED"}


@dataclass
class DecisionTreeNode:
    """
    Karar ağacı düğümü.

    İç düğüm örneği:
        feature_name="credit_score_gt_700", threshold=700, operator="GTE",
        is_leaf=False, depth=0, entropy=0.97, sample_count=500

    Yaprak örneği:
        is_leaf=True, leaf_label="APPROVED", depth=3,
        entropy=0.0, sample_count=87
    """
    id:           UUID             = field(default_factory=uuid4)
    feature_name: Optional[str]   = None   # None → yaprak
    threshold:    Optional[float] = None
    operator:     Optional[str]   = None   # "GTE" | "LTE" | "GT" | "LT" | "EQ" | "NEQ"
    is_leaf:      bool            = False
    leaf_label:   Optional[str]   = None   # "APPROVED" veya "REJECTED"
    depth:        int             = 0
    entropy:      float           = 0.0
    sample_count: int             = 0

    # İnferrans sırasında confidence hesabı için
    majority_class_count: int = 0

    # Çocuk referansları (in-memory tree traversal için)
    child_true:  Optional["DecisionTreeNode"] = field(default=None, repr=False)
    child_false: Optional["DecisionTreeNode"] = field(default=None, repr=False)

    def is_pure(self) -> bool:
        """
        Düğüm saf mı? (Entropi == 0.0)

        Saf düğüm → tüm örnekler aynı sınıfa ait.
        Yaprak yapmak için ideal koşul.
        """
        return abs(self.entropy) < 1e-9  # floating point tolerance

    def validate(self) -> None:
        """
        Düğüm tutarlılık kontrolü. ValueError fırlatır.

        Kurallar:
            - Yaprak değilse feature_name olmalı
            - Yapraksa leaf_label geçerli değerde olmalı
            - operator VALID_OPERATORS içinde olmalı
        """
        if not self.is_leaf:
            if not self.feature_name:
                raise ValueError(f"İç düğüm {self.id} için feature_name gerekli.")
            if self.operator and self.operator not in VALID_OPERATORS:
                raise ValueError(
                    f"Geçersiz operator: '{self.operator}'. "
                    f"Geçerli: {VALID_OPERATORS}"
                )
        else:
            if self.leaf_label and self.leaf_label not in VALID_LABELS:
                raise ValueError(
                    f"Geçersiz yaprak etiketi: '{self.leaf_label}'. "
                    f"Geçerli: {VALID_LABELS}"
                )

    def to_dict(self) -> dict:
        """JSON-serializable dict döner."""
        return {
            "id":           str(self.id),
            "feature_name": self.feature_name,
            "threshold":    self.threshold,
            "operator":     self.operator,
            "is_leaf":      self.is_leaf,
            "leaf_label":   self.leaf_label,
            "depth":        self.depth,
            "entropy":      round(self.entropy, 6),
            "sample_count": self.sample_count,
        }

    def __repr__(self) -> str:
        if self.is_leaf:
            return (
                f"LeafNode(id={str(self.id)[:8]}..., "
                f"label={self.leaf_label}, depth={self.depth}, "
                f"samples={self.sample_count}, H={self.entropy:.4f})"
            )
        return (
            f"InnerNode(id={str(self.id)[:8]}..., "
            f"feature='{self.feature_name}', depth={self.depth}, "
            f"samples={self.sample_count}, H={self.entropy:.4f})"
        )


@dataclass
class DecisionTreeEdge:
    """
    İki düğüm arasındaki yönlü kenar.

    Özellikler:
        source_node_id: Kaynak düğüm (test eden iç düğüm)
        target_node_id: Hedef düğüm
        branch_value:   True  → "Evet" dalı (koşul sağlandı)
                        False → "Hayır" dalı (koşul sağlanmadı)

    Kısıt: UNIQUE(source_node_id, branch_value) → ağaç determinizmi
    """
    id:             UUID = field(default_factory=uuid4)
    source_node_id: UUID = field(default_factory=uuid4)
    target_node_id: UUID = field(default_factory=uuid4)
    branch_value:   bool = True

    def to_dict(self) -> dict:
        """JSON-serializable dict döner."""
        return {
            "id":             str(self.id),
            "source_node_id": str(self.source_node_id),
            "target_node_id": str(self.target_node_id),
            "branch_value":   self.branch_value,
        }

    def __repr__(self) -> str:
        branch = "TRUE→" if self.branch_value else "FALSE→"
        return (
            f"Edge({str(self.source_node_id)[:8]}... "
            f"─{branch}→ {str(self.target_node_id)[:8]}...)"
        )
