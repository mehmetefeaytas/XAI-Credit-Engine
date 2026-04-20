# Adım 4 — Veritabanı Modelleri ve Alembic Migration

**Tarih:** 2026-04-20  
**Durum:** ✅ TAMAMLANDI

---

## Bu Adımda Ne Yapıldı?

Geçici in-memory dictionary kullanılan veri yapılarının tam teşekküllü, asenkron ve kalıcı bir veritabanına dönüştürülmesi için **SQLAlchemy Asenkron (aiosqlite/asyncpg)** ve göç yönetimi için **Alembic** yapılandırıldı.

---

## Oluşturulan Modeller (SQLAlchemy)

### 1. `database.py` (Asenkron ORM Bağlantısı)

FastAPI projesinde kullanılan `async_sessionmaker` ve `create_async_engine` kullanılarak yapıldı. Bu sayede veritabanı G/Ç işlemleri sistemdeki asenkron thread'leri bloke etmeyecek.

### 2. `DatasetModel` (`datasets` tablosu)

Müşteri kredi verisinin şeffaf şekilde, ve karar ağacı öncesi iş kuralı çıktısı `decision` ve `feature_vector` objesi JSON olarak saklandı.

### 3. Tree Modelleri (`tree_versions`, `decision_nodes`, `tree_edges`)

Karar ağacının tüm parçaları ilişkilendirilmiş (foreign keys) şekilde bölündü.

1. Ağacın geçerlilik (is_valid) ve metadata bilgisi
2. Ayrı iç ve yaprak düğümleri
3. True/False ile geçilen dallar (edges)

### 4. Log Modelleri (`inference_logs`, `explanation_logs`)

Otomatik kararlara yönelik her istek `InferenceLogModel`'e, ve GDPR kapsamında üretilen açıklamalar `ExplanationLogModel` tablosuna kaydedilir şekilde hazırlandı.

---

## Migration Süreci

1. `alembic init -t async migrations` çalıştırıldı.
2. `alembic/env.py` yapılandırılarak `app.data.models` ve dinamik `DATABASE_URL` sisteme dahil edildi.
3. `alembic revision --autogenerate -m "Initial Models"` ile ilk göç dosyası (c762618144a6) üretildi.
4. `alembic upgrade head` ile veritabanı başarıyla şemaya uygun `xai_credit.db` olarak oluşturuldu.

---

## Sonraki Adımlar

Şu anda modeller var ancak API endpoint'leri hala in-memory listeleri okuyor.
**Sıradaki yapılacaklar:** API endpoint'leri (`dataset.py`, `tree.py`, `inference.py`, `explanation.py`) güncellenerek Dependency Injection (Depends) yardımıyla `get_db` kullanacak şekilde veritabanına bağlanacak.

Dilersen var olan API'yi in-memory den veritabanına taşıma (refactoring) adımını hemen gerçekleştirebilirim.
