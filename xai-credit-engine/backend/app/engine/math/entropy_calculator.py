"""
engine/math/entropy_calculator.py
──────────────────────────────────────────────────────────────────────────────
Shannon Entropy (Bilgi Entropisi) hesaplama modülü.

Matematiksel temel:
    H(S) = -Σ p_i * log₂(p_i)       (binary: sadece APPROVED/REJECTED)
    H(S|A) = Σ (|S_v|/|S|) * H(S_v)

Sınır değerler:
    - Saf node  (tümü aynı sınıf):  H = 0.0
    - Dengeli 50-50 dağılım:         H = 1.0 (binary)
"""

import math
from typing import Sequence


class EntropyCalculator:
    """
    Binary sınıflandırma için Shannon Entropy hesabı.

    Kullanım:
        labels = [True, True, False, True, False]
        H = EntropyCalculator.calculate(labels)  # → ~0.971
    """

    @staticmethod
    def calculate(labels: Sequence[bool]) -> float:
        """
        H(S) = -Σ p_i * log₂(p_i) hesabı.

        Args:
            labels: Boolean sınıf etiketleri (True=APPROVED, False=REJECTED)

        Returns:
            float ∈ [0.0, 1.0] — Entropi değeri

        Örnekler:
            [T,T,T,T,T]         → 0.0   (saf, hepsi True)
            [T,T,F,F]           → 1.0   (dengeli dağılım)
            [T,T,T,F,F]         → 0.971 (3/5 T, 2/5 F)
        """
        if len(labels) == 0:
            return 0.0

        probs = EntropyCalculator._class_probabilities(labels)
        entropy = 0.0

        for p in probs.values():
            if p > 0.0:
                entropy -= p * math.log2(p)

        return entropy

    @staticmethod
    def conditional_entropy(
        labels: Sequence[bool],
        feature_values: Sequence[bool]
    ) -> float:
        """
        H(S|A) = Σ (|S_v|/|S|) * H(S_v)

        Bir özellik (A) değerlerine göre ağırlıklı ortalama entropi.

        Args:
            labels:         Boolean sınıf etiketleri
            feature_values: Boolean özellik değerleri (aynı uzunlukta)

        Returns:
            float — Koşullu entropi değeri

        Raises:
            ValueError: labels ve feature_values uzunlukları farklıysa
        """
        if len(labels) != len(feature_values):
            raise ValueError(
                f"labels ve feature_values aynı uzunlukta olmalı: "
                f"{len(labels)} != {len(feature_values)}"
            )

        if len(labels) == 0:
            return 0.0

        total = len(labels)

        # Alt kümelere ayır: True grubu ve False grubu
        subsets: dict[bool, list[bool]] = {True: [], False: []}
        for label, fval in zip(labels, feature_values):
            subsets[fval].append(label)

        cond_h = 0.0
        for _fval, subset_labels in subsets.items():
            if len(subset_labels) == 0:
                continue
            weight = len(subset_labels) / total
            subset_h = EntropyCalculator.calculate(subset_labels)
            cond_h += weight * subset_h

        return cond_h

    @staticmethod
    def _class_probabilities(labels: Sequence[bool]) -> dict[bool, float]:
        """
        Sınıf olasılıklarını hesaplar.

        Args:
            labels: Boolean etiket listesi

        Returns:
            {True: p_positive, False: p_negative}
        """
        total = len(labels)
        if total == 0:
            return {True: 0.0, False: 0.0}

        pos_count = sum(1 for lbl in labels if lbl)
        neg_count = total - pos_count

        return {
            True:  pos_count / total,
            False: neg_count / total,
        }
