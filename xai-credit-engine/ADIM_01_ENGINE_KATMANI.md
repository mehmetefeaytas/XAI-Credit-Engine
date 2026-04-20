# Adım 1 — Engine Katmanı ve Temel Altyapı

**Tarih:** 2026-04-20  
**Durum:** ✅ TAMAMLANDI (34/34 test geçti)

---

## Bu Adımda Ne Yapıldı?

Teknik planın **ÇIKTI 2** (Backend Dosya Listesi) ve **ÇIKTI 5** (Python Sınıf İskeletleri) bölümleri referans alınarak projenin temel engine katmanı sıfırdan yazıldı.

---

## Oluşturulan Dosyalar

### 📁 Monorepo Klasör Yapısı

Teknik plandaki **ÇIKTI 1** klasör ağacına uygun olarak tüm dizinler yaratıldı.

### 🔢 Engine / Math Katmanı

| Dosya                                | Sorumluluk                                 | Neden?                                                       |
| ------------------------------------ | ------------------------------------------ | ------------------------------------------------------------ |
| `engine/math/entropy_calculator.py`  | Shannon Entropy H(S) ve H(S\|A)            | Karar ağacının bölme kriteri. Saf düğüm → H=0, dengeli → H=1 |
| `engine/math/information_gain.py`    | IG, SplitInfo, GainRatio, feature sıralama | En bilgilendirici özelliği seçmek için                       |
| `engine/math/truth_table_builder.py` | 2^N kombinatoryal doğruluk tablosu         | XAI Boolean formülü doğrulaması ve DNF üretimi için          |

**Matematiksel temel:**

```
H(S) = -Σ p_i * log₂(p_i)
IG(S, A) = H(S) - H(S|A)
GainRatio = IG / SplitInfo   (C4.5 yöntemi)
```

### 🌳 Engine / Tree Katmanı

| Dosya                           | Sorumluluk                      | Neden?                                       |
| ------------------------------- | ------------------------------- | -------------------------------------------- |
| `engine/tree/tree_builder.py`   | ID3 recursive ağaç inşacısı     | scikit-learn yok, sıfırdan implementasyon    |
| `engine/tree/tree_validator.py` | 7 graf teorisi kuralı doğrulama | Cycle, in-degree, bağlantılılık, determinizm |

**7 Durdurma Kriteri (Stopping Criteria):**

1. Boş veri → parent majority sınıfı
2. Saf küme (H=0) → saf yaprak
3. Özellik listesi bitti → majority vote
4. max_depth aşıldı → yaprak
5. min_samples_split → yaprak
6. Best IG = 0 → yaprak
7. min_samples_leaf → o dalı yaprak yap

**7 Doğrulama Kuralı (TreeValidator):**

1. Tek kök (in-degree=0 olan 1 düğüm)
2. Kök hariç in-degree=1
3. Döngü yok (DFS cycle detection)
4. Tüm düğümler erişilebilir (BFS bağlantılılık)
5. Her iç düğüm tam 2 çocuk (binary tree)
6. Yaprak etiketleri geçerli (APPROVED/REJECTED)
7. UNIQUE(source, branch_value) — determinizm garantisi

### ⚙️ Engine / Inference Katmanı

| Dosya                                  | Sorumluluk                                | Neden?                           |
| -------------------------------------- | ----------------------------------------- | -------------------------------- |
| `engine/inference/inference_engine.py` | Kökten yaprağa traversal + path recording | O(d) karmaşıklıkla karar üretimi |

**Özellikler:**

- Eksik feature için imputation stratejisi
- Confidence skoru: majority_count / total
- Batch predict desteği

### 🧠 Engine / XAI Katmanı

| Dosya                                 | Sorumluluk                                           | Neden?                                       |
| ------------------------------------- | ---------------------------------------------------- | -------------------------------------------- |
| `engine/xai/explanation_generator.py` | Boolean formülü + DNF + Türkçe NL rapor + teknik log | GDPR Madde 22 uyumu için açıklanabilir karar |

**Üretilen açıklama formatları:**

1. **Boolean AND zinciri:** `(credit_score_gt_700 = T) ∧ (income_gt_50k = T) ∧ ¬(has_prior_default = T)`
2. **DNF mintermi:** `[APPROVED] credit_score_gt_700=T ∧ income_gt_50k=T`
3. **Türkçe NL raporu:** "✅ Kredi başvurusu ONAYLANDI. Kredi puanı 700 veya üzerinde ✓..."
4. **Teknik audit log:** Adım adım node/feature/branch detayları

### 📊 Domain Katmanı

| Dosya                                | Sorumluluk                               | Neden?                                         |
| ------------------------------------ | ---------------------------------------- | ---------------------------------------------- |
| `domain/models/customer.py`          | Müşteri modeli + Boolean vektöre dönüşüm | Sürekli değerleri ağaç girdisine çevirir       |
| `domain/models/decision_node.py`     | DecisionTreeNode + DecisionTreeEdge      | Graf teorisi ağırlıklı model                   |
| `domain/services/dataset_service.py` | Sentetik veri üreticisi                  | Sınıf dengesi %40-60, kural tabanlı etiketleme |

---

## Test Sonuçları

```
python3 -m pytest tests/unit/ -v
======================== 34 passed in 0.17s ========================
```

| Test Dosyası           | Test Sayısı | Durum         |
| ---------------------- | ----------- | ------------- |
| `test_entropy.py`      | 13 test     | ✅ Tümü geçti |
| `test_tree_builder.py` | 17 test     | ✅ Tümü geçti |

**Kritik test senaryoları:**

- `H(pure)=0`, `H(balanced)=1`, bilinen değer `H([T,T,T,F,F])≈0.971`
- Koşullu entropi: bilgi veren özellik → H(S|A) < H(S)
- Saf dataset → kök yaprak (tek düğüm)
- `max_depth=1` → yalnızca 1 seviye bölme
- Binary tree yapısı: her iç düğüm tam 2 çocuk
- Yaprak etiketleri {APPROVED, REJECTED} dışı yok

---

## Sonraki Adımlar

| Öncelik | Adım   | İçerik                                                      |
| ------- | ------ | ----------------------------------------------------------- |
| ⭐      | Adım 2 | FastAPI backend (main.py, config.py, router.py)             |
| ⭐      | Adım 3 | API Endpoints (dataset, tree, inference, explanation, logs) |
| ⭐      | Adım 4 | Veritabanı modelleri + Alembic migration                    |
|         | Adım 5 | Integration testleri (seed → build → infer → explain)       |
|         | Adım 6 | Frontend (React + Vite + TypeScript)                        |

---

## Teknik Notlar

- **scikit-learn kullanılmadı** — ID3 sıfırdan implementasyon
- **Eşitlik durumu (tie-break):** Alfabetik küçük özellik seçilir (deterministik)
- **Boş yaprak karar:** Finansal ihtiyat ilkesiyle REJECTED (pos==neg)
- **Entropy hesabı:** floating point hassasiyeti için `abs(h) < 1e-9` kullanıldı
- **Python 3.14.3** üzerinde test edildi ✓
