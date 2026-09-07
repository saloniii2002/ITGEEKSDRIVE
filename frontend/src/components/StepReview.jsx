import React, { useState } from "react";
import { CheckCircle2, AlertTriangle, Plus, Trash2, ShieldAlert, Cpu } from "lucide-react";
import { updateConfirmedBill, confirmBill } from "../api";

export default function StepReview({ billData, onConfirmComplete, onBack }) {
  const [items, setItems] = useState(billData.initial_confirmed?.items || []);
  const [subtotal, setSubtotal] = useState(billData.initial_confirmed?.subtotal || "0.00");
  const [tax, setTax] = useState(billData.initial_confirmed?.tax || "0.00");
  const [serviceCharge, setServiceCharge] = useState(billData.initial_confirmed?.service_charge || "0.00");
  const [discount, setDiscount] = useState(billData.initial_confirmed?.discount || "0.00");
  const [total, setTotal] = useState(billData.initial_confirmed?.total || "0.00");
  
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Match raw items confidence scores by index
  const rawItems = billData.raw_extraction?.items || [];
  const provenance = billData.provenance;

  const handleItemChange = (index, field, value) => {
    const updated = [...items];
    updated[index] = { ...updated[index], [field]: value };
    setItems(updated);
  };

  const handleAddItem = () => {
    const newItem = {
      id: `custom_item_${Date.now()}`,
      name: "New Item",
      quantity: 1,
      price: "0.00",
    };
    setItems([...items, newItem]);
  };

  const handleDeleteItem = (index) => {
    const updated = items.filter((_, i) => i !== index);
    setItems(updated);
  };

  const handleConfirm = async () => {
    setSaving(true);
    setError(null);
    try {
      const confirmedPayload = {
        items: items.map((itm) => ({
          id: itm.id,
          name: itm.name,
          quantity: parseInt(itm.quantity, 10) || 1,
          price: String(parseFloat(itm.price) || 0),
        })),
        subtotal: String(parseFloat(subtotal) || 0),
        tax: String(parseFloat(tax) || 0),
        service_charge: String(parseFloat(serviceCharge) || 0),
        discount: String(parseFloat(discount) || 0),
        total: String(parseFloat(total) || 0),
      };

      // 1. Save updated confirmed bill
      await updateConfirmedBill(billData.bill_id, confirmedPayload);
      // 2. Lock confirmed status
      const lockRes = await confirmBill(billData.bill_id);
      onConfirmComplete({ ...billData, confirmed_bill: confirmedPayload, status: lockRes.status });
    } catch (err) {
      setError(err.message || "Failed to confirm bill.");
    } finally {
      setSaving(false);
    }
  };

  const calculatedItemsSum = items
    .reduce((acc, itm) => acc + (parseFloat(itm.price) || 0), 0)
    .toFixed(2);

  const getConfidenceBadge = (confidence) => {
    if (confidence === undefined || confidence === null) return null;
    const pct = Math.round(confidence * 100);
    if (pct >= 90) {
      return <span className="badge badge-success">{pct}% match</span>;
    } else if (pct >= 70) {
      return <span className="badge badge-warning">{pct}% confidence</span>;
    } else {
      return (
        <span className="badge badge-danger">
          <AlertTriangle size={12} /> {pct}% (Verify)
        </span>
      );
    }
  };

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
        <div>
          <h2 className="card-title">
            <CheckCircle2 size={22} style={{ color: "var(--success)" }} />
            Human Review & Correction
          </h2>
          <p className="card-desc" style={{ marginBottom: "0.25rem" }}>
            Review AI extraction results. Edit any incorrect prices or quantities before confirming.
          </p>
        </div>

        {provenance && (
          <div className="badge badge-success" style={{ gap: "0.4rem", padding: "0.35rem 0.65rem" }}>
            <Cpu size={14} />
            <span>
              {provenance.provider} ({provenance.model}) • {Math.round(provenance.average_confidence * 100)}% avg conf
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="banner banner-danger">
          <ShieldAlert size={20} />
          <div>{error}</div>
        </div>
      )}

      {/* Items Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th style={{ width: "45%" }}>Item Name</th>
              <th style={{ width: "15%" }}>Qty</th>
              <th style={{ width: "20%" }}>Total Price (₹)</th>
              <th style={{ width: "15%" }}>AI Confidence</th>
              <th style={{ width: "5%" }}></th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => {
              const conf = rawItems[index]?.confidence;
              return (
                <tr key={item.id || index}>
                  <td>
                    <input
                      type="text"
                      className="input-text"
                      value={item.name}
                      onChange={(e) => handleItemChange(index, "name", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min="1"
                      className="input-number"
                      value={item.quantity}
                      onChange={(e) => handleItemChange(index, "quantity", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      className="input-number"
                      value={item.price}
                      onChange={(e) => handleItemChange(index, "price", e.target.value)}
                    />
                  </td>
                  <td>{getConfidenceBadge(conf)}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => handleDeleteItem(index)}
                      style={{ background: "transparent", border: "none", color: "var(--danger)", cursor: "pointer" }}
                      title="Delete item"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <button type="button" className="btn btn-secondary btn-sm" onClick={handleAddItem}>
          <Plus size={14} /> Add Missing Item
        </button>
        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          Sum of items: <strong style={{ color: "var(--text-main)" }}>₹{calculatedItemsSum}</strong>
        </span>
      </div>

      {/* Summary Charges Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "1rem", background: "#FAF7F2", padding: "1.25rem", borderRadius: "12px", border: "1px solid var(--surface-border)", marginBottom: "1.5rem" }}>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Subtotal (₹)</label>
          <input
            type="number"
            step="0.01"
            className="input-number"
            value={subtotal}
            onChange={(e) => setSubtotal(e.target.value)}
          />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Discount (₹)</label>
          <input
            type="number"
            step="0.01"
            className="input-number"
            value={discount}
            onChange={(e) => setDiscount(e.target.value)}
          />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Tax (GST) (₹)</label>
          <input
            type="number"
            step="0.01"
            className="input-number"
            value={tax}
            onChange={(e) => setTax(e.target.value)}
          />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label">Service Charge (₹)</label>
          <input
            type="number"
            step="0.01"
            className="input-number"
            value={serviceCharge}
            onChange={(e) => setServiceCharge(e.target.value)}
          />
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label className="form-label" style={{ color: "var(--primary-brand)" }}>Printed Bill Total (₹)</label>
          <input
            type="number"
            step="0.01"
            className="input-number"
            style={{ fontWeight: "bold", borderColor: "var(--primary-brand)" }}
            value={total}
            onChange={(e) => setTotal(e.target.value)}
          />
        </div>
      </div>

      <div className="action-bar">
        <button type="button" className="btn btn-secondary" onClick={onBack}>
          Upload Again
        </button>
        <button
          type="button"
          className="btn btn-success"
          onClick={handleConfirm}
          disabled={saving || items.length === 0}
        >
          {saving ? "Locking & Confirming..." : "Confirm & Lock Bill"}
        </button>
      </div>
    </div>
  );
}
