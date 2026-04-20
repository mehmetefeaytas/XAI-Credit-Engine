"""
domain/services/dataset_service.py
──────────────────────────────────────────────────────────────────────────────
Sentetik Kredi Başvurusu Veri Seti Üreticisi

Bu servis:
  1. Gerçekçi müşteri verileri üretir (Faker benzeri kurallar)
  2. İş kurallarına göre APPROVED/REJECTED kararını atar
  3. Sınıf dengesini %40-60 arasında tutar
  4. Feature vektörünü Boolean'a dönüştürür (karar ağacı girdi formatı)

Teknik önem:
  - scikit-learn veya harici ML kütüphanesi yok
  - Kural tabanlı karar (deterministik, şeffaf)
  - Sınıf dengesi: az örnekli sınıf %40'ın altına inmez
"""

import random
import math
from dataclasses import dataclass

from app.domain.models.customer import Customer, EmploymentStatus, DEFAULT_THRESHOLDS


@dataclass
class DatasetRecord:
    """
    Tek bir dataset kaydı.

    customer:        Müşteri bilgileri
    feature_vector:  Boolean özellik vektörü (karar ağacı girdisi)
    decision:        True=APPROVED, False=REJECTED (doğru etiket)
    """
    customer:       Customer
    feature_vector: dict[str, bool]
    decision:       bool


