"""
tests/integration/test_pipeline_e2e.py
──────────────────────────────────────────────────────────────────────────────
FastAPI + SQLAlchemy asenkron altyapısını test eden TAM pipeline entegrasyonu.
Sırasıyla:
1. Sentetik Veri üretimi
2. Karar Ağacı inşası
3. Müşteri Çıkarım (Inference)
4. XAI Açıklaması (Explanation)
5. Audit Log kontrolü
"""

import pytest

pytestmark = pytest.mark.asyncio

async def test_full_xai_pipeline(client):
    # 1. Dataset Üretimi
    res_data = await client.post("/api/v1/dataset/generate", json={
        "count": 50,
        "approval_ratio": 0.5,
        "seed": 123
    })
    assert res_data.status_code == 201
    data_summary = res_data.json()
    assert data_summary["total"] == 50
    assert data_summary["approved"] > 0
    
    # 1.1 Dataset İstatisleri Okuma
    res_stats = await client.get("/api/v1/dataset/stats")
    assert res_stats.status_code == 200
    assert res_stats.json()["total"] == 50

    # 2. Ağaç Inşası
    res_tree = await client.post("/api/v1/tree/build", json={
        "max_depth": 5,
        "min_samples_split": 2,
        "min_samples_leaf": 1,
        "use_gain_ratio": False
    })
    assert res_tree.status_code == 201
    tree_data = res_tree.json()
    assert tree_data["is_valid"] is True
    assert tree_data["total_nodes"] > 1
    
    version_id = tree_data["version_id"]

    # 2.1 Aktif Ağaç Kontrolü
    res_active = await client.get("/api/v1/tree/active")
    assert res_active.status_code == 200
    assert res_active.json()["version_id"] == version_id

    # 3. Kredi Değerlendirmesi (Inference)
    customer_payload = {
        "full_name": "Ahmet Test",
        "age": 30,
        "income": 120000.0,
        "credit_score": 750,
        "has_prior_default": False,
        "employment_status": "EMPLOYED",
        "debt_to_income": 0.20,
        "existing_credits": 1,
        "loan_amount": 30000.0
    }
    res_inf = await client.post("/api/v1/inference", json=customer_payload)
    assert res_inf.status_code == 200
    inf_data = res_inf.json()
    assert inf_data["decision"] in ["APPROVED", "REJECTED"]
    assert 0.0 <= inf_data["confidence"] <= 1.0
    assert len(inf_data["path"]) > 0
    inference_id = inf_data["inference_id"]

    # 4. XAI Açıklaması Alınması
    res_exp = await client.get(f"/api/v1/explanation/{inference_id}?language=tr")
    assert res_exp.status_code == 200
    exp_data = res_exp.json()
    assert exp_data["decision"] == inf_data["decision"]
    assert len(exp_data["boolean_formula"]) > 5
    assert "✅" in exp_data["natural_language"] or "❌" in exp_data["natural_language"]

    # 5. Logların Kontrolü
    res_logs = await client.get("/api/v1/logs?size=10")
    assert res_logs.status_code == 200
    logs_resp = res_logs.json()
    
    # Beklenen 2 log var (1 Inference, 1 Explanation)
    assert logs_resp["total"] >= 2
    types = [item["type"] for item in logs_resp["items"]]
    assert "inference" in types
    assert "explanation" in types
