import React, { useState } from "react";
import { API_BASE } from "../App";
import { Send, FileText, CheckCircle, XCircle } from "lucide-react";

export default function InferenceForm() {
  const [formData, setFormData] = useState({
    full_name: "Ahmet Yılmaz",
    age: 30,
    income: 60000,
    credit_score: 720,
    has_prior_default: "false",
    employment_status: "EMPLOYED",
    debt_to_income: 0.25,
    existing_credits: 1,
    loan_amount: 50000,
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [explanation, setExplanation] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setExplanation(null);

    try {
      const payload = {
        ...formData,
        age: Number(formData.age),
        income: Number(formData.income),
        credit_score: Number(formData.credit_score),
        has_prior_default: formData.has_prior_default === "true",
        debt_to_income: Number(formData.debt_to_income),
        existing_credits: Number(formData.existing_credits),
        loan_amount: Number(formData.loan_amount),
      };

      // 1. Çıkarım Yap
      const infRes = await fetch(`${API_BASE}/inference`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!infRes.ok) {
        const err = await infRes.json();
        throw new Error(
          err.detail?.message ||
            "Çıkarım başarısız oldu (Ağaç aktif olmayabilir).",
        );
      }

      const infData = await infRes.json();
      setResult(infData);

      // 2. Açıklama Üret
      const expRes = await fetch(
        `${API_BASE}/explanation/${infData.inference_id}?language=tr`,
      );
      if (expRes.ok) {
        setExplanation(await expRes.json());
      }
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <div className="grid-2">
      <div className="glass-card">
        <h3>Yeni Kredi Başvurusu</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Ad Soyad</label>
            <input
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              required
            />
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1rem",
            }}
          >
            <div className="form-group">
              <label>Yaş</label>
              <input
                type="number"
                name="age"
                value={formData.age}
                onChange={handleChange}
                min={18}
                max={100}
                required
              />
            </div>
            <div className="form-group">
              <label>Yıllık Gelir (TL)</label>
              <input
                type="number"
                name="income"
                value={formData.income}
                onChange={handleChange}
                min={1}
                required
              />
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1rem",
            }}
          >
            <div className="form-group">
              <label>Kredi Puanı</label>
              <input
                type="number"
                name="credit_score"
                value={formData.credit_score}
                onChange={handleChange}
                min={300}
                max={850}
                required
              />
            </div>
            <div className="form-group">
              <label>Borç / Gelir Oranı</label>
              <input
                type="number"
                name="debt_to_income"
                value={formData.debt_to_income}
                onChange={handleChange}
                step={0.01}
                min={0}
                max={1}
                required
              />
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1rem",
            }}
          >
            <div className="form-group">
              <label>Geçmiş İcra Kaydı</label>
              <select
                name="has_prior_default"
                value={formData.has_prior_default}
                onChange={handleChange}
              >
                <option value="false">Yok</option>
                <option value="true">Var</option>
              </select>
            </div>
            <div className="form-group">
              <label>Çalışma Durumu</label>
              <select
                name="employment_status"
                value={formData.employment_status}
                onChange={handleChange}
              >
                <option value="EMPLOYED">Maaşlı</option>
                <option value="SELF_EMPLOYED">Serbest Meslek</option>
                <option value="UNEMPLOYED">Çalışmıyor</option>
              </select>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1rem",
            }}
          >
            <div className="form-group">
              <label>Mevcut Aktif Kredi Sayısı</label>
              <input
                type="number"
                name="existing_credits"
                value={formData.existing_credits}
                onChange={handleChange}
                min={0}
                required
              />
            </div>
            <div className="form-group">
              <label>Kredi Tutarı (TL)</label>
              <input
                type="number"
                name="loan_amount"
                value={formData.loan_amount}
                onChange={handleChange}
                min={1000}
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn"
            style={{ width: "100%", marginTop: "1rem" }}
            disabled={loading}
          >
            {loading ? (
              <div className="loader" />
            ) : (
              <>
                <Send size={18} /> Değerlendir
              </>
            )}
          </button>
        </form>

        {error && (
          <div
            className="text-danger"
            style={{
              marginTop: "1rem",
              padding: "1rem",
              background: "rgba(239, 68, 68, 0.1)",
              borderRadius: "8px",
            }}
          >
            {error}
          </div>
        )}
      </div>

      <div
        className="glass-card"
        style={{ display: "flex", flexDirection: "column" }}
      >
        <h3>
          <FileText
            size={20}
            style={{ verticalAlign: "middle", marginRight: 8 }}
          />{" "}
          Sistem Kararı ve Gerekçesi
        </h3>

        {!result && !loading && (
          <div
            style={{
              display: "flex",
              flex: 1,
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-muted)",
            }}
          >
            Başvuru verilerini gönderdikten sonra sistem kararı ve yasal XAI
            raporu burada görünecektir.
          </div>
        )}

        {result && (
          <div
            style={{
              marginTop: "1rem",
              flex: 1,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "1rem",
                padding: "1rem",
                background: "rgba(0,0,0,0.2)",
                borderRadius: "8px",
                marginBottom: "1.5rem",
              }}
            >
              {result.decision === "APPROVED" ? (
                <CheckCircle size={48} className="text-success" />
              ) : (
                <XCircle size={48} className="text-danger" />
              )}
              <div>
                <div
                  style={{ fontSize: "1.5rem", fontWeight: "bold" }}
                  className={
                    result.decision === "APPROVED"
                      ? "text-success"
                      : "text-danger"
                  }
                >
                  {result.decision}
                </div>
                <div className="text-muted" style={{ fontSize: "0.9rem" }}>
                  Güven Skoru: {(result.confidence * 100).toFixed(1)}% | Kural
                  Derinliği: {result.depth_reached}
                </div>
              </div>
            </div>

            {explanation && (
              <>
                <div style={{ marginBottom: "1rem" }}>
                  <h4
                    style={{
                      color: "var(--text-main)",
                      marginBottom: "0.5rem",
                    }}
                  >
                    Doğal Dil Raporu (GDPR Uyumu)
                  </h4>
                  <div
                    style={{
                      whiteSpace: "pre-wrap",
                      background: "rgba(0,0,0,0.3)",
                      padding: "1rem",
                      borderRadius: "8px",
                      fontSize: "0.95rem",
                      lineHeight: "1.5",
                    }}
                  >
                    {explanation.natural_language}
                  </div>
                </div>

                <div style={{ marginTop: "auto" }}>
                  <h4
                    style={{
                      color: "var(--text-main)",
                      marginBottom: "0.5rem",
                    }}
                  >
                    Boolean Karar Mantığı Formülü
                  </h4>
                  <pre>{explanation.boolean_formula}</pre>
                </div>

                <div
                  style={{
                    marginTop: "1rem",
                    padding: "1rem",
                    background: "rgba(59, 130, 246, 0.1)",
                    borderLeft: "4px solid #3b82f6",
                    borderRadius: "4px",
                    fontSize: "0.85rem",
                    color: "var(--text-muted)",
                    lineHeight: "1.4",
                  }}
                >
                  <strong>GDPR Madde 22 Hakkında:</strong> GDPR Madde 22,
                  bireylerin, yalnızca otomatik işlemeye (yapay zeka, profil
                  oluşturma vb.) dayalı ve kendisi üzerinde hukuki veya benzeri
                  önemli etkiler yaratan kararlara tabi tutulmama hakkını
                  düzenler. Bu madde, insan müdahalesi, görüş bildirme ve
                  karara itiraz etme haklarını güvence altına alarak,
                  otomasyonun getirdiği riskleri sınırlar.
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
