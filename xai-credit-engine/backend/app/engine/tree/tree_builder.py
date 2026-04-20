"""
engine/tree/tree_builder.py
──────────────────────────────────────────────────────────────────────────────
ID3 Tabanlı Karar Ağacı İnşacısı — Sıfırdan Implementasyon

Bu modül scikit-learn veya başka ML kütüphanesi KULLANMAZ.
Tüm matematik sıfırdan uygulanmıştır.

Algoritma: ID3 (Iterative Dichotomiser 3) — Quinlan, 1986
    1. Kümede entropi hesapla
    2. Her özellik için Information Gain hesapla
    3. En yüksek IG'li özelliği seç (bölme kriteri)
    4. Veriyi True/False grubuna böl
    5. Her grup için recursive olarak tekrarla

Durdurma Kriterleri (Stopping Criteria):
    [1] Veri boş
    [2] Tüm etiketler aynı (saf düğüm) → H = 0
    [3] Özellik listesi boş
    [4] max_depth aşıldı
    [5] Örnek sayısı min_samples_split altında
    [6] En iyi IG = 0 (hiçbir özellik ayrım yapamıyor)
    [7] Bölünecek dal min_samples_leaf altında

Karmaşıklık:
    Eğitim: O(n × m × log n)   [n=örnek, m=özellik]
    Alan:   O(n + m × d)        [d=derinlik]
"""

from dataclasses import dataclass, field
from typing import Optional

from app.domain.models.decision_node import DecisionTreeEdge, DecisionTreeNode
from app.engine.math.information_gain import InformationGainCalculator
from app.engine.math.entropy_calculator import EntropyCalculator


@dataclass
class TreeBuildConfig:
    """
    Karar ağacı inşa konfigürasyonu.

    Attributes:
        max_depth:           Maksimum ağaç derinliği (aşırı öğrenmeyi önler)
        min_samples_split:   Bölme için minimum örnek sayısı
        min_samples_leaf:    Yaprak için minimum örnek sayısı
        use_gain_ratio:      True=GainRatio, False=InformationGain
        tie_break_feature:   Eşitlik durumunda özellik seçimi: "first" | "random"
    """
    max_depth:           int  = 10
    min_samples_split:   int  = 5
    min_samples_leaf:    int  = 2
    use_gain_ratio:      bool = False
    tie_break_feature:   str  = "first"   # "first" → alfabetik ilk


