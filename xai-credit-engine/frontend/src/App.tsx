import React, { useState } from "react";
import Dashboard from "./components/Dashboard";
import TreeVisualizer from "./components/TreeVisualizer";
import InferenceForm from "./components/InferenceForm";
import { Activity, GitMerge, FileCheck } from "lucide-react";

export const API_BASE = "http://127.0.0.1:8000/api/v1";

function App() {
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "tree" | "inference"
  >("dashboard");

  return (
    <div className="container">
      <header className="header">
        <div>
          <h1>XAI Credit Engine</h1>
          <p className="text-muted">
            Açıklanabilir Yapay Zeka (XAI) Tabanlı Otonom Kredi Onay Sistemi
          </p>
        </div>
        <nav style={{ display: "flex", gap: "1rem" }}>
          <button
            className={`btn ${activeTab === "dashboard" ? "" : "btn-outline"}`}
            onClick={() => setActiveTab("dashboard")}
          >
            <Activity size={18} /> Sistem / Veri
          </button>
          <button
            className={`btn ${activeTab === "tree" ? "" : "btn-outline"}`}
            onClick={() => setActiveTab("tree")}
          >
            <GitMerge size={18} /> Karar Ağacı
          </button>
          <button
            className={`btn ${activeTab === "inference" ? "" : "btn-outline"}`}
            onClick={() => setActiveTab("inference")}
          >
            <FileCheck size={18} /> Kredi Başvurusu
          </button>
        </nav>
      </header>

      <main>
        {activeTab === "dashboard" && <Dashboard />}
        {activeTab === "tree" && <TreeVisualizer />}
        {activeTab === "inference" && <InferenceForm />}
      </main>
    </div>
  );
}

export default App;
