import React, { useState } from "react";
import { Upload, FileText, Image as ImageIcon, Sparkles, AlertCircle } from "lucide-react";
import { uploadBill } from "../api";

export default function StepUpload({ onExtractionComplete }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
      setError(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      setFiles(Array.from(e.dataTransfer.files));
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError("Please select at least one bill photo.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await uploadBill(files);
      onExtractionComplete(data);
    } catch (err) {
      setError(err.message || "Failed to extract bill. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      // Create a dummy image blob to trigger the mock extractor
      const dummyBlob = new Blob(["mock-bill-image-content"], { type: "image/jpeg" });
      const demoFile = new File([dummyBlob], "sample_receipt.jpg", { type: "image/jpeg" });
      const data = await uploadBill([demoFile]);
      onExtractionComplete(data);
    } catch (err) {
      setError(err.message || "Failed to load demo bill.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2 className="card-title">
        <ImageIcon size={22} className="text-primary" />
        Upload Restaurant Bill Photo(s)
      </h2>
      <p className="card-desc">
        Upload a single receipt or multiple overlapping photos for long bills.
        Our Vision LLM extracts line items, taxes, discounts, and totals with per-item confidence scores.
      </p>

      {error && (
        <div className="banner banner-danger">
          <AlertCircle size={20} />
          <div>{error}</div>
        </div>
      )}

      <div
        className="dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => document.getElementById("bill-file-input").click()}
      >
        <Upload size={44} style={{ color: "#60a5fa", margin: "0 auto 1rem" }} />
        <p style={{ fontWeight: 600, fontSize: "1.05rem", marginBottom: "0.25rem" }}>
          Drag & drop bill photos here, or click to browse
        </p>
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Supports JPG, PNG, WEBP (Single or multi-page receipts)
        </p>
        <input
          id="bill-file-input"
          type="file"
          multiple
          accept="image/*"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
      </div>

      {files.length > 0 && (
        <div style={{ marginTop: "1.25rem" }}>
          <p style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.5rem" }}>
            Selected Files ({files.length}):
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {files.map((f, i) => (
              <span key={i} className="badge badge-success" style={{ padding: "0.4rem 0.7rem" }}>
                <FileText size={14} /> {f.name} ({(f.size / 1024).toFixed(1)} KB)
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="action-bar">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleLoadDemo}
          disabled={loading}
        >
          <Sparkles size={16} /> Use Sample Demo Bill
        </button>

        <button
          type="button"
          className="btn btn-primary"
          onClick={handleUpload}
          disabled={loading || files.length === 0}
        >
          {loading ? "Extracting with Vision AI..." : `Extract Bill (${files.length} Photo${files.length > 1 ? "s" : ""})`}
        </button>
      </div>
    </div>
  );
}
