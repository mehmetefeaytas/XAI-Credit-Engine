"""
app/api/v1/tree.py
──────────────────────────────────────────────────────────────────────────────
Karar ağacı inşa ve yönetim endpoint'leri.

POST /api/v1/tree/build          → Dataset'ten ağaç inşa et
GET  /api/v1/tree                → Tüm ağaç versiyonlarını listele
GET  /api/v1/tree/active         → Aktif (güncel) ağacı döner
GET  /api/v1/tree/{version_id}   → Belirli versiyonu döner
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.domain.services.dataset_service import DatasetService
from app.engine.tree.tree_builder import TreeBuilder, TreeBuildConfig
from app.engine.tree.tree_validator import TreeValidator
from app.engine.math.information_gain import InformationGainCalculator
from app.engine.math.entropy_calculator import EntropyCalculator
from app.schemas.tree_schema import (
    TreeBuildRequest,
    TreeBuildResponse,
    TreeListItem,
    NodeResponse,
    EdgeResponse,
    FeatureImportanceItem,
)
from app.api.v1.dataset import get_dataset_store

router   = APIRouter()
settings = get_settings()


# ── In-Memory Ağaç Deposu ────────────────────────────────────────────────────
# {version_id: {root, nodes, edges, metadata, is_active}}
_tree_store:       dict[str, dict] = {}
_active_version:   str | None      = None


def get_active_tree() -> dict | None:
    """Aktif ağaç versiyonunu döner. Dış modüller (inference) için."""
    global _tree_store, _active_version
    if _active_version and _active_version in _tree_store:
        return _tree_store[_active_version]
    return None


# ── POST /tree/build ─────────────────────────────────────────────────────────
@router.post("/build", response_model=TreeBuildResponse, status_code=201,
             summary="Karar ağacı inşa et")
async def build_tree(req: TreeBuildRequest):
    """
    Mevcut dataset üzerinde ID3 algoritması ile karar ağacı inşa eder.

    **Önce** `/dataset/generate` çağrılmış olmalıdır.

    - **max_depth**: Maksimum derinlik (1-20)
    - **min_samples_split**: Bölme için min örnek
    - **use_gain_ratio**: True=GainRatio (C4.5), False=IG (ID3)

    Başarılı build sonrası bu versiyon **aktif** hale gelir.
    """
    global _tree_store, _active_version

    # Dataset kontrolü
    records = get_dataset_store()
    if not records:
        raise HTTPException(
            status_code=409,
            detail={
                "code":    "DATASET_EMPTY",
                "message": "Dataset boş. Önce /dataset/generate çağırın.",
            },
        )

    # Dataset'i ağaç formatına çevir
    dataset  = DatasetService().to_tree_dataset(records)
    features = DatasetService.feature_names()

    # Feature importance hesapla (build öncesi)
    ig_calc = InformationGainCalculator(EntropyCalculator())
    ig_scores = ig_calc.rank_features(
        dataset=dataset,
        label_col="decision",
        feature_cols=features,
        use_gain_ratio=req.use_gain_ratio,
    )

    # Ağaç inşa et
    config  = TreeBuildConfig(
        max_depth=req.max_depth,
        min_samples_split=req.min_samples_split,
        min_samples_leaf=req.min_samples_leaf,
        use_gain_ratio=req.use_gain_ratio,
    )
    builder = TreeBuilder(config=config)
    root    = builder.build(dataset, features, label_col="decision")
    edges   = builder.get_edges()
    stats   = builder.get_stats()
    all_nodes = builder.collect_all_nodes(root)

    # Ağacı doğrula
    validator = TreeValidator()
    val_result = validator.validate(all_nodes, edges)

    # Maksimum derinlik hesapla
    max_depth_reached = max(n.depth for n in all_nodes) if all_nodes else 0

    # Versiyon oluştur
    version_id = str(uuid.uuid4())
    built_at   = datetime.now(timezone.utc).isoformat()

    # Ağacı depoya kaydet
    _tree_store[version_id] = {
        "root":         root,
        "nodes":        all_nodes,
        "edges":        edges,
        "metadata": {
            "version_id":        version_id,
            "built_at":          built_at,
            "training_size":     len(records),
            "total_nodes":       stats["total_nodes"],
            "leaf_nodes":        stats["leaf_nodes"],
            "inner_nodes":       stats["inner_nodes"],
            "max_depth_reached": max_depth_reached,
            "is_valid":          val_result.is_valid,
            "description":       req.description,
        },
    }
    _active_version = version_id

    # Response oluştur
    node_responses = [
        NodeResponse(
            id=str(n.id),
            feature_name=n.feature_name,
            threshold=n.threshold,
            operator=n.operator,
            is_leaf=n.is_leaf,
            leaf_label=n.leaf_label,
            depth=n.depth,
            entropy=round(n.entropy, 6),
            sample_count=n.sample_count,
        )
        for n in all_nodes
    ]

    edge_responses = [
        EdgeResponse(
            id=str(e.id),
            source_node_id=str(e.source_node_id),
            target_node_id=str(e.target_node_id),
            branch_value=e.branch_value,
        )
        for e in edges
    ]

    feature_importance = [
        FeatureImportanceItem(feature=f, score=round(s, 6), rank=i + 1)
        for i, (f, s) in enumerate(ig_scores)
    ]

    return TreeBuildResponse(
        version_id=version_id,
        built_at=built_at,
        total_nodes=stats["total_nodes"],
        leaf_nodes=stats["leaf_nodes"],
        inner_nodes=stats["inner_nodes"],
        max_depth_reached=max_depth_reached,
        training_size=len(records),
        is_valid=val_result.is_valid,
        validation_errors=val_result.errors,
        feature_importance=feature_importance,
        root_node_id=str(root.id),
        nodes=node_responses,
        edges=edge_responses,
    )


# ── GET /tree ────────────────────────────────────────────────────────────────
@router.get("", summary="Tüm ağaç versiyonlarını listele")
async def list_trees():
    """Üretilmiş tüm ağaç versiyonlarını listeler."""
    global _tree_store, _active_version

    items = []
    for vid, tree_data in _tree_store.items():
        m = tree_data["metadata"]
        items.append(TreeListItem(
            version_id=m["version_id"],
            built_at=m["built_at"],
            total_nodes=m["total_nodes"],
            is_active=(vid == _active_version),
            training_size=m["training_size"],
            description=m.get("description", ""),
        ))

    return {"total": len(items), "active_version": _active_version, "trees": items}


# ── GET /tree/active ─────────────────────────────────────────────────────────
@router.get("/active", summary="Aktif ağacı döner")
async def get_active():
    """Şu an aktif olan ağacın meta verilerini döner."""
    global _active_version
    tree_data = get_active_tree()
    if not tree_data:
        raise HTTPException(
            status_code=404,
            detail={"code": "NO_ACTIVE_TREE", "message": "Aktif ağaç yok. Önce /tree/build çağırın."},
        )
    return {**tree_data["metadata"], "is_active": True}


# ── GET /tree/{version_id} ───────────────────────────────────────────────────
@router.get("/{version_id}", summary="Belirli versiyon ağacı döner")
async def get_tree_by_version(version_id: str):
    """Versiyon ID'siyle belirli bir ağacı döner."""
    global _tree_store, _active_version

    tree_data = _tree_store.get(version_id)
    if not tree_data:
        raise HTTPException(
            status_code=404,
            detail={"code": "TREE_NOT_FOUND", "message": f"Versiyon '{version_id}' bulunamadı."},
        )

    return {
        **tree_data["metadata"],
        "is_active": (version_id == _active_version),
    }
