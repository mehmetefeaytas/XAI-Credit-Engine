import React, { useState, useEffect } from "react";
import { API_BASE } from "../App";
import { Database, Zap, ArrowRight, ShieldCheck, Server } from "lucide-react";

interface Stats {
  total: number;
  approved: number;
  rejected: number;
  approval_rate: number;
  generated_at?: string;
  features?: string[];
  message?: string;
}

export default function Dashboard() {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [treeInfo, setTreeInfo] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [treeLoading, setTreeLoading] = useState(false);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/dataset/stats`);
      const data = await res.json();
      setStats(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchTree = async () => {
    try {
      const res = await fetch(`${API_BASE}/tree/active`);
      if (res.ok) {
        setTreeInfo(await res.json());
      } else {
        setTreeInfo(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/health");
      if (res.ok) setHealth(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchStats();
    fetchTree();
  }, []);

  const handleGenerateData = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/dataset/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          count: 5000,
          approval_ratio: 0.55,
          seed: Math.floor(Math.random() * 1000),
        }),
      });
      await fetchStats();
      // Veri değişince aktif ağaç uyuşmaz, tree bilgisini sıfırla
      setTreeInfo(null);
    } catch (e) {
      alert("Hata oluştu");
    }
    setLoading(false);
  };

  const handleBuildTree = async () => {
    setTreeLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tree/build`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ max_depth: 8, min_samples_split: 5 }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail?.message || "Ağaç inşa edilemedi");
      } else {
        await fetchTree();
      }
    } catch (e) {
      alert("Hata oluştu");
    }
    setTreeLoading(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      <div
        className="glass-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h2>
            <Server
              size={24}
              style={{ verticalAlign: "middle", marginRight: 8 }}
            />{" "}
            Sistem Durumu
          </h2>
          {health ? (
            <p className="text-muted">
              Bağlantı başarılı:{" "}
              <span className="text-success">REST API Çevrimiçi</span> (
              {health.version})
            </p>
          ) : (
            <p className="text-danger">
              Sunucuya bağlanılamıyor. Backend açık mı?
            </p>
          )}
        </div>
        <ShieldCheck size={48} color="var(--success)" opacity={0.6} />
      </div>

      <div className="grid-2">
        {/* Dataset Card */}
        <div className="glass-card">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "1rem",
            }}
          >
            <h3 style={{ margin: 0 }}>
              <Database
                size={20}
                style={{ verticalAlign: "middle", marginRight: 8 }}
              />{" "}
              Veri Seti
            </h3>
            <span
              className={`badge ${stats?.total ? "badge-success" : "badge-danger"}`}
            >
              {stats?.total ? "Hazır" : "Boş"}
            </span>
          </div>

          {stats?.total ? (
            <div style={{ marginBottom: "1.5rem" }}>
              <p>Sentetik Kredi Başvuru Verisi (ID3 için hazır)</p>
              <div style={{ display: "flex", gap: "2rem", marginTop: "1rem" }}>
                <div>
                  <div className="text-muted" style={{ fontSize: "0.85rem" }}>
                    TOPLAM KAYIT
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
                    {stats.total}
                  </div>
                </div>
                <div>
                  <div className="text-muted" style={{ fontSize: "0.85rem" }}>
                    ONAY (APPROVED)
                  </div>
                  <div
                    className="text-success"
                    style={{ fontSize: "1.5rem", fontWeight: "bold" }}
                  >
                    {stats.approved}
                  </div>
                </div>
                <div>
                  <div className="text-muted" style={{ fontSize: "0.85rem" }}>
                    RED (REJECTED)
                  </div>
                  <div
                    className="text-danger"
                    style={{ fontSize: "1.5rem", fontWeight: "bold" }}
                  >
                    {stats.rejected}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-muted" style={{ marginBottom: "1.5rem" }}>
              Sistemde şu an hiç müşteri başvurusu eğitimi verisi
              bulunmamaktadır.
            </p>
          )}

          <button
            className="btn"
            onClick={handleGenerateData}
            disabled={loading}
          >
            {loading ? (
              <div className="loader" />
            ) : (
              <>
                <Database size={16} />{" "}
                {stats?.total ? "Yeniden Üret" : "Sentetik Veri Üret"}
              </>
            )}
          </button>
        </div>

        {/* Tree Engine Card */}
        <div className="glass-card">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "1rem",
            }}
          >
            <h3 style={{ margin: 0 }}>
              <Zap
                size={20}
                style={{ verticalAlign: "middle", marginRight: 8 }}
              />{" "}
              Karar Ağacı Motoru
            </h3>
            <span
              className={`badge ${treeInfo ? "badge-success" : "badge-danger"}`}
            >
              {treeInfo ? "Aktif" : "Hazır Değil"}
            </span>
          </div>

          {treeInfo ? (
            <div style={{ marginBottom: "1.5rem" }}>
              <p>ID3 algoritması ile bilgi kazancı kullanılarak eğitildi.</p>
              <div style={{ display: "flex", gap: "2rem", marginTop: "1rem" }}>
                <div>
                  <div className="text-muted" style={{ fontSize: "0.85rem" }}>
                    TOPLAM DÜĞÜM
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
                    {treeInfo.total_nodes}
                  </div>
                </div>
                <div>
                  <div className="text-muted" style={{ fontSize: "0.85rem" }}>
                    MAKS. DERİNLİK
                  </div>
                  <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
                    {treeInfo.max_depth_reached}
                  </div>
                </div>
                <div>
                  <div className="text-muted" style={{ fontSize: "0.85rem" }}>
                    VALIDATION
                  </div>
                  <div
                    className="text-success"
                    style={{ fontSize: "1.5rem", fontWeight: "bold" }}
                  >
                    {treeInfo.is_valid ? "Pass ✓" : "Fail ✗"}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-muted" style={{ marginBottom: "1.5rem" }}>
              Mevcut veri seti üzerinde bir karar ağacı eğitimi başlatmanız
              gerekiyor.
            </p>
          )}

          <button
            className="btn btn-success"
            onClick={handleBuildTree}
            disabled={treeLoading || !stats?.total}
            title={!stats?.total ? "Önce veri üretmelisiniz" : ""}
          >
            {treeLoading ? (
              <div className="loader" />
            ) : (
              <>
                <ArrowRight size={16} /> Ağacı İnşa Et
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
