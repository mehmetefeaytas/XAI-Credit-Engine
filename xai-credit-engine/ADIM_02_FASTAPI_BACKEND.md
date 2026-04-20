# Adım 2 — FastAPI Backend ve REST API Katmanı

**Tarih:** 2026-04-20  
**Durum:** ✅ TAMAMLANDI (5/5 API endpoint tam çalışıyor)

---

## Bu Adımda Ne Yapıldı?

Teknik planın **ÇIKTI 2** (API Katmanı görev listesi) bölümüne uygun olarak tüm REST API katmanı yazıldı. Adım 1'deki engine katmanının üstüne FastAPI çerçevesi eklendi.

---

## Oluşturulan Dosyalar

### ⚙️ Uygulama Giriş Noktası

| Dosya               | Sorumluluk                                   | Neden?                                                               |
| ------------------- | -------------------------------------------- | -------------------------------------------------------------------- |
| `app/config.py`     | `pydantic-settings` ile `.env` okuma         | Tüm ayarlar ortam değişkeninden override edilebilir; test izolasyonu |
| `app/main.py`       | FastAPI app, CORS, middleware, lifespan hook | Sunucu başlatma, global hata yönetimi, istek zamanlaması             |
| `app/api/router.py` | Tüm v1 router'larını birleştirir             | Tek tutulacak yer (`import app.api.router`)                          |

### 📡 API Endpoint'leri (v1)

| Dosya                   | Endpoint'ler                                                                      | Teknik Planın Karşılığı  |
| ----------------------- | --------------------------------------------------------------------------------- | ------------------------ | ----------------- |
| `api/v1/dataset.py`     | `GET /dataset`, `POST /dataset/generate`, `DELETE /dataset`, `GET /dataset/stats` | ÇIKTI 2 → dataset.py     |
| `api/v1/tree.py`        | `POST /tree/build`, `GET /tree`, `GET /tree/active`, `GET /tree/{version_id}`     | ÇIKTI 2 → tree.py        |
| `api/v1/inference.py`   | `POST /inference`                                                                 | ÇIKTI 2 → inference.py   |
| `api/v1/explanation.py` | `GET /explanation/{inference_id}`                                                 | ÇIKTI 2 → explanation.py |
| `api/v1/logs.py`        | `GET /logs?type=inference                                                         | explanation&page=`       | ÇIKTI 2 → logs.py |

### 📋 Pydantic Şemaları

| Dosya                           | İçerik                                                                                 |
| ------------------------------- | -------------------------------------------------------------------------------------- |
| `schemas/dataset_schema.py`     | DatasetGenerateRequest, DatasetRecordResponse, DatasetSummaryResponse                  |
| `schemas/tree_schema.py`        | TreeBuildRequest, TreeBuildResponse, NodeResponse, EdgeResponse, FeatureImportanceItem |
| `schemas/inference_schema.py`   | InferenceRequest, InferenceResponse, PathStep                                          |
| `schemas/explanation_schema.py` | ExplanationResponse                                                                    |

---

## Neden Bu Şekilde Tasarlandı?

### In-Memory Store (Geçici)

Adım 4'te (Veritabanı) SQLAlchemy ile değiştirilecek. Şu an:

- `_dataset_store: list[DatasetRecord]` → dataset kayıtları
- `_tree_store: dict[str, dict]` → versiyonlu ağaçlar
- `_inference_log: list[dict]` → çıkarım geçmişi
- `_explanation_log: dict` → açıklama cache

**Gerekçe:** DB kurulumu olmadan sistemi test etmek. Arayüz sabit kalacak, yalnızca depolama mekanizması değişecek.

### Dependency Injection Hazırlığı

`get_dataset_store()`, `get_active_tree()`, `get_inference_log()` fonksiyonları FastAPI `Depends()` ile değiştirilebilecek şekilde yazıldı.

### 409 Conflict Stratejisi

Ağaç yokken `/inference` çağrılırsa `409 Conflict` döner (400 değil). Çünkü istek formatı doğru, ancak sistem **durumu** uygun değil.

---

## Canlı Test Çıktısı

```
[1] Dataset üretiliyor...
    Total=200, APPROVED=110, REJECTED=90

[2] Agac insa ediliyor...
    Versiyon: 0bd92169-0a5...
    Dugumler: 14 (ic: 6, yaprak: 8)
    Gecerli: True
    Feature onemi:
      1. credit_score_gt_700: 0.6244
      2. existing_credits_lt_3: 0.4793
      3. debt_to_income_lt_35: 0.4222

[3] Cikarim yapiliyor...
    KARAR: APPROVED (guven: 100.0%, derinlik: 4)
    Path adimlari: 4

[4] XAI aciklama aliniyor...
    Boolean: (credit_score_gt_700 = T) ∧ (existing_credits_lt_3 = T) ∧ ...
    NL rapor: ✅ Kredi başvurusu ONAYLANDI. 🔍 Değerlendirilen Kriterler: ...

[5] Loglar listeleniyor...
    Toplam log: 2
    - [explanation] karar: APPROVED
    - [inference] karar: APPROVED

Tum API endpoint testleri basarili!
```

---

## Swagger UI Doğrulaması

`http://127.0.0.1:8000/docs` adresinde Swagger UI çalışıyor:

- **Tree**: POST /build, GET /tree, GET /active, GET /{version_id}
- **Inference**: POST /inference
- **Explanation**: GET /{inference_id}
- **Logs**: GET /logs
- **Dataset**: GET, POST /generate, DELETE, GET /stats
- **System**: GET /health, GET /

**Tüm Pydantic şemaları** (14 adet) Swagger'da görünür ve interaktif test edilebilir.

---

## Kurulum ve Çalıştırma

```bash
cd backend
python3 -m pip install fastapi uvicorn pydantic-settings
python3 -m uvicorn app.main:app --reload --port 8000

# API test
python3 test_api_e2e.py
```

---

## Sonraki Adımlar

| Öncelik | Adım   | İçerik                                              |
| ------- | ------ | --------------------------------------------------- |
| ⭐      | Adım 3 | Frontend (React + Vite + TypeScript + React-Flow)   |
| ⭐      | Adım 4 | Veritabanı katmanı (SQLAlchemy + Alembic migration) |
|         | Adım 5 | Integration testleri (pytest + httpx)               |

---

## Teknik Notlar

- **In-memory state** → thread-safe değil; production için DB + async gerekir
- **CORS** → frontend origin'leri `.env` ile yönetilir
- **Lifespan hook** → DB bağlantısı Adım 4'te buraya eklenir
- **Error handler** → `ValueError` → 422, genel hata → 500, iş kuralı → 409
- **`@lru_cache`** → `get_settings()` singleton; test'de `cache_clear()` ile override
