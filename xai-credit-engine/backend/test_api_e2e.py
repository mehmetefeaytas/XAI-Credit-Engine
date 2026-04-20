"""API end-to-end entegrasyon testi (CLI scripti)."""
import sys
import urllib.request
import json

BASE = "http://127.0.0.1:8000/api/v1"

def api(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

errors = []

# 1: Dataset
print("[1] Dataset üretiliyor...")
r = api("POST", "/dataset/generate", {"count": 200, "approval_ratio": 0.55, "seed": 42})
print(f"    Total={r['total']}, APPROVED={r['approved']}, REJECTED={r['rejected']}")

# 2: Tree build
print("[2] Agac insa ediliyor...")
r = api("POST", "/tree/build", {"max_depth": 6, "min_samples_split": 5})
version_id = r["version_id"]
print(f"    Versiyon: {version_id[:12]}...")
print(f"    Dugumler: {r['total_nodes']} (ic: {r['inner_nodes']}, yaprak: {r['leaf_nodes']})")
print(f"    Gecerli: {r['is_valid']}")
print("    Feature onemi:")
for fi in r["feature_importance"][:3]:
    print(f"      {fi['rank']}. {fi['feature']}: {fi['score']:.4f}")

# 3: Inference
print("[3] Cikarim yapiliyor...")
customer = {
    "age": 34, "income": 72000, "credit_score": 742,
    "has_prior_default": False, "employment_status": "EMPLOYED",
    "debt_to_income": 0.28, "existing_credits": 1,
    "loan_amount": 50000, "full_name": "Mehmet Yilmaz"
}
r = api("POST", "/inference", customer)
inference_id = r["inference_id"]
print(f"    KARAR: {r['decision']} (guven: {r['confidence']:.1%}, derinlik: {r['depth_reached']})")
print(f"    Inference ID: {inference_id[:12]}...")
print(f"    Path adimlari: {len(r['path'])}")

# 4: Explanation
print("[4] XAI aciklama aliniyor...")
r = api("GET", f"/explanation/{inference_id}")
print(f"    Boolean: {r['boolean_formula'][:80]}...")
nl = r["natural_language"].replace("\n", " ")
print(f"    NL rapor: {nl[:100]}...")

# 5: Logs
print("[5] Loglar listeleniyor...")
r = api("GET", "/logs?page=1&size=10")
print(f"    Toplam log: {r['total']}")
for item in r["items"]:
    decision = item.get("decision", "?")
    print(f"    - [{item['type']}] karar: {decision}")

print()
print("Tum API endpoint testleri basarili!")
