"""
engine/inference/inference_engine.py
──────────────────────────────────────────────────────────────────────────────
Karar Ağacı Çıkarım Motoru — Kökten Yaprağa Traversal

Bu motor, eğitilmiş bir karar ağacını alır ve yeni müşteri için
kararı ve karar yolunu (path) üretir.

Algoritma:
    1. Kök düğümden başla
    2. Düğümün özelliğini feature_vector'dan oku
    3. Değere göre True/False dalını seç
    4. Yaprak bulunana kadar tekrarla
    5. Yaprak etiketi karar, path tüm adımlar

Karmaşıklık:
    Tekil çıkarım:  O(d)  [d = ağaç derinliği]
    Batch çıkarım:  O(k×d) [k = batch boyutu]
"""

from dataclasses import dataclass, field
from typing import Optional

from app.domain.models.decision_node import DecisionTreeNode


@dataclass
class InferenceStep:
    """
    Tek bir çıkarım adımı (karar ağacında bir düğüm geçişi).

    Attributes:
        node_id:      Düğüm ID'si
        feature:      Test edilen özellik adı
        threshold:    Eşik değeri
        operator:     Karşılaştırma operatörü
        input_value:  Müşterinin bu özellik için değeri
        branch_taken: True = sol dal (koşul sağlandı), False = sağ dal
        depth:        Ağaçtaki derinlik
    """
    node_id:      str
    feature:      str
    threshold:    Optional[float]
    operator:     Optional[str]
    input_value:  bool
    branch_taken: bool
    depth:        int

    def to_dict(self) -> dict:
        return {
            "node_id":      self.node_id,
            "feature":      self.feature,
            "threshold":    self.threshold,
            "operator":     self.operator,
            "input_value":  self.input_value,
            "branch_taken": self.branch_taken,
            "depth":        self.depth,
        }


@dataclass
class InferenceResult:
    """
    Tek bir müşteri için çıkarım sonucu.

    Attributes:
        decision:      "APPROVED" veya "REJECTED"
        path:          Tüm karar adımları listesi
        leaf_node_id:  Ulaşılan yaprak düğümün ID'si
        confidence:    Yaprak safsızlığına göre güven skoru (0.5–1.0)
        depth_reached: Karar için geçilen derinlik
    """
    decision:      str
    path:          list[InferenceStep]
    leaf_node_id:  str
    confidence:    float
    depth_reached: int

    def path_as_dicts(self) -> list[dict]:
        return [step.to_dict() for step in self.path]

    def summary(self) -> dict:
        return {
            "decision":      self.decision,
            "confidence":    round(self.confidence, 4),
            "depth_reached": self.depth_reached,
            "path_length":   len(self.path),
            "leaf_node_id":  self.leaf_node_id,
        }

    def __repr__(self) -> str:
        return (
            f"InferenceResult(decision={self.decision}, "
            f"confidence={self.confidence:.2%}, "
            f"depth={self.depth_reached}, "
            f"path_steps={len(self.path)})"
        )


class TreeTraversalError(Exception):
    """Ağaç geçişi sırasında kritik hata."""
    pass