class DatasetService:
    """
    Sentetik kredi başvurusu veri seti üreticisi.

    Kullanım:
        service = DatasetService(seed=42)
        records = service.generate(count=500, approval_ratio=0.55)

        # Dataset formatına dönüştür (ağaç için)
        dataset = service.to_tree_dataset(records)
    """

    # Bölge/isim havuzu (Faker yerine basit liste)
    _FIRST_NAMES = [
        "Ahmet", "Mehmet", "Ali", "Ayşe", "Fatma", "Zeynep", "Mustafa",
        "Hasan", "Hüseyin", "Elif", "Emine", "Hatice", "Ömer", "İbrahim",
        "Yusuf", "Musa", "İsa", "Davut", "Süleyman", "Yunus", "Büşra", "Selin"
    ]
    _LAST_NAMES = [
        "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Doğan", "Kılıç",
        "Arslan", "Taş", "Aydın", "Özdemir", "Arslan", "Yıldırım",
        "Erdoğan", "Kurt", "Özkan", "Çetin", "Akar", "Güneş", "Aslan"
    ]

    def __init__(self, seed: int | None = 42):
        """
        Args:
            seed: Rastgele tohumlama değeri. None ise her seferinde farklı.
        """
        self._rng = random.Random(seed)

    def generate(
        self,
        count: int = 500,
        approval_ratio: float = 0.55,
        thresholds: dict | None = None
    ) -> list[DatasetRecord]:
        """
        Belirtilen sayıda sentetik kayıt üretir.

        Sınıf dengesi stratejisi:
            Hedef: approval_ratio ± 0.05 (yani %50-60 arası)
            Yöntem: Önce "elverişli" müşteri üretilir, sonra küçük
                    gürültü eklenerek gerçekçilik sağlanır.

        Args:
            count:          Üretilecek kayıt sayısı
            approval_ratio: APPROVED oranı (0.4-0.6 arası önerilir)
            thresholds:     Özellik eşik değerleri

        Returns:
            DatasetRecord listesi

        Raises:
            ValueError: count ≤ 0 veya approval_ratio geçersizse
        """
        if count <= 0:
            raise ValueError(f"count pozitif olmalı: {count}")
        if not (0.1 <= approval_ratio <= 0.9):
            raise ValueError(f"approval_ratio 0.1-0.9 arası olmalı: {approval_ratio}")

        t = thresholds or DEFAULT_THRESHOLDS
        records: list[DatasetRecord] = []

        approved_target = int(count * approval_ratio)
        rejected_target = count - approved_target

        # APPROVED kayıtları üret
        for _ in range(approved_target):
            customer = self._generate_approved_profile(t)
            fv = customer.to_feature_vector(t)
            records.append(DatasetRecord(
                customer=customer,
                feature_vector=fv,
                decision=True,
            ))

        # REJECTED kayıtları üret
        for _ in range(rejected_target):
            customer = self._generate_rejected_profile(t)
            fv = customer.to_feature_vector(t)
            records.append(DatasetRecord(
                customer=customer,
                feature_vector=fv,
                decision=False,
            ))

        # Karıştır (shuffle) — sıra önyargısını gider
        self._rng.shuffle(records)
        return records

    def _generate_approved_profile(self, t: dict) -> Customer:
        """
        Kredi onaylanacak bir müşteri profili üretir.

        Kural: Onay için en az şu kriterler sağlanmalı:
            - Income > threshold
            - credit_score ≥ threshold
            - NO prior default
            - debt_to_income < threshold
        Küçük gürültü: bazı faktörlerde %20 ihtimalle "zayıf" değer.
        """
        noise = self._rng.random() < 0.15  # %15 ihtimalle sınır vaka

        income = self._rng.uniform(
            t.get("income_threshold", 50000) * (0.8 if noise else 1.1),
            t.get("income_threshold", 50000) * 3.0
        )
        credit_score = self._rng.randint(
            int(t.get("credit_score_threshold", 700)) - (20 if noise else 0),
            850
        )
        debt_to_income = self._rng.uniform(
            0.05,
            t.get("debt_to_income_threshold", 0.35) * (1.05 if noise else 0.9)
        )
        age = self._rng.randint(
            25 if not noise else 22,
            65
        )
        existing_credits = self._rng.randint(0, 2)
        employment = (
            EmploymentStatus.EMPLOYED
            if self._rng.random() > 0.1
            else EmploymentStatus.SELF_EMPLOYED
        )
        loan_amount = self._rng.uniform(10_000, 500_000)

        return Customer(
            full_name=self._random_name(),
            age=max(18, age),
            income=round(income, 2),
            credit_score=max(300, min(850, credit_score)),
            has_prior_default=False,
            employment_status=employment,
            debt_to_income=round(min(0.99, max(0.01, debt_to_income)), 4),
            existing_credits=existing_credits,
            loan_amount=round(loan_amount, 2),
        )

    def _generate_rejected_profile(self, t: dict) -> Customer:
        """
        Kredi reddedilecek bir müşteri profili üretir.

        Kural: En az 1-2 kötü faktör zorunlu:
            - Düşük gelir VEYA
            - Düşük kredi puanı VEYA
            - Geçmiş icra kaydı VEYA
            - Yüksek borç oranı
        """
        # Reddedilme sebebi rastgele seç
        rejection_reason = self._rng.choice([
            "low_income", "low_score", "prior_default",
            "high_dti", "multiple_issues"
        ])

        income = self._rng.uniform(10_000, 120_000)
        credit_score = self._rng.randint(300, 850)
        debt_to_income = self._rng.uniform(0.05, 0.95)
        has_prior_default = False
        age = self._rng.randint(18, 65)
        employment = self._rng.choice(list(EmploymentStatus))
        existing_credits = self._rng.randint(0, 8)
        loan_amount = self._rng.uniform(5_000, 1_000_000)

        if rejection_reason == "low_income":
            income = self._rng.uniform(5_000, t.get("income_threshold", 50000) * 0.85)
        elif rejection_reason == "low_score":
            credit_score = self._rng.randint(300, int(t.get("credit_score_threshold", 700)) - 10)
        elif rejection_reason == "prior_default":
            has_prior_default = True
        elif rejection_reason == "high_dti":
            debt_to_income = self._rng.uniform(t.get("debt_to_income_threshold", 0.35) * 1.1, 0.95)
        elif rejection_reason == "multiple_issues":
            income = self._rng.uniform(5_000, 30_000)
            credit_score = self._rng.randint(300, 620)
            has_prior_default = self._rng.choice([True, False])

        return Customer(
            full_name=self._random_name(),
            age=max(18, age),
            income=round(max(1, income), 2),
            credit_score=max(300, min(850, credit_score)),
            has_prior_default=has_prior_default,
            employment_status=employment,
            debt_to_income=round(min(0.99, max(0.01, debt_to_income)), 4),
            existing_credits=max(0, existing_credits),
            loan_amount=round(max(1, loan_amount), 2),
        )

    def _random_name(self) -> str:
        fname = self._rng.choice(self._FIRST_NAMES)
        lname = self._rng.choice(self._LAST_NAMES)
        return f"{fname} {lname}"

    def to_tree_dataset(self, records: list[DatasetRecord]) -> list[dict]:
        """
        DatasetRecord listesini karar ağacı için gereken
        dict formatına dönüştürür.

        Her dict: feature_vector + {"decision": bool}

        Örnek:
            {
                "income_gt_50k":         True,
                "credit_score_gt_700":   True,
                "has_prior_default":     False,
                "debt_to_income_lt_35":  True,
                "employment_employed":   True,
                "age_gte_25":            True,
                "existing_credits_lt_3": True,
                "decision":              True,
            }
        """
        dataset: list[dict] = []
        for rec in records:
            row = dict(rec.feature_vector)
            row["decision"] = rec.decision
            dataset.append(row)
        return dataset

    @staticmethod
    def class_balance(records: list[DatasetRecord]) -> dict:
        """Sınıf dengesi istatistikleri."""
        total    = len(records)
        approved = sum(1 for r in records if r.decision)
        rejected = total - approved
        return {
            "total":           total,
            "approved":        approved,
            "rejected":        rejected,
            "approval_rate":   round(approved / total, 4) if total > 0 else 0.0,
            "rejection_rate":  round(rejected / total, 4) if total > 0 else 0.0,
        }

    @staticmethod
    def feature_names() -> list[str]:
        """Karar ağacı için kullanılan Boolean özellik sütun adları."""
        return [
            "income_gt_50k",
            "credit_score_gt_700",
            "has_prior_default",
            "debt_to_income_lt_35",
            "employment_employed",
            "age_gte_25",
            "existing_credits_lt_3",
        ]
