# XAI Credit Engine — README

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-34%20passed-brightgreen)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

**Açıklanabilir Yapay Zeka Tabanlı Otonom Kredi Onay Sistemi**

---

## 🎯 Proje Hakkında

XAI Credit Engine, bankaların kredi değerlendirme süreçlerinde kullanabileceği,
**tamamen sıfırdan inşa edilmiş** bir karar ağacı motorudur. Hiçbir makine öğrenmesi
kütüphanesi kullanılmadan; Shannon entropisi, bilgi kazancı ve ayrık matematik
temelleriyle geliştirilmiştir.

Her kararın **neden verildiğini** Boolean formülleri ve doğal dil raporlarıyla açıklar.

---

## 📁 Proje Yapısı

```
xai-credit-engine/
├── ADIM_01_ENGINE_KATMANI.md      ← İlerleme belgeleri
├── backend/
│   ├── demo_engine.py             ← Hızlı demo çalıştırma
│   ├── requirements.txt
│   ├── pytest.ini
│   └── app/
│       ├── domain/
│       │   ├── models/            ← Customer, DecisionNode, Edge
│       │   └── services/          ← DatasetService (sentetik veri)
│       └── engine/
│           ├── math/              ← Entropy, InformationGain, TruthTable
│           ├── tree/              ← TreeBuilder (ID3), TreeValidator
│           ├── inference/         ← InferenceEngine, PathRecorder
│           └── xai/               ← ExplanationGenerator (Boolean + NL)
└── docs/                          ← Mimari ve akademik belgeler
```

---

## 🚀 Hızlı Test

```bash
cd backend
python3 -m pip install pytest
python3 -m pytest tests/unit/ -v    # 34 test
python3 demo_engine.py              # end-to-end demo
```

---

## ✅ Tamamlanan Adımlar

| Adım   | İçerik                          | Durum         |
| ------ | ------------------------------- | ------------- |
| Adım 1 | Engine katmanı + birim testleri | ✅ 34/34 test |
| Adım 2 | FastAPI backend                 | 🔜            |
| Adım 3 | REST API endpoints              | 🔜            |
| Adım 4 | Veritabanı + Alembic            | 🔜            |
| Adım 5 | Integration testleri            | 🔜            |
| Adım 6 | React frontend                  | 🔜            |
