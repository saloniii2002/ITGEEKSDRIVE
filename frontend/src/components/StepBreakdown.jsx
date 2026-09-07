import React, { useState, useEffect } from "react";
import { CheckCircle2, AlertTriangle, Share2, Copy, Check, MessageSquare, RotateCcw } from "lucide-react";
import { getWhatsAppShare } from "../api";

export default function StepBreakdown({ result, billData, onReset }) {
  const [waData, setWaData] = useState(null);
  const [copiedText, setCopiedText] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    if (result?.bill_id) {
      getWhatsAppShare(result.bill_id)
        .then((data) => setWaData(data))
        .catch((err) => console.error("Could not fetch WhatsApp share link", err));
    }
  }, [result?.bill_id]);

  const handleCopyMessage = () => {
    if (waData?.message_text) {
      navigator.clipboard.writeText(waData.message_text);
      setCopiedText(true);
      setTimeout(() => setCopiedText(false), 2000);
    }
  };

  const handleCopyShareLink = () => {
    const shareUrl = `${window.location.origin}/share/${billData.share_token}`;
    navigator.clipboard.writeText(shareUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  if (!result) return null;

  return (
    <div>
      {/* Validation Banner: Perfect Match vs Mismatch */}
      {!result.mismatch ? (
        <div className="banner banner-success">
          <CheckCircle2 size={24} style={{ color: "#34d399", flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: "1rem" }}>
              Total Validated: Exact Match (Zero Drift)
            </div>
            <div style={{ fontSize: "0.875rem", color: "#a7f3d0" }}>
              The sum of all individual shares equals ₹{result.calculated_total}, perfectly matching the printed bill total of ₹{result.printed_total}.
            </div>
          </div>
        </div>
      ) : (
        <div className="banner banner-warning">
          <AlertTriangle size={24} style={{ color: "#f59e0b", flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: "1rem" }}>
              ⚠️ Bill Total Mismatch Detected!
            </div>
            <div style={{ fontSize: "0.875rem" }}>
              Calculated total is <strong>₹{result.calculated_total}</strong>, while the printed bill shows <strong>₹{result.printed_total}</strong> (Difference: <strong>₹{result.difference > 0 ? `+${result.difference}` : result.difference}</strong>).
              This discrepancy is surfaced explicitly and not silently smoothed away.
            </div>
          </div>
        </div>
      )}

      {/* Unassigned items notice if applicable */}
      {result.unassigned_items && result.unassigned_items.length > 0 && (
        <div className="banner banner-warning">
          <AlertTriangle size={20} style={{ color: "#f59e0b" }} />
          <div>
            <strong>Notice:</strong> {result.unassigned_items.length} unassigned item(s) totaling ₹{result.unassigned_items.reduce((a, b) => a + parseFloat(b.price), 0).toFixed(2)} were excluded from the split:{" "}
            {result.unassigned_items.map((i) => `${i.name} (₹${i.price})`).join(", ")}
          </div>
        </div>
      )}

      {/* Bill Overview Summary */}
      <div className="card" style={{ padding: "1.25rem 1.5rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "1rem", textAlign: "center" }}>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Assigned Food</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>₹{result.assigned_food_total}</div>
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Discount</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#34d399" }}>-₹{result.discount}</div>
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Tax (GST)</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>₹{result.tax}</div>
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Service Charge</div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>₹{result.service_charge}</div>
          </div>
          <div style={{ borderLeft: "1px solid var(--surface-border)", paddingLeft: "1rem" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Grand Total</div>
            <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#60a5fa", fontFamily: "var(--font-mono)" }}>
              ₹{result.calculated_total}
            </div>
          </div>
        </div>
      </div>

      {/* Per-Person Breakdown Grid */}
      <div className="breakdown-grid">
        {result.persons.map((person) => (
          <div key={person.person_id} className="person-card">
            <div>
              <div className="person-header">
                <span className="person-name">{person.name}</span>
                <span className="person-total">₹{person.total}</span>
              </div>

              {/* Items consumed */}
              <ul className="item-list">
                {person.items.map((itm, idx) => (
                  <li key={idx} className="item-row">
                    <span>
                      {itm.item_name}
                      {itm.split_among_count > 1 && (
                        <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginLeft: "0.3rem" }}>
                          (1/{itm.split_among_count})
                        </span>
                      )}
                    </span>
                    <span style={{ fontFamily: "var(--font-mono)" }}>₹{itm.share_amount}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Subtotals and proportional extras */}
            <div className="charges-subtotal">
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.2rem" }}>
                <span>Food subtotal:</span>
                <span>₹{person.food_subtotal}</span>
              </div>
              {parseFloat(person.discount_share) > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between", color: "#34d399", marginBottom: "0.2rem" }}>
                  <span>Discount share:</span>
                  <span>-₹{person.discount_share}</span>
                </div>
              )}
              {parseFloat(person.tax_share) > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.2rem" }}>
                  <span>Proportional Tax:</span>
                  <span>₹{person.tax_share}</span>
                </div>
              )}
              {parseFloat(person.service_charge_share) > 0 && (
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.2rem" }}>
                  <span>Proportional Service:</span>
                  <span>₹{person.service_charge_share}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Sharing & Actions Card */}
      <div className="card" style={{ marginTop: "1rem" }}>
        <h3 className="card-title" style={{ fontSize: "1.1rem" }}>
          <Share2 size={18} style={{ color: "#34d399" }} />
          Share Bill Split
        </h3>
        <p className="card-desc" style={{ marginBottom: "1rem" }}>
          Send the itemized breakdown directly to friends via WhatsApp or share a read-only web link.
        </p>

        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "center" }}>
          {waData?.whatsapp_url && (
            <a
              href={waData.whatsapp_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-success"
            >
              <MessageSquare size={16} /> Open in WhatsApp
            </a>
          )}

          <button type="button" className="btn btn-secondary" onClick={handleCopyMessage}>
            {copiedText ? <Check size={16} style={{ color: "#34d399" }} /> : <Copy size={16} />}
            {copiedText ? "Message Copied!" : "Copy WhatsApp Text"}
          </button>

          <button type="button" className="btn btn-secondary" onClick={handleCopyShareLink}>
            {copiedLink ? <Check size={16} style={{ color: "#34d399" }} /> : <Copy size={16} />}
            {copiedLink ? "Link Copied!" : "Copy Read-Only Link"}
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            style={{ marginLeft: "auto" }}
            onClick={onReset}
          >
            <RotateCcw size={16} /> Split Another Bill
          </button>
        </div>
      </div>
    </div>
  );
}
