"""
app/api/v1/tree.py
──────────────────────────────────────────────────────────────────────────────
Karar ağacı inşa ve yönetim endpoint'leri (SQLAlchemy Destekli).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import get_settings
from app.data.database import get_db
from app.data.models.dataset_model import DatasetModel
from app.data.models.tree_model import TreeVersionModel, DecisionNodeModel, TreeEdgeModel
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

router   = APIRouter()
settings = get_settings()

@router.post("/build", response_model=TreeBuildResponse, status_code=201, summary="Karar ağacı inşa et")
async def build_tree(req: TreeBuildRequest, db: AsyncSession = Depends(get_db)):
    # Dataset'i DB'den çek
    result = await db.execute(select(DatasetModel))
    records = result.scalars().all()
    
    if not records:
        raise HTTPException(
            status_code=409,
            detail={"code": "DATASET_EMPTY", "message": "Dataset boş. Önce /dataset/generate çağırın."},
        )

    # Ağaç algoritması için dictionary listesine çevir
    dataset = []
    for r in records:
        row = dict(r.feature_vector)
        row["decision"] = r.decision
        dataset.append(row)
        
    features = DatasetService.feature_names()

    # Feature önem hesapla
    ig_calc = InformationGainCalculator(EntropyCalculator())
    ig_scores = ig_calc.rank_features(
        dataset=dataset,
        label_col="decision",
        feature_cols=features,
        use_gain_ratio=req.use_gain_ratio,
    )

    # Ağacı inşa et
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

    # Doğrula
    validator = TreeValidator()
    val_result = validator.validate(all_nodes, edges)
    max_depth_reached = max(n.depth for n in all_nodes) if all_nodes else 0

    # Versiyon Model
    version_id = str(uuid.uuid4())
    
    # Eskileri deaktif et
    await db.execute(update(TreeVersionModel).values(is_active=False))
    
    tree_version = TreeVersionModel(
        id=version_id,
        training_size=len(records),
        total_nodes=stats["total_nodes"],
        leaf_nodes=stats["leaf_nodes"],
        inner_nodes=stats["inner_nodes"],
        max_depth_reached=max_depth_reached,
        is_valid=val_result.is_valid,
        description=req.description,
        is_active=True,
        root_node_id=str(root.id)
    )
    db.add(tree_version)
    
    # Nodeları DB'ye ekle
    node_responses = []
    for n in all_nodes:
        db_node = DecisionNodeModel(
            id=str(n.id),
            tree_version_id=version_id,
            feature_name=n.feature_name,
            threshold=n.threshold,
            operator=n.operator,
            is_leaf=n.is_leaf,
            leaf_label=n.leaf_label,
            depth=n.depth,
            entropy=n.entropy,
            sample_count=n.sample_count
        )
        db.add(db_node)
        node_responses.append(NodeResponse(**db_node.__dict__))
        
    # Edgeları DB'ye ekle
    edge_responses = []
    for e in edges:
        db_edge = TreeEdgeModel(
            id=str(e.id),
            tree_version_id=version_id,
            source_node_id=str(e.source_node_id),
            target_node_id=str(e.target_node_id),
            branch_value=e.branch_value
        )
        db.add(db_edge)
        edge_responses.append(EdgeResponse(**db_edge.__dict__))

    await db.commit()

    feature_importance = [
        FeatureImportanceItem(feature=f, score=round(s, 6), rank=i + 1)
        for i, (f, s) in enumerate(ig_scores)
    ]

    return TreeBuildResponse(
        version_id=version_id,
        built_at=tree_version.built_at.isoformat() if tree_version.built_at else datetime.now(timezone.utc).isoformat(),
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


@router.get("", summary="Tüm ağaç versiyonlarını listele")
async def list_trees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TreeVersionModel).order_by(TreeVersionModel.built_at.desc()))
    versions = result.scalars().all()
    
    items = []
    active_version = None
    for v in versions:
        if v.is_active:
            active_version = v.id
        items.append(TreeListItem(
            version_id=v.id,
            built_at=v.built_at.isoformat() if v.built_at else "",
            total_nodes=v.total_nodes,
            is_active=v.is_active,
            training_size=v.training_size,
            description=v.description or ""
        ))
        
    return {"total": len(items), "active_version": active_version, "trees": items}


@router.get("/active", summary="Aktif ağacı döner")
async def get_active(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TreeVersionModel).where(TreeVersionModel.is_active == True))
    active = result.scalars().first()
    if not active:
        raise HTTPException(
            status_code=404,
            detail={"code": "NO_ACTIVE_TREE", "message": "Aktif ağaç yok. Önce /tree/build çağırın."},
        )
    
    return {
        "version_id": active.id,
        "built_at": active.built_at.isoformat(),
        "training_size": active.training_size,
        "total_nodes": active.total_nodes,
        "leaf_nodes": active.leaf_nodes,
        "inner_nodes": active.inner_nodes,
        "max_depth_reached": active.max_depth_reached,
        "is_valid": active.is_valid,
        "is_active": active.is_active
    }


@router.get("/{version_id}", summary="Belirli versiyon ağacı döner (grafıyla birlikte)")
async def get_tree_by_version(version_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TreeVersionModel).where(TreeVersionModel.id == version_id))
    tree_data = result.scalars().first()
    if not tree_data:
        raise HTTPException(
            status_code=404,
            detail={"code": "TREE_NOT_FOUND", "message": f"Versiyon '{version_id}' bulunamadı."},
        )
        
    # Ağacın tüm node ve edgeleri de döndürülmeli ki Frontend React flow kullansın
    nodes_res = await db.execute(select(DecisionNodeModel).where(DecisionNodeModel.tree_version_id == version_id))
    edges_res = await db.execute(select(TreeEdgeModel).where(TreeEdgeModel.tree_version_id == version_id))
    
    nodes = nodes_res.scalars().all()
    edges = edges_res.scalars().all()

    return {
        "version_id": tree_data.id,
        "built_at": tree_data.built_at.isoformat(),
        "training_size": tree_data.training_size,
        "total_nodes": tree_data.total_nodes,
        "root_node_id": tree_data.root_node_id,
        "is_active": tree_data.is_active,
        "nodes": [NodeResponse(**n.__dict__) for n in nodes],
        "edges": [EdgeResponse(**e.__dict__) for e in edges]
    }
