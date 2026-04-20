"""
engine/xai/explanation_generator.py
──────────────────────────────────────────────────────────────────────────────
XAI Açıklama Üreticisi — Boolean Formülü ve Doğal Dil Raporu

Bu modül, karar ağacının yürüttüğü path'i alarak:
    1. Boolean AND zinciri formülü üretir
    2. DNF (Disjunctive Normal Form) formatına dönüştürür
    3. Doğal dil (Türkçe) raporu üretir
    4. Teknik adım logu oluşturur

Çıktı örneği:
    Boolean: (credit_score ≥ 700) ∧ (income > 50000) ∧ ¬(has_prior_default)
    NL Rapor: "Kredi başvurusu ONAYLANDI. Gerekçe: ..."
    Tech Log: "Adım 1: Node[...] | Feature: credit_score..."

GDPR Madde 22 uyumu:
    Her otomatik karar için insan tarafından anlaşılabilir gerekçe üretilmesi
    yasal zorunluluktur. Bu modül bu gereksinimi karşılar.
"""

from dataclasses import dataclass
from typing import Optional

from app.engine.inference.inference_engine import InferenceStep


# ── Özellik Türkçe Etiketleri ────────────────────────────────────────────────
FEATURE_LABELS_TR: dict[str, str] = {
    "income_gt_50k":         "Yıllık gelir",
    "credit_score_gt_700":   "Kredi puanı",
    "has_prior_default":     "Geçmiş icra/temerrüt kaydı",
    "debt_to_income_lt_35":  "Borç/gelir oranı",
    "employment_employed":   "Çalışma durumu",
    "age_gte_25":            "Müşteri yaşı",
    "existing_credits_lt_3": "Mevcut aktif kredi sayısı",
}

# ── Operatör Türkçe Etiketleri ────────────────────────────────────────────────
OPERATOR_LABELS_TR: dict[str, str] = {
    "GTE": "en az",
    "LTE": "en fazla",
    "GT":  "üzerinde",
    "LT":  "altında",
    "EQ":  "eşit",
    "NEQ": "farklı",
}

# ── Özellik Boolean Açıklamaları ─────────────────────────────────────────────
FEATURE_CONDITION_TR: dict[str, dict[bool, str]] = {
    "income_gt_50k": {
        True:  "Yıllık gelir 50.000 TL üzerinde ✓",
        False: "Yıllık gelir 50.000 TL veya altında ✗",
    },
    "credit_score_gt_700": {
        True:  "Kredi puanı 700 veya üzerinde ✓",
        False: "Kredi puanı 700 altında ✗",
    },
    "has_prior_default": {
        True:  "Geçmişte icra/temerrüt kaydı mevcut ✗",
        False: "Geçmişte icra/temerrüt kaydı yok ✓",
    },
    "debt_to_income_lt_35": {
        True:  "Borç/gelir oranı %35 altında ✓",
        False: "Borç/gelir oranı %35 veya üzerinde ✗",
    },
    "employment_employed": {
        True:  "Maaşlı çalışan statüsünde ✓",
        False: "Maaşlı çalışan değil ✗",
    },
    "age_gte_25": {
        True:  "Yaş 25 veya üzerinde ✓",
        False: "Yaş 25 altında ✗",
    },
    "existing_credits_lt_3": {
        True:  "Mevcut aktif kredi sayısı 3'ten az ✓",
        False: "Mevcut aktif kredi sayısı 3 veya daha fazla ✗",
    },
}


@dataclass
class ExplanationOutput:
    """
    XAI Açıklama çıktısı.

    Attributes:
        boolean_formula:  AND zinciri formülü (teknik)
        dnf_formula:      DNF formatı (akademik/bonus)
        natural_language: Doğal dil Türkçe raporu (GDPR uyumu)
        technical_log:    Adım adım teknik log (audit)
    """
    boolean_formula:  str
    dnf_formula:      str
    natural_language: str
    technical_log:    str

    def to_dict(self) -> dict:
        return {
            "boolean_formula":  self.boolean_formula,
            "dnf_formula":      self.dnf_formula,
            "natural_language": self.natural_language,
            "technical_log":    self.technical_log,
        }

    def __repr__(self) -> str:
        return (
            f"ExplanationOutput(\n"
            f"  formula='{self.boolean_formula[:60]}...'\n"
            f"  nl_report_chars={len(self.natural_language)}\n"
            f")"
        )


