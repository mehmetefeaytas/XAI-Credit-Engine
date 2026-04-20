"""
tests/unit/test_tree_builder.py
──────────────────────────────────────────────────────────────────────────────
Karar Ağacı İnşacısı — Birim Testleri

Test kapsamı:
    1. Doğruca ayrılabilen basit dataset → kök düğüm doğru feature seçer
    2. Saf dataset → tek yaprak döner (entropy=0)
    3. Boş dataset → ValueError
    4. Boş feature listesi → ValueError
    5. max_depth kısıtı çalışıyor
    6. Tekil özellik ile ağaç inşası
    7. Dejenere durum: tüm örnekler aynı etiket
    8. Ağaç her zaman binary (bölme her seferinde True/False)
    9. collect_all_nodes BFS sırası doğru
    10. get_edges() tüm kenarları döner
"""

import pytest

from app.engine.tree.tree_builder import TreeBuilder, TreeBuildConfig
from app.engine.math.information_gain import InformationGainCalculator
from app.engine.math.entropy_calculator import EntropyCalculator


# ── Test dataset fabrikaları ─────────────────────────────────────────────────

def make_simple_dataset():
    """
    Basit, tamamen ayrılabilir dataset.
    Kural: income_gt_50k=True → APPROVED, False → REJECTED
    """
    return [
        {"income_gt_50k": True,  "credit_score_gt_700": True,  "decision": True},
        {"income_gt_50k": True,  "credit_score_gt_700": False, "decision": True},
        {"income_gt_50k": True,  "credit_score_gt_700": True,  "decision": True},
        {"income_gt_50k": False, "credit_score_gt_700": True,  "decision": False},
        {"income_gt_50k": False, "credit_score_gt_700": False, "decision": False},
        {"income_gt_50k": False, "credit_score_gt_700": True,  "decision": False},
    ]

def make_pure_dataset():
    """Hepsi APPROVED → entropi 0.0"""
    return [
        {"income_gt_50k": True,  "decision": True},
        {"income_gt_50k": False, "decision": True},
        {"income_gt_50k": True,  "decision": True},
    ]

def make_multifeature_dataset(n_approved=60, n_rejected=40, seed=42):
    """n kayıtlı dengeli dataset."""
    import random
    rng = random.Random(seed)
    features = ["f1", "f2", "f3"]
    rows = []
    for _ in range(n_approved):
        row = {f: True for f in features}
        row["decision"] = True
        rows.append(row)
    for _ in range(n_rejected):
        row = {f: False for f in features}
        row["decision"] = False
        rows.append(row)
    rng.shuffle(rows)
    return rows, features


def make_builder(max_depth=10, min_samples_split=2, min_samples_leaf=1):
    config = TreeBuildConfig(
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
    )
    return TreeBuilder(config=config)


# ── Testler ──────────────────────────────────────────────────────────────────

class TestTreeBuilderBasic:

    def test_simple_dataset_builds_tree(self):
        """Basit dataset'ten kök düğüm oluşturulmalı."""
        builder = make_builder()
        dataset = make_simple_dataset()
        root = builder.build(dataset, ["income_gt_50k", "credit_score_gt_700"], "decision")
        assert root is not None
        assert not root.is_leaf
        # income_gt_50k en yüksek IG'ye sahip olmalı (mükemmel ayırıcı)
        assert root.feature_name == "income_gt_50k"

    def test_pure_dataset_returns_single_leaf(self):
        """Saf dataset → kök kendisi yaprak olmalı (H=0)."""
        builder = make_builder(min_samples_split=1)
        dataset = make_pure_dataset()
        root = builder.build(dataset, ["income_gt_50k"], "decision")
        assert root.is_leaf
        assert root.leaf_label == "APPROVED"
        assert root.entropy == pytest.approx(0.0, abs=1e-9)

    def test_empty_dataset_raises_error(self):
        """Boş dataset → ValueError."""
        builder = make_builder()
        with pytest.raises(ValueError, match="Dataset boş"):
            builder.build([], ["income_gt_50k"], "decision")

    def test_empty_features_raises_error(self):
        """Boş feature listesi → ValueError."""
        builder = make_builder()
        with pytest.raises(ValueError, match="Features listesi boş"):
            builder.build(make_simple_dataset(), [], "decision")

    def test_invalid_label_col_raises_error(self):
        """Geçersiz label_col → ValueError."""
        builder = make_builder()
        with pytest.raises(ValueError, match="bulunamadı"):
            builder.build(make_simple_dataset(), ["income_gt_50k"], "NONEXISTENT")


