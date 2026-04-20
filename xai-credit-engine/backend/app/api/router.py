"""
app/api/router.py
──────────────────────────────────────────────────────────────────────────────
Tüm API router'larının merkezi toplayıcısı.

v1 endpoint'leri:
    /api/v1/dataset     → Dataset CRUD (generate, list, delete)
    /api/v1/tree        → Ağaç inşa, listeleme, versiyon
    /api/v1/inference   → Müşteri değerlendirmesi
    /api/v1/explanation → XAI açıklama raporu
    /api/v1/logs        → Audit log listeleme
"""

from fastapi import APIRouter

from app.api.v1 import dataset, tree, inference, explanation, logs

api_router = APIRouter()

# ── v1 Router'ları ────────────────────────────────────────────────────────────
api_router.include_router(
    dataset.router,
    prefix="/dataset",
    tags=["Dataset"],
)

api_router.include_router(
    tree.router,
    prefix="/tree",
    tags=["Tree"],
)

api_router.include_router(
    inference.router,
    prefix="/inference",
    tags=["Inference"],
)

api_router.include_router(
    explanation.router,
    prefix="/explanation",
    tags=["Explanation"],
)

api_router.include_router(
    logs.router,
    prefix="/logs",
    tags=["Logs"],
)
