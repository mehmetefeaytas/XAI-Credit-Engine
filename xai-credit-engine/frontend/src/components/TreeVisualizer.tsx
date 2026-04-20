import React, { useEffect, useState, useCallback, useMemo } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { API_BASE } from "../App";

// Custom Nodes
const DecisionNode = ({ data }: any) => {
  return (
    <div className="react-flow__node-decision">
      <Handle type="target" position={Position.Top} />
      <div
        style={{ fontWeight: "bold", fontSize: "14px", marginBottom: "4px" }}
      >
        {data.feature}
      </div>
      <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.7)" }}>
        Entropi: {data.entropy.toFixed(3)}
      </div>
      <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.7)" }}>
        Örnek: {data.samples}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

const LeafNode = ({ data }: any) => {
  return (
    <div className={`react-flow__node-leaf ${data.label?.toLowerCase()}`}>
      <Handle type="target" position={Position.Top} />
      <div>{data.label}</div>
      <div style={{ fontSize: "10px", marginTop: "4px", opacity: 0.8 }}>
        Örnek: {data.samples}
      </div>
    </div>
  );
};

const nodeTypes = {
  decision: DecisionNode,
  leaf: LeafNode,
};

export default function TreeVisualizer() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [importance, setImportance] = useState<any[]>([]);

  useEffect(() => {
    const fetchFullTree = async () => {
      try {
        // 1. Get active tree ID
        const activeRes = await fetch(`${API_BASE}/tree/active`);
        if (!activeRes.ok) {
          setError(
            "Aktif bir ağaç bulunamadı. Lütfen önce 'Sistem' sekmesinden ağacı inşa edin.",
          );
          setLoading(false);
          return;
        }
        const activeData = await activeRes.json();

        // Bu sürüm için özellik önemini kaydet
        // Gerçek API'de ağaç inşa tepkisinde dönüyor, bu yüzden basit olsun diye /tree/build cevabında cached veya state lazımdı.
        // Ama biz ağacın tam yapısını getirmeliyiz. Şimdilik "ağacın tam modeli" API'de /tree/{version_id}
        // Maalesef ağacın nodes/edges bilgisi GET endpoint'inde eksik olabilir (Adım 2'de metadata dönüyorduk sadece)
        // Eğer nodes dönmüyorsa, UI'da ağaç çizemeyeceğiz anlamına gelir. Biz geçici olarak tree listesinden root idsini vs okuyamayacağımız için burada hata verebilir.
        throw new Error(
          "UI Ağaç çizim API'si henüz backend'de Nodes ve Edges döndürmüyor, bu bölüm için Backend'de GET /tree/{id}/nodes çağrısı gereklidir.",
        );
      } catch (err: any) {
        setError(err.message || "Bir hata oluştu");
        setLoading(false);
      }
    };

    fetchFullTree();
  }, []);

  if (loading)
    return (
      <div
        className="glass-card"
        style={{ textAlign: "center", padding: "3rem" }}
      >
        <div className="loader" style={{ margin: "0 auto" }}></div>
      </div>
    );

  if (error)
    return (
      <div className="glass-card" style={{ borderColor: "var(--warning)" }}>
        <h3 className="text-warning">Görselleştirme Kullanılamıyor</h3>
        <p>{error}</p>
        <p
          className="text-muted"
          style={{ marginTop: "1rem", fontSize: "0.9rem" }}
        >
          Not: Backend (Adım 2), tam graf node'larını GET endpoint'inde
          döndürmeyecek şekilde (sadece metadata) tasarlandı. Graph ağacı çizmek
          için FastAPI tarafında güncelleme gerekebilir.
        </p>
      </div>
    );

  return (
    <div
      className="glass-card"
      style={{ height: "75vh", padding: 0, overflow: "hidden" }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background color="#fff" gap={16} />
        <MiniMap
          nodeColor={(n) => {
            if (n.type === "leaf")
              return n.data.label === "APPROVED" ? "#10B981" : "#EF4444";
            return "#4F46E5";
          }}
        />
        <Controls />
      </ReactFlow>
    </div>
  );
}