class InferenceEngine:
    """
    Karar ağacı çıkarım motoru.

    Kullanım:
        engine = InferenceEngine(root_node=root, edge_map=edge_map)
        result = engine.predict(feature_vector)

    edge_map formatı:
        {node_id: {True: child_node_true, False: child_node_false}}

    Bu format O(1) dal seçimine olanak tanır.
    """

    def __init__(
        self,
        root_node: DecisionTreeNode,
        edge_map: Optional[dict] = None,
    ):
        """
        Args:
            root_node: Kök düğüm
            edge_map:  Önceden hesaplanmış dal haritası.
                       None ise root_node'dan otomatik inşa edilir.
        """
        self._root = root_node
        self._edge_map = edge_map or self._build_edge_map(root_node)

    def predict(self, feature_vector: dict[str, bool]) -> InferenceResult:
        """
        Tek müşteri için karar üretir.

        Args:
            feature_vector: Boolean özellik değerleri dict'i
                            Örnek: {"income_gt_50k": True, "credit_score_gt_700": False, ...}

        Returns:
            InferenceResult — karar, path, güven skoru

        Raises:
            ValueError:          feature_vector boşsa veya eksik özellik varsa
            TreeTraversalError:  Ağaçta kenar bulunamazsa (bozuk yapı)
        """
        if not feature_vector:
            raise ValueError("feature_vector boş olamaz.")

        path: list[InferenceStep] = []
        return self._traverse(self._root, feature_vector, path, depth=0)

    def _traverse(
        self,
        node: DecisionTreeNode,
        vector: dict[str, bool],
        path: list[InferenceStep],
        depth: int
    ) -> InferenceResult:
        """
        Recursive traversal.

        Her çağrı bir düğümü işler:
            - Yapraksa → sonuç döner
            - İç düğümse → feature değerini okur, uygun dala geçer
        """
        # ── YAPRAK KONTROLÜ ──────────────────────────────────────────────────
        if node.is_leaf:
            confidence = self._calculate_confidence(node)
            return InferenceResult(
                decision=node.leaf_label or "REJECTED",
                path=path,
                leaf_node_id=str(node.id),
                confidence=confidence,
                depth_reached=depth,
            )

        # ── FEATURE DEĞERİNİ AL ──────────────────────────────────────────────
        feature_val = vector.get(node.feature_name)

        if feature_val is None:
            # Eksik feature: imputation → çoğunluk dalı (basit strateji)
            # Daha gelişmiş: median veya bayes imputation (v2 scope)
            feature_val = self._majority_branch(node)

        # ── KARAR ADIMINI KAYDET ─────────────────────────────────────────────
        step = InferenceStep(
            node_id=str(node.id),
            feature=node.feature_name or "",
            threshold=node.threshold,
            operator=node.operator,
            input_value=feature_val,
            branch_taken=feature_val,
            depth=depth,
        )
        path.append(step)

        # ── DAL SEÇİMİ ───────────────────────────────────────────────────────
        node_branches = self._edge_map.get(node.id)
        if node_branches is None:
            raise TreeTraversalError(
                f"Düğüm {str(node.id)[:8]}... için kenar haritasında giriş yok. "
                f"Ağaç bozuk olabilir."
            )

        next_node = node_branches.get(feature_val)
        if next_node is None:
            raise TreeTraversalError(
                f"Düğüm {str(node.id)[:8]}... için branch_value={feature_val} "
                f"kenarı bulunamadı."
            )

        return self._traverse(next_node, vector, path, depth + 1)

    @staticmethod
    def _calculate_confidence(leaf_node: DecisionTreeNode) -> float:
        """
        Yaprak düğümün güven skorunu hesaplar.

        confidence = majority_count / total_count
            - Saf yaprak (H=0): confidence = 1.0
            - Kirli yaprak:     confidence ∈ (0.5, 1.0)

        Args:
            leaf_node: Yaprak düğüm

        Returns:
            float ∈ [0.5, 1.0]
        """
        total = leaf_node.sample_count
        if total == 0:
            return 1.0

        majority = leaf_node.majority_class_count
        return majority / total if majority > 0 else 0.5

    @staticmethod
    def _majority_branch(node: DecisionTreeNode) -> bool:
        """
        Eksik özellik için imputation: daha büyük çocuğa git.
        Basit strateji: True dalına git (güvenli taraf).
        """
        # v1: Sabit True (konservatif strateji)
        # v2: node.majority_branch_value gibi meta veri eklenebilir
        return True

    @staticmethod
    def _build_edge_map(root: DecisionTreeNode) -> dict:
        """
        Kök düğümden itibaren tüm ağacı dolaşarak edge_map inşa eder.

        Format: {node_id: {True: child_node, False: child_node}}

        O(N) zaman karmaşıklığı (N = toplam düğüm sayısı)
        """
        from collections import deque

        edge_map: dict = {}
        queue: deque = deque([root])

        while queue:
            current = queue.popleft()
            if current.is_leaf:
                continue

            branches: dict = {}
            if current.child_true:
                branches[True] = current.child_true
                queue.append(current.child_true)
            if current.child_false:
                branches[False] = current.child_false
                queue.append(current.child_false)

            edge_map[current.id] = branches

        return edge_map

    def batch_predict(
        self,
        feature_vectors: list[dict[str, bool]]
    ) -> list[InferenceResult]:
        """
        Birden fazla müşteri için toplu çıkarım.

        Args:
            feature_vectors: feature_vector dict listesi

        Returns:
            InferenceResult listesi (aynı sıra)
        """
        return [self.predict(fv) for fv in feature_vectors]
