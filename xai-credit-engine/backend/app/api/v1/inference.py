"""
app/api/v1/inference.py
──────────────────────────────────────────────────────────────────────────────
Müşteri kredi değerlendirmesi endpoint'i (SQLAlchemy Destekli).
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.data.database import get_db
from app.data.models.tree_model import TreeVersionModel, DecisionNodeModel, TreeEdgeModel
from app.data.models.log_model import InferenceLogModel
from app.domain.models.customer import Customer, EmploymentStatus
from app.domain.models.decision_node import DecisionTreeNode, DecisionTreeEdge
from app.engine.inference.inference_engine import InferenceEngine
from app.schemas.inference_schema import InferenceRequest, InferenceResponse, PathStep

router = APIRouter()

async def get_active_tree(db: AsyncSession):
    # Aktif ağaç versiyonunu bul
    res_tv = await db.execute(select(TreeVersionModel).where(TreeVersionModel.is_active == True))
    tree_ver = res_tv.scalars().first()
    if not tree_ver:
        return None
        
    # Ağacın düğümlerini ve kenarlarını getir
    res_nodes = await db.execute(select(DecisionNodeModel).where(DecisionNodeModel.tree_version_id == tree_ver.id))
    db_nodes = res_nodes.scalars().all()
    
    res_edges = await db.execute(select(TreeEdgeModel).where(TreeEdgeModel.tree_version_id == tree_ver.id))
    db_edges = res_edges.scalars().all()
    
    # DB Modelinden -> Domain Modeline dönüştür
    node_map = {}
    for dn in db_nodes:
        node = DecisionTreeNode(
            id=uuid.UUID(dn.id),
            feature_name=dn.feature_name,
            threshold=dn.threshold,
            operator=dn.operator,
            is_leaf=dn.is_leaf,
            leaf_label=dn.leaf_label,
            depth=dn.depth,
            entropy=dn.entropy,
            sample_count=dn.sample_count
        )
        node_map[str(node.id)] = node
        
    for de in db_edges:
        source = node_map[de.source_node_id]
        target = node_map[de.target_node_id]
        
        # Domain model edge nesnesi oluştur (eğer ileride lazımsa)
        edge = DecisionTreeEdge(
            id=uuid.UUID(de.id),
            source_node_id=source.id,
            target_node_id=target.id,
            branch_value=de.branch_value
        )
        
        # In-memory ağaç traverslı için çocukları set et
        if de.branch_value:
            source.child_true = target
        else:
            source.child_false = target
        
    root_node = node_map.get(tree_ver.root_node_id)
    return {
        "metadata": {
            "version_id": tree_ver.id
        },
        "root": root_node
    }


@router.post("", response_model=InferenceResponse, status_code=200, summary="Müşteri kredi değerlendirmesi")
async def run_inference(req: InferenceRequest, db: AsyncSession = Depends(get_db)):
    # ── Aktif ağacı yükle ─────────────────────────────────────────────────────
    tree_data = await get_active_tree(db)
    if not tree_data:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_ACTIVE_TREE", "message": "Aktif bir karar ağacı yok. Önce /tree/build çağırın."}
        )

    # ── Müşteri domain modeli oluştur ─────────────────────────────────────────
    try:
        employment = EmploymentStatus(req.employment_status.upper())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_EMPLOYMENT", "message": "Geçersiz employment_status."}
        )

    customer = Customer(**req.model_dump())

    try:
        customer.validate()
    except ValueError as e:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": str(e)})

    # ── Feature vektörüne dönüştür ────────────────────────────────────────────
    feature_vector = customer.to_feature_vector()

    # ── Çıkarım yap ───────────────────────────────────────────────────────────
    root = tree_data["root"]
    engine = InferenceEngine(root_node=root)

    try:
        result = engine.predict(feature_vector)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "INFERENCE_ERROR", "message": f"Çıkarım hatası: {str(e)}"},
        )

    # ── Sonucu DB logla ───────────────────────────────────────────────────────
    inference_id = str(uuid.uuid4())
    version_id = tree_data["metadata"]["version_id"]

    path_dicts = result.path_as_dicts()

    inf_log = InferenceLogModel(
        id=inference_id,
        tree_version_id=version_id,
        customer_name=req.full_name,
        decision=result.decision,
        confidence=result.confidence,
        depth_reached=result.depth_reached,
        feature_vector=feature_vector,
        path=path_dicts
    )
    db.add(inf_log)
    await db.commit()
    await db.refresh(inf_log)

    # ── Response döner ────────────────────────────────────────────────────────
    path_steps = [
        PathStep(
            node_id=step.node_id,
            feature=step.feature,
            threshold=step.threshold,
            operator=step.operator,
            input_value=step.input_value,
            branch_taken=step.branch_taken,
            depth=step.depth,
        )
        for step in result.path
    ]

    return InferenceResponse(
        inference_id=inference_id,
        decision=result.decision,
        confidence=round(result.confidence, 4),
        depth_reached=result.depth_reached,
        path=path_steps,
        feature_vector=feature_vector,
        tree_version_id=version_id,
        created_at=inf_log.created_at.isoformat()
    )