class TestTreeBuilderStoppingCriteria:

    def test_max_depth_respected(self):
        """max_depth=1 → en fazla 1 seviye bölme yapılmalı."""
        builder = make_builder(max_depth=1, min_samples_split=1, min_samples_leaf=1)
        dataset, features = make_multifeature_dataset()
        root = builder.build(dataset, features, "decision")

        # Kök çocukları yaprak olmalı
        if not root.is_leaf:
            if root.child_true:
                assert root.child_true.depth == 1
            if root.child_false:
                assert root.child_false.depth == 1

    def test_all_same_label_returns_leaf(self):
        """Tüm örnekler REJECTED → kök yaprak olmalı."""
        dataset = [
            {"f1": True,  "f2": False, "decision": False},
            {"f1": False, "f2": True,  "decision": False},
            {"f1": True,  "f2": True,  "decision": False},
        ]
        builder = make_builder(min_samples_split=1)
        root = builder.build(dataset, ["f1", "f2"], "decision")
        assert root.is_leaf
        assert root.leaf_label == "REJECTED"

    def test_min_samples_split_creates_leaf(self):
        """min_samples_split büyük seçilince tüm ağaç tek yaprak."""
        dataset = make_simple_dataset()
        builder = make_builder(min_samples_split=100)  # 6 örnekten çok
        root = builder.build(dataset, ["income_gt_50k", "credit_score_gt_700"], "decision")
        assert root.is_leaf  # min_samples_split aşılamadı → yaprak

    def test_zero_ig_creates_leaf(self):
        """Hiçbir özellik ayrım yapamıyorsa → yaprak."""
        # Tüm özellikler sabit → IG = 0
        dataset = [
            {"f1": True, "f2": True, "decision": True},
            {"f1": True, "f2": True, "decision": False},
            {"f1": True, "f2": True, "decision": True},
            {"f1": True, "f2": True, "decision": False},
        ]
        builder = make_builder(min_samples_split=1, min_samples_leaf=1)
        root = builder.build(dataset, ["f1", "f2"], "decision")
        assert root.is_leaf


class TestTreeBuilderStructure:

    def test_binary_tree_structure(self):
        """Her iç düğümün tam 2 çocuğu olmalı."""
        builder = make_builder()
        dataset, features = make_multifeature_dataset()
        root = builder.build(dataset, features, "decision")
        all_nodes = builder.collect_all_nodes(root)
        for node in all_nodes:
            if not node.is_leaf:
                assert node.child_true is not None, f"child_true eksik: {node}"
                assert node.child_false is not None, f"child_false eksik: {node}"

    def test_collect_all_nodes_includes_root(self):
        """collect_all_nodes kök dahil tüm düğümleri döner."""
        builder = make_builder()
        dataset = make_simple_dataset()
        root = builder.build(dataset, ["income_gt_50k", "credit_score_gt_700"], "decision")
        all_nodes = builder.collect_all_nodes(root)
        assert root in all_nodes

    def test_edges_match_node_count(self):
        """Kenar sayısı = iç düğüm × 2."""
        builder = make_builder()
        dataset, features = make_multifeature_dataset()
        root = builder.build(dataset, features, "decision")
        edges = builder.get_edges()
        all_nodes = builder.collect_all_nodes(root)
        inner_nodes = sum(1 for n in all_nodes if not n.is_leaf)
        # Her iç düğümden 2 kenar çıkar
        assert len(edges) == inner_nodes * 2

    def test_leaf_labels_valid(self):
        """Tüm yaprak etiketleri APPROVED veya REJECTED olmalı."""
        builder = make_builder()
        dataset, features = make_multifeature_dataset()
        root = builder.build(dataset, features, "decision")
        all_nodes = builder.collect_all_nodes(root)
        for node in all_nodes:
            if node.is_leaf:
                assert node.leaf_label in {"APPROVED", "REJECTED"}

    def test_depth_increases_with_level(self):
        """Alt düğümlerin derinliği üst düğüme göre 1 fazla olmalı."""
        builder = make_builder()
        dataset, features = make_multifeature_dataset()
        root = builder.build(dataset, features, "decision")

        def check_depth(node, expected_depth):
            assert node.depth == expected_depth, f"Beklenen {expected_depth}, gelen {node.depth}"
            if not node.is_leaf:
                if node.child_true:
                    check_depth(node.child_true,  expected_depth + 1)
                if node.child_false:
                    check_depth(node.child_false, expected_depth + 1)

        check_depth(root, 0)

    def test_sample_count_propagates(self):
        """Kök sample_count tüm dataset boyutuna eşit olmalı."""
        builder = make_builder()
        dataset, features = make_multifeature_dataset(n_approved=40, n_rejected=40)
        root = builder.build(dataset, features, "decision")
        assert root.sample_count == 80

    def test_get_stats_correct(self):
        """get_stats() makul değerler döner."""
        builder = make_builder()
        dataset, features = make_multifeature_dataset()
        root = builder.build(dataset, features, "decision")
        stats = builder.get_stats()
        assert stats["total_nodes"] > 0
        assert stats["leaf_nodes"] > 0
        assert stats["inner_nodes"] >= 0
        assert stats["total_nodes"] == stats["leaf_nodes"] + stats["inner_nodes"]
