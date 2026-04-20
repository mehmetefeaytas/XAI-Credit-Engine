"""
engine/math/truth_table_builder.py
──────────────────────────────────────────────────────────────────────────────
Önerme Kümesi → Doğruluk Tablosu Üreticisi

N Boolean özellik için 2^N satırlı combinatorial doğruluk tablosu üretir.
Bu tablo, karar ağacının olası tüm karar yollarını temsil eder.

Matematiksel temel:
    N özellik için doğruluk uzayı: {T,F}^N  →  2^N kombinasyon
    Her satır bir "müşteri profili" örnekler.

Kullanım alanı:
    - Boolean formülü doğrulama (XAI çıktısı truth table ile tutarlı mı?)
    - CNF/DNF dönüşümü için girdi
    - Akademik ispat: ağaç kararları truth table ile eşdeğer mi?
"""

import itertools
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class TruthTableRow:
    """
    Doğruluk tablosunun tek bir satırı.

    Attributes:
        feature_names:  Özellik adları listesi (sütun isimleri)
        assignments:    Her özellik için True/False değerleri
        outcome:        Bu kombinasyon için karar ağacının kararı (başlangıçta None)
    """
    feature_names: list[str]
    assignments:   list[bool]
    outcome:       bool | None = None  # None = henüz değerlendirilmedi

    def to_dict(self) -> dict[str, bool]:
        """Özellik adı → değer eşlemesi döner."""
        return dict(zip(self.feature_names, self.assignments))

    def to_conjunction(self) -> str:
        """
        AND(P1 ∧ P2 ∧ ...) formatında Boolean formül döner.

        Örnek:
            features = ["income_gt_50k", "credit_score_gt_700"]
            assignments = [True, False]
            → "(income_gt_50k=T) ∧ (¬credit_score_gt_700)"
        """
        clauses = []
        for fname, asgn in zip(self.feature_names, self.assignments):
            if asgn:
                clauses.append(f"({fname}=T)")
            else:
                clauses.append(f"(¬{fname})")
        return " ∧ ".join(clauses)

    def __repr__(self) -> str:
        vals = ", ".join(
            f"{n}={'T' if v else 'F'}"
            for n, v in zip(self.feature_names, self.assignments)
        )
        outcome_str = "?" if self.outcome is None else ("APPROVED" if self.outcome else "REJECTED")
        return f"TruthTableRow({vals}) → {outcome_str}"


class TruthTableBuilder:
    """
    N Boolean özellik için 2^N satırlı doğruluk tablosu üreticisi.

    Kullanım:
        builder = TruthTableBuilder()
        table = builder.build(["income_gt_50k", "credit_score_gt_700", "has_prior_default"])
        # → 8 satırlı TruthTableRow listesi (2^3 = 8)
    """

    def build(self, feature_names: Sequence[str]) -> list[TruthTableRow]:
        """
        Tüm kombinasyonları oluşturur.

        Args:
            feature_names: Boolean özellik adları

        Returns:
            2^N adet TruthTableRow listesi (Gray code sıralamasında değil, standart)

        Raises:
            ValueError: feature_names boşsa veya çok büyükse (N > 20 practical limit)
        """
        n = len(feature_names)
        if n == 0:
            raise ValueError("feature_names boş olamaz.")
        if n > 20:
            raise ValueError(
                f"Özellik sayısı çok büyük (N={n}). "
                f"Doğruluk tablosu 2^{n} = {2**n} satır içerir. "
                f"Pratik limit N ≤ 20 (1.048.576 satır)."
            )

        feature_list = list(feature_names)
        rows: list[TruthTableRow] = []

        # itertools.product ile {True, False}^N üret
        for combo in itertools.product([True, False], repeat=n):
            rows.append(
                TruthTableRow(
                    feature_names=feature_list,
                    assignments=list(combo),
                    outcome=None,
                )
            )

        return rows

    def fill_outcomes(
        self,
        rows: list[TruthTableRow],
        predictor: "callable"
    ) -> list[TruthTableRow]:
        """
        Doğruluk tablosu satırlarını bir karar fonksiyonuyla doldurur.

        Args:
            rows:      TruthTableRow listesi (build() çıktısı)
            predictor: dict[str,bool] → bool alan callable
                       (örn: InferenceEngine.predict_bool)

        Returns:
            outcome alanı doldurulmuş satırlar
        """
        for row in rows:
            feature_vector = row.to_dict()
            row.outcome = predictor(feature_vector)
        return rows

    def to_dnf(self, rows: list[TruthTableRow], target_outcome: bool = True) -> str:
        """
        Belirli bir sonuca (örn: APPROVED=True) karşılık gelen satırları
        DNF (Disjunctive Normal Form) formatına dönüştürür.

        DNF: (P1 ∧ P2) ∨ (P3 ∧ ¬P4) ∨ ...

        Args:
            rows:           Doldurulmuş TruthTableRow listesi
            target_outcome: True ise APPROVED mintermleri, False ise REJECTED

        Returns:
            DNF formülü string

        Örnek:
            → "(income_gt_50k=T ∧ credit_score_gt_700=T) ∨ (¬income_gt_50k ∧ credit_score_gt_700=T)"
        """
        minterms = [
            row.to_conjunction()
            for row in rows
            if row.outcome == target_outcome
        ]

        if not minterms:
            label = "APPROVED" if target_outcome else "REJECTED"
            return f"∅  (hiçbir satır {label} değil)"

        return " ∨\n".join(f"({term})" for term in minterms)

    @staticmethod
    def summary(rows: list[TruthTableRow]) -> dict:
        """
        Tablo özet istatistikleri.

        Returns:
            {total, approved_count, rejected_count, unevaluated_count}
        """
        approved   = sum(1 for r in rows if r.outcome is True)
        rejected   = sum(1 for r in rows if r.outcome is False)
        unevaluated= sum(1 for r in rows if r.outcome is None)
        return {
            "total":             len(rows),
            "approved_count":    approved,
            "rejected_count":    rejected,
            "unevaluated_count": unevaluated,
        }
