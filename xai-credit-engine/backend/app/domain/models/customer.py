"""
domain/models/customer.py
──────────────────────────────────────────────────────────────────────────────
Müşteri alan modeli ve özellik vektörü dönüşümü.

Bu model:
  - Müşteri verilerini doğrular (yaş ≥ 18, gelir ≥ 0)
  - Sürekli/kategorik değerleri Boolean özellik vektörüne dönüştürür
  - Karar ağacına girdi hazırlar

Örnek dönüşüm:
    Customer(age=34, income=72000, credit_score=742, ...) →
    {
        "income_gt_50k":         True,
        "credit_score_gt_700":   True,
        "has_prior_default":     False,
        "debt_to_income_lt_35":  True,
        "employment_employed":   True,
        "age_gte_25":            True,
        "existing_credits_lt_3": True,
    }
"""

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class EmploymentStatus(str, Enum):
    EMPLOYED      = "EMPLOYED"
    SELF_EMPLOYED = "SELF_EMPLOYED"
    UNEMPLOYED    = "UNEMPLOYED"


# Varsayılan eşik değerleri (sabit, v2'de DB'den dinamik yüklenecek)
DEFAULT_THRESHOLDS: dict[str, float] = {
    "income_threshold":       50_000.0,   # TL/yıl
    "credit_score_threshold":    700.0,
    "debt_to_income_threshold":    0.35,  # %35
    "age_threshold":              25.0,   # yıl
    "existing_credits_threshold":  3.0,  # adet
    "loan_amount_threshold":  100_000.0,  # TL
}


@dataclass
class Customer:
    """
    Müşteri alan modeli.

    Attributes:
        id:               Benzersiz UUID (otomatik üretilir)
        full_name:        Tam ad
        age:              Yaş (18-100 arası)
        income:           Yıllık gelir (TL, ≥ 0)
        credit_score:     Kredi puanı (300-850)
        has_prior_default:Geçmişte icra/temerrüt kaydı var mı?
        employment_status:Çalışma durumu
        debt_to_income:   Borç/gelir oranı (0.0 - 1.0)
        existing_credits: Mevcut aktif kredi sayısı
        loan_amount:      Talep edilen kredi tutarı (TL)
    """
    id:                UUID              = field(default_factory=uuid4)
    full_name:         str               = ""
    age:               int               = 0
    income:            float             = 0.0
    credit_score:      int               = 500
    has_prior_default: bool              = False
    employment_status: EmploymentStatus  = EmploymentStatus.EMPLOYED
    debt_to_income:    float             = 0.0
    existing_credits:  int               = 0
    loan_amount:       float             = 0.0

    def validate(self) -> None:
        """
        İş kuralı doğrulaması. Geçersiz veri için ValueError fırlatır.

        Kurallar:
            - Yaş 18-100 arasında olmalı
            - Gelir negatif olamaz
            - Kredi puanı 300-850 arasında olmalı
            - Borç/gelir oranı 0-1 arasında olmalı
            - Kredi tutarı > 0 olmalı
        """
        errors: list[str] = []

        if not (18 <= self.age <= 100):
            errors.append(f"Yaş geçersiz: {self.age}. 18-100 arası olmalı.")

        if self.income < 0:
            errors.append(f"Gelir negatif olamaz: {self.income}")

        if not (300 <= self.credit_score <= 850):
            errors.append(f"Kredi puanı geçersiz: {self.credit_score}. 300-850 arası olmalı.")

        if not (0.0 <= self.debt_to_income <= 1.0):
            errors.append(f"Borç/gelir oranı geçersiz: {self.debt_to_income}. 0.0-1.0 arası olmalı.")

        if self.loan_amount <= 0:
            errors.append(f"Kredi tutarı pozitif olmalı: {self.loan_amount}")

        if self.existing_credits < 0:
            errors.append(f"Mevcut kredi sayısı negatif olamaz: {self.existing_credits}")

        if errors:
            raise ValueError("Müşteri doğrulama hatası:\n" + "\n".join(errors))

    def to_feature_vector(
        self,
        thresholds: dict[str, float] | None = None
    ) -> dict[str, bool]:
        """
        Müşteri niteliklerini Boolean özellik vektörüne dönüştürür.

        Karar ağacının girdi formatı budur. Her özellik bir eşik
        karşılaştırmasının sonucudur (True/False).

        Args:
            thresholds: Eşik değerleri dict'i. None ise DEFAULT_THRESHOLDS kullanılır.

        Returns:
            7 Boolean özellikten oluşan dict

        Örnek çıktı:
            {
                "income_gt_50k":         True,   # gelir > 50000
                "credit_score_gt_700":   True,   # kredi puanı ≥ 700
                "has_prior_default":     False,  # geçmiş icra kaydı yok
                "debt_to_income_lt_35":  True,   # borç oranı < 0.35
                "employment_employed":   True,   # çalışıyor
                "age_gte_25":            True,   # yaş ≥ 25
                "existing_credits_lt_3": True,   # 3'ten az aktif kredi
            }
        """
        t = thresholds or DEFAULT_THRESHOLDS

        return {
            # Gelir eşiği
            "income_gt_50k":
                self.income > t.get("income_threshold", 50_000.0),

            # Kredi puanı eşiği
            "credit_score_gt_700":
                self.credit_score >= t.get("credit_score_threshold", 700.0),

            # İcra/temerrüt kaydı (True = kötü, False = temiz)
            "has_prior_default":
                self.has_prior_default,

            # Borç/gelir oranı eşiği (düşük = iyi)
            "debt_to_income_lt_35":
                self.debt_to_income < t.get("debt_to_income_threshold", 0.35),

            # Çalışma durumu (sadece "maaşlı çalışan" True)
            "employment_employed":
                self.employment_status == EmploymentStatus.EMPLOYED,

            # Yaş eşiği
            "age_gte_25":
                self.age >= t.get("age_threshold", 25.0),

            # Mevcut kredi sayısı eşiği (az = iyi)
            "existing_credits_lt_3":
                self.existing_credits < t.get("existing_credits_threshold", 3.0),
        }

    def __repr__(self) -> str:
        return (
            f"Customer(id={str(self.id)[:8]}..., name='{self.full_name}', "
            f"age={self.age}, income={self.income:,.0f}, "
            f"credit_score={self.credit_score}, "
            f"employment={self.employment_status.value})"
        )