class ExplanationGenerator:
    """
    Karar path'inden XAI açıklaması üretir.

    Kullanım:
        generator = ExplanationGenerator()
        output = generator.generate(
            path=inference_result.path,
            decision="APPROVED",
            language="tr"
        )
        print(output.natural_language)
    """

    def __init__(self, feature_labels: Optional[dict] = None):
        """
        Args:
            feature_labels: Özelleştirilmiş Türkçe etiketler.
                            None ise FEATURE_LABELS_TR kullanılır.
        """
        self._feature_labels = feature_labels or FEATURE_LABELS_TR

    def generate(
        self,
        path: list[InferenceStep],
        decision: str,
        language: str = "tr"
    ) -> ExplanationOutput:
        """
        Ana üretim fonksiyonu.

        Args:
            path:     InferenceStep listesi (InferenceEngine.predict() çıktısı)
            decision: "APPROVED" veya "REJECTED"
            language: "tr" (Türkçe) veya "en" (İngilizce — v2 scope)

        Returns:
            ExplanationOutput ile 4 format
        """
        bool_formula = self._path_to_boolean_formula(path)
        dnf_formula  = self._boolean_formula_to_dnf(path, decision)
        nl_report    = self._formula_to_natural_language(path, decision, language)
        tech_log     = self._build_technical_log(path, decision)

        return ExplanationOutput(
            boolean_formula=bool_formula,
            dnf_formula=dnf_formula,
            natural_language=nl_report,
            technical_log=tech_log,
        )

    def _path_to_boolean_formula(self, path: list[InferenceStep]) -> str:
        """
        Path → Boolean AND zinciri formülü.

        Örnek:
            path adımları:
                credit_score_gt_700=True  → (credit_score_gt_700 = T)
                income_gt_50k=True        → (income_gt_50k = T)
                has_prior_default=False   → ¬(has_prior_default = T)

            Çıktı:
                (credit_score_gt_700 = T) ∧ (income_gt_50k = T) ∧ ¬(has_prior_default = T)
        """
        clauses: list[str] = []

        for step in path:
            feature = step.feature
            branch  = step.branch_taken

            if branch:
                clause = f"({feature} = T)"
            else:
                clause = f"¬({feature} = T)"

            clauses.append(clause)

        if not clauses:
            return "∅ (boş path)"

        return " ∧ ".join(clauses)

    @staticmethod
    def _boolean_formula_to_dnf(
        path: list[InferenceStep],
        decision: str
    ) -> str:
        """
        Mevcut path'i DNF mintermi olarak döner.

        Not: Tam DNF için tüm APPROVED path'lerinin birleşimi gerekir.
        Bu fonksiyon yalnızca mevcut kararın path'ini DNF biçiminde sunar.
        Tam DNF için TruthTableBuilder.to_dnf() kullanılmalı.

        Örnek:
            decision=APPROVED için:
            (credit_score_gt_700=T) ∧ (income_gt_50k=T) ∧ ¬(has_prior_default=T)

            Bu tek bir minterm'dir. Tam DNF: tüm APPROVED path'lerinin ∨ birleşimi.
        """
        clauses: list[str] = []
        for step in path:
            if step.branch_taken:
                clauses.append(f"{step.feature}=T")
            else:
                clauses.append(f"¬{step.feature}")

        conjunction = " ∧ ".join(clauses) if clauses else "∅"
        decision_label = "APPROVED" if decision == "APPROVED" else "REJECTED"
        return f"[{decision_label}] {conjunction}"

    def _formula_to_natural_language(
        self,
        path: list[InferenceStep],
        decision: str,
        lang: str = "tr"
    ) -> str:
        """
        Path → Doğal dil Türkçe raporu.

        Format:
            Kredi başvurusu ONAYLANDI / REDDEDİLDİ.

            Değerlendirilen Kriterler:
            ✓ Kredi puanı 700 veya üzerinde
            ✓ Yıllık gelir 50.000 TL üzerinde
            ✗ Geçmişte icra/temerrüt kaydı yok

            Karar Gerekçesi:
            Yukarıdaki kriterlerin tümünün sağlanması sonucunda...
        """
        if decision == "APPROVED":
            header = "✅ Kredi başvurusu ONAYLANDI.\n"
            summary_line = (
                "\n📋 Karar Gerekçesi:\n"
                "Değerlendirilen kriterlerin tümü başarıyla karşılandığından "
                "kredi başvurusu otomatik sistem tarafından onaylanmıştır."
            )
        else:
            header = "❌ Kredi başvurusu REDDEDİLDİ.\n"
            summary_line = (
                "\n📋 Karar Gerekçesi:\n"
                "Aşağıda belirtilen kriter(ler) karşılanamaması nedeniyle "
                "kredi başvurusu otomatik sistem tarafından reddedilmiştir."
            )

        # Kriter madde işaretleri
        lines: list[str] = [header, "\n🔍 Değerlendirilen Kriterler:"]

        for step in path:
            feature = step.feature
            branch  = step.branch_taken

            # Özel Türkçe açıklama varsa kullan, yoksa genel format
            cond_map = FEATURE_CONDITION_TR.get(feature)
            if cond_map:
                line = f"  • {cond_map[branch]}"
            else:
                label = self._feature_labels.get(feature, feature)
                state = "Sağlandı ✓" if branch else "Sağlanamadı ✗"
                line = f"  • {label}: {state}"

            lines.append(line)

        lines.append(summary_line)

        lines.append(
            "\n⚖️ Yasal Uyarı:\n"
            "Bu karar, açıklanabilir yapay zeka (XAI) tabanlı karar ağacı "
            "sistemi tarafından otomatik olarak üretilmiştir. GDPR Madde 22 "
            "kapsamında itiraz hakkınız saklıdır."
        )

        return "\n".join(lines)

    @staticmethod
    def _build_technical_log(path: list[InferenceStep], decision: str) -> str:
        """
        Adım adım teknik log — audit trail için.

        Format:
            === KARAR AĞACI ÇIKARIM LOGU ===
            Karar: APPROVED
            Path Derinliği: 3
            ─────────────────────────────────
            Adım 1: Node[a1b2c3d4...] | Feature: credit_score_gt_700 | ...
            ...
            ─────────────────────────────────
            SONUÇ YAPRAĞI: APPROVED
        """
        lines: list[str] = [
            "═══════════════════════════════════════",
            "  KARAR AĞACI ÇIKARIM LOGU (XAI)      ",
            "═══════════════════════════════════════",
            f"Karar:         {decision}",
            f"Path Derinliği: {len(path)}",
            "───────────────────────────────────────",
        ]

        for i, step in enumerate(path, start=1):
            branch_dir = "TRUE → SOL DAL" if step.branch_taken else "FALSE → SAĞ DAL"
            lines.append(
                f"Adım {i:>2}: Node[{step.node_id[:8]}...]\n"
                f"         Feature:    {step.feature}\n"
                f"         Threshold:  {step.threshold}\n"
                f"         Operator:   {step.operator}\n"
                f"         InputValue: {step.input_value}\n"
                f"         Branch:     {branch_dir}\n"
                f"         Depth:      {step.depth}"
            )
            lines.append("         ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─")

        lines.append("───────────────────────────────────────")
        lines.append(f"SONUÇ YAPRAĞI: {decision}")
        lines.append("═══════════════════════════════════════")

        return "\n".join(lines)
