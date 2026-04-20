"""
Demo: Tüm engine katmanını end-to-end çalıştır.

Çıktı: Veri üret → Ağaç inşa et → Doğrula → Çıkarım yap → Açıklama üret
"""
import sys
sys.path.insert(0, ".")

from app.domain.models.customer import Customer, EmploymentStatus
from app.domain.services.dataset_service import DatasetService
from app.engine.tree.tree_builder import TreeBuilder, TreeBuildConfig
from app.engine.tree.tree_validator import TreeValidator
from app.engine.inference.inference_engine import InferenceEngine
from app.engine.xai.explanation_generator import ExplanationGenerator

print("=" * 60)
print("  XAI Credit Engine — Engine Demo")
print("=" * 60)

# 1. Sentetik veri üret
print("\n[1] Sentetik veri üretiliyor (500 kayıt)...")
service = DatasetService(seed=42)
records = service.generate(count=500, approval_ratio=0.55)
balance = DatasetService.class_balance(records)
print(f"    Toplam: {balance['total']} | "
      f"APPROVED: {balance['approved']} ({balance['approval_rate']:.1%}) | "
      f"REJECTED: {balance['rejected']} ({balance['rejection_rate']:.1%})")

# 2. Dataset hazırla ve ağaç inşa et
dataset = service.to_tree_dataset(records)
features = DatasetService.feature_names()

print("\n[2] Karar ağacı inşa ediliyor (max_depth=6)...")
config = TreeBuildConfig(max_depth=6, min_samples_split=5, min_samples_leaf=2)
builder = TreeBuilder(config=config)
root = builder.build(dataset, features, label_col="decision")
stats = builder.get_stats()
edges = builder.get_edges()
all_nodes = builder.collect_all_nodes(root)

print(f"    Kök özelliği: '{root.feature_name}' (en yüksek IG)")
print(f"    Toplam düğüm: {stats['total_nodes']} "
      f"(İç: {stats['inner_nodes']}, Yaprak: {stats['leaf_nodes']})")
print(f"    Kenar sayısı: {stats['total_edges']}")
print(f"    Kök entropisi: {root.entropy:.4f}")

# 3. Ağacı doğrula
print("\n[3] Graf teorisi doğrulaması yapılıyor...")
validator = TreeValidator()
result = validator.validate(all_nodes, edges)
status = "GEÇERLİ ✓" if result.is_valid else "GEÇERSİZ ✗"
print(f"    Sonuç: {status}")
if result.errors:
    for e in result.errors:
        print(f"    HATA: {e}")
if result.warnings:
    for w in result.warnings:
        print(f"    UYARI: {w}")

# 4. Çıkarım yap
print("\n[4] Müşteri değerlendirmesi yapılıyor...")
customer = Customer(
    full_name="Mehmet Yılmaz",
    age=34,
    income=72_000,
    credit_score=742,
    has_prior_default=False,
    employment_status=EmploymentStatus.EMPLOYED,
    debt_to_income=0.28,
    existing_credits=1,
    loan_amount=50_000,
)
customer.validate()
feature_vector = customer.to_feature_vector()
print(f"    Müşteri: {customer.full_name} (Yaş: {customer.age}, Gelir: {customer.income:,.0f} TL)")
print(f"    Feature vektörü: {feature_vector}")

engine = InferenceEngine(root_node=root)
inference = engine.predict(feature_vector)
print(f"\n    ★ KARAR: {inference.decision} "
      f"(Güven: {inference.confidence:.1%}, Derinlik: {inference.depth_reached})")

# 5. XAI Açıklama üret
print("\n[5] XAI açıklaması üretiliyor...")
generator = ExplanationGenerator()
explanation = generator.generate(
    path=inference.path,
    decision=inference.decision,
    language="tr"
)
print("\n  — Boolean Formülü —")
print(f"  {explanation.boolean_formula}")
print("\n  — Doğal Dil Raporu —")
print(explanation.natural_language)

print("\n" + "=" * 60)
print("  🎉 Tüm katmanlar başarıyla çalıştı!")
print("=" * 60)
