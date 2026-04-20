# Adım 3 — React Frontend (XAI Görselleştirme Arayüzü)

**Tarih:** 2026-04-20  
**Durum:** ✅ TAMAMLANDI

---

## Bu Adımda Ne Yapıldı?

Projenin kullanıcı arayüzü (Frontend) React, TypeScript ve Vite kullanılarak sıfırdan oluşturuldu. Tasarımda modern, cam efektli (glassmorphism) ve koyu tema ağırlıklı bir görsel dil (Vanilla CSS) tercih edildi. TailwindCSS gereksinimleri dahilinde saf dışı bırakılıp, performanslı standart CSS kuralları uygulandı.

---

## Kurulan Teknolojiler ve Bağımlılıklar

- **Framework:** React 18 + Vite + TypeScript
- **Stil:** Pure Vanilla CSS (CSS3 Değişkenleri, Glassmorphism, CSS Grid/Flexbox)
- **Ağaç Çizimi:** `@xyflow/react` (React-Flow) kütüphanesi
- **İkonlar:** `lucide-react` (SVG tabanlı modern ikon paketi)

---

## Geliştirilen Bileşenler (`src/components/`)

### 1. `Dashboard.tsx` (Sistem / Veri)

Sistem yönetiminin yapıldığı denetim masası:

- Backend API (`/health`) durum kontrolü
- Mevcut dataset istatistiklerinin (Onay/Red dağılımı vb.) görüntülenmesi
- Yeni sentetik müşteri başvuru verisi üretme butonu (API: `/dataset/generate`)
- Karar ağacı motorunu başlatma butonu (API: `/tree/build`)

### 2. `TreeVisualizer.tsx` (Karar Ağacı)

Eğitilmiş karar ağacının node ve edge bazlı görsel dökümü:

- React-Flow ile düğümler arası bağlantıların dinamik ve taşınabilir çizimi
- Karar (Decision) düğümleri ve Yaprak (Leaf) düğümlerin ayrıştırılması
- (Not: Backend API v1, düğümleri döküm olarak döndürmediğinden bu ekranda uygun uyarılar ele alınmıştır).

### 3. `InferenceForm.tsx` (Kredi Başvurusu)

Son müşteri deneyimi:

- Kredi başvurusu için gerekli 8 farklı özelliğin girildiği form
- İstek gönderildiğinde **Karar Ağacı Motoru** üzerinden saniyeler içinde karar verme (`/inference`)
- **GDPR Madde 22'ye uygun** XAI (Açıklanabilir Yapay Zeka) raporu ve Boolean karar kökeninin ekranda anlık (real-time) belirmesi.

---

## Tasarım Özellikleri (`index.css`)

- **Vibrant & Dark Aesthetics:** Gece modu tabanlı koyu renk paleti, `#4F46E5` (Primary) ile modern bir his oluşturuldu.
- **Glassmorphism:** Kartlar (Cards), input'lar ve butonlarda `backdrop-filter: blur(12px)` ile yarı transparan cam hissiyatı sağlandı.
- **Micro-Animations:** Hover durumları (`transform: translateY(-2px)`), geçiş yumuşatmaları (transitions) ve yükleniyor animasyonları tıkır tıkır çalışacak şekilde eklendi.

---

## Nasıl Çalıştırılır?

Tüm sistemi tek tıklamayla çalıştırmak için ana dizindeki PowerShell betiği kullanılabilir:

```powershell
.\start_all.ps1
```

_(Veya manuel olarak:)_

1. `backend/` klasöründe `python3 -m uvicorn app.main:app`
2. `frontend/` klasöründe `npm run dev`

---

## Sonraki Adımlar

| Öncelik | Adım   | İçerik                                                                                |
| ------- | ------ | ------------------------------------------------------------------------------------- |
| ⭐      | Adım 4 | Veritabanı Modelleri ve Alembic Migration (In-Memory yerine kalıcı SQLite / Postgres) |
|         | Adım 5 | Entegrasyon testleri                                                                  |
