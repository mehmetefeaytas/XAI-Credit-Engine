import React, { useEffect, useState, useCallback } from "react";
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
import dagre from "dagre";
import { API_BASE } from "../App";

const FEATURE_LABELS: Record<string, string> = {
  income_gt_50k: "Yıllık Gelir > 50.000 TL",
  credit_score_gt_700: "Kredi Puanı > 700",
  has_prior_default: "Geçmiş İcra Kaydı Var",
  debt_to_income_lt_35: "Borç/Gelir Oranı < %35",
  employment_employed: "Düzenli / Maaşlı Çalışan",
  age_gte_25: "Yaş ≥ 25",
  existing_credits_lt_3: "Aktif Kredi Sayısı < 3",
};

const DecisionNode = ({ data }: any) => {
  const label = FEATURE_LABELS[data.feature_name] || data.feature_name;
  return (
    <div className="react-flow__node-decision">
      <Handle type="target" position={Position.Top} />
      <div
        style={{
          fontWeight: "bold",
          fontSize: "12px",
          marginBottom: "4px",
          padding: "0 4px",
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.7)" }}>
        Entropi: {data.entropy?.toFixed(3)}
      </div>
      <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.7)" }}>
        Örnek Sayısı: {data.sample_count}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

const LeafNode = ({ data }: any) => {
  return (
    <div className={`react-flow__node-leaf ${data.leaf_label?.toLowerCase()}`}>
      <Handle type="target" position={Position.Top} />
      <div>{data.leaf_label}</div>
      <div style={{ fontSize: "10px", marginTop: "4px", opacity: 0.8 }}>
        Örnek: {data.sample_count}
      </div>
    </div>
  );
};

const nodeTypes = {
  decision: DecisionNode,
  leaf: LeafNode,
};

const layoutElements = (nodes: any[], edges: any[], direction = "TB") => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({
    rankdir: direction,
    align: "UL",
    nodesep: 60,
    edgesep: 20,
    ranksep: 80,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 180, height: 80 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
      position: {
        x: nodeWithPosition.x - 180 / 2,
        y: nodeWithPosition.y - 80 / 2,
      },
    };
  });

  return { nodes: newNodes, edges };
};

export default function TreeVisualizer() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFullTree = async () => {
      try {
        setLoading(true);
        // 1. Aktif ağacın IDsini al
        const activeRes = await fetch(`${API_BASE}/tree/active`);
        if (!activeRes.ok) {
          setError(
            "Aktif bir ağaç bulunamadı. Lütfen önce 'Sistem' sekmesinden ağacı inşa edin.",
          );
          setLoading(false);
          return;
        }
        const activeData = await activeRes.json();
        const activeId = activeData.version_id;

        // 2. Tam ağacı Node ve Edge verileriyle çek
        const treeRes = await fetch(`${API_BASE}/tree/${activeId}`);
        if (!treeRes.ok) {
          throw new Error("Ağaç verileri getirilemedi.");
        }

        const treeData = await treeRes.json();

        // 3. Backend formatını React Flow formatına dönüştür
        const flowNodes = treeData.nodes.map((n: any) => ({
          id: n.id,
          type: n.is_leaf ? "leaf" : "decision",
          data: { ...n },
          position: { x: 0, y: 0 }, // Dagre tarafından düzenlenecek
        }));

        const flowEdges = treeData.edges.map((e: any) => ({
          id: e.id,
          source: e.source_node_id,
          target: e.target_node_id,
          label: e.branch_value ? "Evet" : "Hayır",
          type: "smoothstep",
          animated: true,
          style: {
            stroke: e.branch_value ? "#10B981" : "#EF4444",
            strokeWidth: 2,
          },
          labelStyle: { fill: "#333", fontWeight: 700 },
          labelBgStyle: { fill: "rgba(255, 255, 255, 0.75)" },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: e.branch_value ? "#10B981" : "#EF4444",
          },
        }));

        // 4. Dagre ile düzenle (Layout)
        const { nodes: layoutedNodes, edges: layoutedEdges } = layoutElements(
          flowNodes,
          flowEdges,
        );

        setNodes(layoutedNodes);
        setEdges(layoutedEdges);
        setLoading(false);
      } catch (err: any) {
        setError(err.message || "Bir hata oluştu");
        setLoading(false);
      }
    };

    fetchFullTree();
  }, [setNodes, setEdges]);

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
        <h3 className="text-warning">Ağaç Görselleştirme</h3>
        <p>{error}</p>
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
        attributionPosition="bottom-right"
      >
        <Background color="#ccc" gap={16} />
        <MiniMap
          nodeColor={(n) => {
            if (n.type === "leaf")
              return n.data.leaf_label === "APPROVED" ? "#10B981" : "#EF4444";
            return "#4F46E5";
          }}
          maskColor="rgba(0,0,0,0.2)"
        />
        <Controls />
      </ReactFlow>
    </div>
  );
}
