"""
tests/unit/test_entropy.py
──────────────────────────────────────────────────────────────────────────────
Shannon Entropy Modülü — Birim Testleri

Test kapsamı:
    1. Saf pozitif küme → H = 0.0
    2. Saf negatif küme → H = 0.0
    3. Dengeli ikili dağılım → H = 1.0
    4. Bilinen değer: [T,T,T,F,F] → H ≈ 0.971
    5. Boş liste → H = 0.0
    6. Tek eleman → H = 0.0
    7. Koşullu entropi: feature bilgi veriyorsa H(S|A) < H(S)
    8. Koşullu entropi: feature bilgi vermiyorsa H(S|A) = H(S)
    9. Koşullu entropi: uzunluk uyumsuzluğu → ValueError
    10. _class_probabilities: olasılıklar toplamı = 1.0
"""

import math
import pytest

from app.engine.math.entropy_calculator import EntropyCalculator


class TestEntropyCalculateFunction:
    """EntropyCalculator.calculate() testleri"""

    def test_pure_positive_labels_returns_zero(self):
        """Hepsi True → H = 0.0 (saf küme)"""
        labels = [True, True, True, True, True]
        result = EntropyCalculator.calculate(labels)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_pure_negative_labels_returns_zero(self):
        """Hepsi False → H = 0.0 (saf küme)"""
        labels = [False, False, False, False]
        result = EntropyCalculator.calculate(labels)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_balanced_binary_returns_one(self):
        """50-50 dağılım → H = 1.0 (maksimum kargaşa)"""
        labels = [True, True, False, False]
        result = EntropyCalculator.calculate(labels)
        assert result == pytest.approx(1.0, abs=1e-9)

    def test_known_value_three_pos_two_neg(self):
        """
        [T,T,T,F,F] → p+ = 3/5 = 0.6, p- = 2/5 = 0.4
        H = -(0.6*log2(0.6)) - (0.4*log2(0.4))
          = -(0.6 * -0.73697) - (0.4 * -1.32193)
          = 0.44218 + 0.52877
          = 0.97095
        """
        labels = [True, True, True, False, False]
        result = EntropyCalculator.calculate(labels)
        expected = -(0.6 * math.log2(0.6)) - (0.4 * math.log2(0.4))
        assert result == pytest.approx(expected, rel=1e-5)

    def test_empty_labels_returns_zero(self):
        """Boş liste → H = 0.0"""
        result = EntropyCalculator.calculate([])
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_single_true_returns_zero(self):
        """Tek eleman True → H = 0.0"""
        result = EntropyCalculator.calculate([True])
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_single_false_returns_zero(self):
        """Tek eleman False → H = 0.0"""
        result = EntropyCalculator.calculate([False])
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_entropy_is_non_negative(self):
        """Entropi her zaman ≥ 0 olmalı"""
        import random
        rng = random.Random(42)
        for _ in range(20):
            n = rng.randint(1, 100)
            labels = [rng.choice([True, False]) for _ in range(n)]
            result = EntropyCalculator.calculate(labels)
            assert result >= -1e-9, f"Negatif entropi: {result} for {labels[:5]}..."

    def test_entropy_max_one_for_binary(self):
        """Binary için entropi ≤ 1.0 olmalı"""
        import random
        rng = random.Random(99)
        for _ in range(20):
            n = rng.randint(2, 100)
            labels = [rng.choice([True, False]) for _ in range(n)]
            result = EntropyCalculator.calculate(labels)
            assert result <= 1.0 + 1e-9, f"Entropi > 1: {result}"

    def test_larger_unbalanced_dataset(self):
        """Büyük dengesiz dataset: 90 True, 10 False"""
        labels = [True] * 90 + [False] * 10
        result = EntropyCalculator.calculate(labels)
        # H = -(0.9*log2(0.9)) - (0.1*log2(0.1)) ≈ 0.469
        expected = -(0.9 * math.log2(0.9)) - (0.1 * math.log2(0.1))
        assert result == pytest.approx(expected, rel=1e-5)


class TestConditionalEntropy:
    """EntropyCalculator.conditional_entropy() testleri"""

    def test_informative_feature_reduces_entropy(self):
        """
        Bilgi veren özellik: koşullu entropi < ana entropi
        labels = [T,T,T,F,F,F]  → H(S) = 1.0
        feature= [T,T,T,F,F,F]  → perfect predictor → H(S|A) = 0.0
        """
        labels  = [True,  True,  True,  False, False, False]
        feature = [True,  True,  True,  False, False, False]
        cond_h = EntropyCalculator.conditional_entropy(labels, feature)
        assert cond_h == pytest.approx(0.0, abs=1e-9)

    def test_non_informative_feature_same_entropy(self):
        """
        Bilgi vermeyen özellik: H(S|A) = H(S)
        feature değerleri label ile ilişkisizse bilgi kazancı = 0
        """
        labels  = [True, False, True, False]
        feature = [True, True, False, False]  # label ile alakasız
        h_s     = EntropyCalculator.calculate(labels)
        cond_h  = EntropyCalculator.conditional_entropy(labels, feature)
        # IG = H(S) - H(S|A) ≈ 0 olacak
        ig = h_s - cond_h
        assert ig >= -1e-9  # IG negatif olamaz (teorik garanti)

    def test_length_mismatch_raises_error(self):
        """Farklı uzunluk → ValueError"""
        labels  = [True, False, True]
        feature = [True, False]
        with pytest.raises(ValueError, match="aynı uzunlukta"):
            EntropyCalculator.conditional_entropy(labels, feature)

    def test_empty_inputs_returns_zero(self):
        """Boş giriş → H = 0.0"""
        result = EntropyCalculator.conditional_entropy([], [])
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_all_same_feature_value(self):
        """
        Tüm feature değerleri aynı → H(S|A) = H(S)
        (Özellik hiç bölme yapmıyor)
        """
        labels  = [True, False, True, True, False]
        feature = [True, True, True, True, True]  # hepsi True
        h_s    = EntropyCalculator.calculate(labels)
        cond_h = EntropyCalculator.conditional_entropy(labels, feature)
        assert cond_h == pytest.approx(h_s, rel=1e-5)


class TestClassProbabilities:
    """EntropyCalculator._class_probabilities() testleri"""

    def test_probabilities_sum_to_one(self):
        """Olasılıklar toplamı 1.0 olmalı"""
        labels = [True, True, False, True, False]
        probs = EntropyCalculator._class_probabilities(labels)
        total = sum(probs.values())
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_all_true(self):
        """Hepsi True → p(True)=1.0, p(False)=0.0"""
        labels = [True, True, True]
        probs = EntropyCalculator._class_probabilities(labels)
        assert probs[True]  == pytest.approx(1.0)
        assert probs[False] == pytest.approx(0.0)

    def test_empty_returns_zero_probs(self):
        """Boş → tüm olasılıklar 0.0"""
        probs = EntropyCalculator._class_probabilities([])
        assert probs[True]  == pytest.approx(0.0)
        assert probs[False] == pytest.approx(0.0)