class TreeBuilder:
    """
    ID3 tabanlı ikili karar ağacı inşacısı.

    Kullanım:
        config  = TreeBuildConfig(max_depth=6, min_samples_split=5)
        builder = TreeBuilder(config=config)
        root    = builder.build(dataset, feature_cols, label_col="decision")
        edges   = builder.get_edges()
    """

    def __init__(
        self,
        config: TreeBuildConfig | None = None,
        ig_calculator: InformationGainCalculator | None = None,
    ):
        self._config = config or TreeBuildConfig()
        self._ig_calc = ig_calculator or InformationGainCalculator(EntropyCalculator())
        self._edges: list[DecisionTreeEdge] = []
        self._node_count: int = 0
        self._leaf_count:  int = 0

    def build(
        self,
        dataset: list[dict],
        features: list[str],
        label_col: str = "decision"
    ) -> DecisionTreeNode:
        """
        Ana giriş noktası. Kök düğümü döner.

        Args:
            dataset:   Satır bazlı dict listesi. Her satır feature ve label içermeli.
            features:  Boolean özellik sütun adları listesi
            label_col: Hedef sütun adı (True=APPROVED, False=REJECTED)

        Returns:
            Kök DecisionTreeNode (çocuklara child_true/child_false ile erişilir)

        Raises:
            ValueError: dataset veya features boşsa
        """
        if not dataset:
            raise ValueError("Dataset boş olamaz.")
        if not features:
            raise ValueError("Features listesi boş olamaz.")
        if label_col not in dataset[0]:
            raise ValueError(f"label_col '{label_col}' dataset'te bulunamadı.")

        # Her build çağrısında sıfırla
        self._edges = []
        self._node_count = 0
        self._leaf_count = 0

        root = self._build_recursive(
            data=dataset,
            features=list(features),
            label_col=label_col,
            depth=0,
            parent_data=dataset  # parent majority class için
        )

        return root

    def _build_recursive(
        self,
        data: list[dict],
        features: list[str],
        label_col: str,
        depth: int,
        parent_data: list[dict]
    ) -> DecisionTreeNode:
        """
        Recursive ID3 inşacısı.

        Stopping criteria sırayla kontrol edilir:
        [1] Boş veri → parent majority sınıfından yaprak
        [2] Saf küme → saf yaprak
        [3] Özellik bitti → majority vote yaprak
        [4] max_depth aşıldı → majority vote yaprak
        [5] min_samples_split altında → majority vote yaprak
        [6] Best IG = 0 → majority vote yaprak
        """
        self._node_count += 1

        labels: list[bool] = [row[label_col] for row in data]

        # ── [1] BOŞ VERİ ─────────────────────────────────────────────────────
        if len(data) == 0:
            return self._make_leaf(parent_data, label_col, depth)

        # ── [2] SAF KÜME ─────────────────────────────────────────────────────
        h = EntropyCalculator.calculate(labels)
        if abs(h) < 1e-9:  # H = 0.0 (tüm etiketler aynı)
            self._leaf_count += 1
            majority = labels[0]  # hepsi aynı
            return DecisionTreeNode(
                is_leaf=True,
                leaf_label="APPROVED" if majority else "REJECTED",
                depth=depth,
                entropy=0.0,
                sample_count=len(data),
                majority_class_count=len(data),
            )

        # ── [3] ÖZELLİK BİTTİ ───────────────────────────────────────────────
        if not features:
            return self._make_leaf(data, label_col, depth)

        # ── [4] MAX DEPTH ────────────────────────────────────────────────────
        if depth >= self._config.max_depth:
            return self._make_leaf(data, label_col, depth)

        # ── [5] MIN SAMPLES SPLIT ────────────────────────────────────────────
        if len(data) < self._config.min_samples_split:
            return self._make_leaf(data, label_col, depth)

        # ── EN İYİ ÖZELLİĞİ SEÇ ─────────────────────────────────────────────
        ranked = self._ig_calc.rank_features(
            dataset=data,
            label_col=label_col,
            feature_cols=features,
            use_gain_ratio=self._config.use_gain_ratio,
        )

        # ── [6] BEST IG = 0 ──────────────────────────────────────────────────
        if not ranked or ranked[0][1] <= 0.0:
            return self._make_leaf(data, label_col, depth)

        # Eşitlik çözümü: config.tie_break_feature
        best_score = ranked[0][1]
        tied = [f for f, s in ranked if abs(s - best_score) < 1e-9]
        if self._config.tie_break_feature == "first":
            best_feature = min(tied)  # Alfabetik küçük
        else:
            import random
            best_feature = random.choice(tied)

        # ── DÜĞÜM OLUŞTUR ─────────────────────────────────────────────────────
        node = DecisionTreeNode(
            feature_name=best_feature,
            depth=depth,
            entropy=h,
            sample_count=len(data),
            is_leaf=False,
        )

        # ── VERİYİ BÖLE ──────────────────────────────────────────────────────
        data_true  = [row for row in data if row[best_feature] is True]
        data_false = [row for row in data if row[best_feature] is False]

        remaining_features = [f for f in features if f != best_feature]

        # ── [7] MIN SAMPLES LEAF ─────────────────────────────────────────────
        if len(data_true) < self._config.min_samples_leaf:
            node.child_true = self._make_leaf(data, label_col, depth + 1)
        else:
            node.child_true = self._build_recursive(
                data=data_true,
                features=remaining_features,
                label_col=label_col,
                depth=depth + 1,
                parent_data=data
            )

        if len(data_false) < self._config.min_samples_leaf:
            node.child_false = self._make_leaf(data, label_col, depth + 1)
        else:
            node.child_false = self._build_recursive(
                data=data_false,
                features=remaining_features,
                label_col=label_col,
                depth=depth + 1,
                parent_data=data
            )

        # ── KENARLAR ─────────────────────────────────────────────────────────
        edge_true = DecisionTreeEdge(
            source_node_id=node.id,
            target_node_id=node.child_true.id,
            branch_value=True,
        )
        edge_false = DecisionTreeEdge(
            source_node_id=node.id,
            target_node_id=node.child_false.id,
            branch_value=False,
        )
        self._edges.extend([edge_true, edge_false])

        return node

    def _make_leaf(
        self,
        data: list[dict],
        label_col: str,
        depth: int
    ) -> DecisionTreeNode:
        """
        Çoğunluk oyuna (majority vote) göre yaprak düğümü üretir.

        Eşit dağılım (pos == neg) → "REJECTED"
        (Finansal ihtiyat ilkesi: şüpheli durumda reddet)
        """
        self._leaf_count += 1

        labels: list[bool] = [row[label_col] for row in data]
        pos_count = sum(1 for lbl in labels if lbl is True)
        neg_count = len(labels) - pos_count

        # Eşitlik → REJECTED
        majority = pos_count > neg_count
        leaf_label = "APPROVED" if majority else "REJECTED"

        entropy = EntropyCalculator.calculate(labels) if labels else 0.0
        majority_count = pos_count if majority else neg_count

        return DecisionTreeNode(
            is_leaf=True,
            leaf_label=leaf_label,
            depth=depth,
            entropy=entropy,
            sample_count=len(labels),
            majority_class_count=majority_count,
        )

    def get_edges(self) -> list[DecisionTreeEdge]:
        """Build sonrası tüm kenarları döner."""
        return list(self._edges)

    def get_stats(self) -> dict:
        """Son build için istatistikler."""
        return {
            "total_nodes":  self._node_count,
            "leaf_nodes":   self._leaf_count,
            "inner_nodes":  self._node_count - self._leaf_count,
            "total_edges":  len(self._edges),
        }

    def collect_all_nodes(self, root: DecisionTreeNode) -> list[DecisionTreeNode]:
        """
        Ağacı BFS ile dolaşarak tüm düğümleri döner.

        Args:
            root: Kök düğüm

        Returns:
            Tüm DecisionTreeNode listesi (BFS sıralaması)
        """
        from collections import deque

        nodes: list[DecisionTreeNode] = []
        queue: deque[DecisionTreeNode] = deque([root])

        while queue:
            current = queue.popleft()
            nodes.append(current)
            if not current.is_leaf:
                if current.child_true:
                    queue.append(current.child_true)
                if current.child_false:
                    queue.append(current.child_false)

        return nodes
