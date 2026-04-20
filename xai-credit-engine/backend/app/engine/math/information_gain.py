"""
engine/math/information_gain.py
──────────────────────────────────────────────────────────────────────────────
Information Gain (Bilgi Kazancı) hesaplama modülü.

Matematiksel formüller:
    IG(S, A)       = H(S) - H(S|A)
    SplitInfo(S,A) = -Σ (|S_v|/|S|) * log₂(|S_v|/|S|)
    GainRatio(S,A) = IG(S,A) / SplitInfo(S,A)

Neden GainRatio?
    - IG, çok-değerli özellikleri (yüksek dallanma) aşırı tercih eder.
    - GainRatio bu önyargıyı düzelterek dengeli bölme yapar (C4.5 yöntemi).
"""

import math
from typing import Sequence

from app.engine.math.entropy_calculator import EntropyCalculator


class InformationGainCalculator:
    """
    Bilgi kazancı, split bilgisi ve gain ratio hesapları.

    Bağımlılık: EntropyCalculator (constructor injection)

    Kullanım:
        calc = InformationGainCalculator(EntropyCalculator())
        ig = calc.information_gain(labels, feature_values)
        ranked = calc.rank_features(dataset, "decision", feature_cols)
    """

    def __init__(self, entropy_calc: EntropyCalculator | None = None):
        """
        Args:
            entropy_calc: EntropyCalculator örneği. None ise varsayılan oluşturulur.
        """
        self._entropy = entropy_calc or EntropyCalculator()

    def information_gain(
        self,
        labels: Sequence[bool],
        feature_values: Sequence[bool]
    ) -> float:
        """
        IG(S, A) = H(S) - H(S|A)

        Args:
            labels:         Sınıf etiketleri
            feature_values: Özellik değerleri

        Returns:
            float — Bilgi kazancı (≥ 0.0)
        """
        h_s = EntropyCalculator.calculate(labels)
        h_s_a = EntropyCalculator.conditional_entropy(labels, feature_values)
        return h_s - h_s_a

    def split_info(
        self,
        labels: Sequence[bool],
        feature_values: Sequence[bool]
    ) -> float:
        """
        SplitInfo(S, A) = -Σ (|S_v|/|S|) * log₂(|S_v|/|S|)

        Özelliğin A'nın ne kadar dallandırdığını ölçer.
        Yüksek SplitInfo → özellik çok dallanıyor → GainRatio düşer.

        Returns:
            float — Split bilgisi değeri (≥ 0.0)
        """
        total = len(labels)
        if total == 0:
            return 0.0

        # True ve False gruplarının boyutlarını say
        counts: dict[bool, int] = {True: 0, False: 0}
        for fval in feature_values:
            counts[fval] += 1

        split = 0.0
        for count in counts.values():
            if count == 0:
                continue
            ratio = count / total
            split -= ratio * math.log2(ratio)

        return split

    def gain_ratio(
        self,
        labels: Sequence[bool],
        feature_values: Sequence[bool]
    ) -> float:
        """
        GainRatio(S, A) = IG(S, A) / SplitInfo(S, A)

        SplitInfo = 0 ise → 0.0 döner (sıfıra bölme koruması).

        Returns:
            float — Gain ratio değeri
        """
        ig = self.information_gain(labels, feature_values)
        si = self.split_info(labels, feature_values)

        if si == 0.0:
            return 0.0

        return ig / si

    def rank_features(
        self,
        dataset: list[dict],
        label_col: str,
        feature_cols: list[str],
        use_gain_ratio: bool = False
    ) -> list[tuple[str, float]]:
        """
        Tüm özellikleri IG (veya GainRatio) değerine göre sıralar.

        Args:
            dataset:        Satır bazlı dict listesi
            label_col:      Hedef sütun adı (True/False Boolean değeri)
            feature_cols:   Değerlendirilecek özellik sütunları
            use_gain_ratio: True ise GainRatio kullanır, False ise IG

        Returns:
            [(feature_name, score), ...] — Azalan sıralamayla

        Örnek çıktı:
            [
              ("credit_score_gt_700",  0.4193),
              ("income_gt_50k",        0.3812),
              ("has_prior_default",    0.3541),
              ...
            ]
        """
        labels: list[bool] = [row[label_col] for row in dataset]
        results: list[tuple[str, float]] = []

        for feature in feature_cols:
            feature_values: list[bool] = [row[feature] for row in dataset]

            if use_gain_ratio:
                score = self.gain_ratio(labels, feature_values)
            else:
                score = self.information_gain(labels, feature_values)

            results.append((feature, score))

        # Azalan sıra (en yüksek IG en önce)
        results.sort(key=lambda x: x[1], reverse=True)
        return results
