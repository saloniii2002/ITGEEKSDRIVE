import React, { useState } from "react";
import { CheckSquare, AlertTriangle, Calculator, Sparkles } from "lucide-react";
import { saveAssignments, calculateSplit } from "../api";

export default function StepAssign({ billData, people, onCalculateComplete, onBack }) {
  // Items from confirmed bill
  const items = billData.confirmed_bill?.items || [];

  // Map: stable item_id -> array of person_ids
  const [assignments, setAssignments] = useState(() => {
    const initial = {};
    items.forEach((item) => {
      initial[item.id] = [];
    });
    return initial;
  });

  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState(null);
  const [unassignedPrompt, setUnassignedPrompt] = useState(null);

  const togglePerson = (itemId, personId) => {
    setAssignments((prev) => {
      const current = prev[itemId] || [];
      const updated = current.includes(personId)
        ? current.filter((id) => id !== personId)
        : [...current, personId];
      return { ...prev, [itemId]: updated };
    });
    setUnassignedPrompt(null);
  };

  const assignAllToItem = (itemId) => {
    setAssignments((prev) => ({
      ...prev,
      [itemId]: people.map((p) => p.id),
    }));
    setUnassignedPrompt(null);
  };

  const clearItem = (itemId) => {
    setAssignments((prev) => ({
      ...prev,
      [itemId]: [],
    }));
  };

  const splitAllEvenly = () => {
    const allPersonIds = people.map((p) => p.id);
    const updated = {};
    items.forEach((item) => {
      updated[item.id] = [...allPersonIds];
    });
    setAssignments(updated);
    setUnassignedPrompt(null);
  };

  const handleCalculate = async (acknowledgeUnassigned = false) => {
    setCalculating(true);
    setError(null);
    setUnassignedPrompt(null);

    try {
      // 1. Save assignments first
      await saveAssignments(billData.bill_id, assignments);

      // 2. Execute calculation
      const result = await calculateSplit(billData.bill_id, acknowledgeUnassigned);
      onCalculateComplete(result);
    } catch (err) {
      if (err.status === 409 && err.data) {
        // Unassigned items blocking triggered
        setUnassignedPrompt(err.data);
      } else {
        setError(err.message || "Failed to calculate split.");
      }
    } finally {
      setCalculating(false);
    }
  };

  const unassignedCount = items.filter(
    (itm) => !assignments[itm.id] || assignments[itm.id].length === 0
  ).length;

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
        <div>
          <h2 className="card-title">
            <CheckSquare size={22} style={{ color: "var(--primary-brand)" }} />
            Assign Items to Consumers
          </h2>
          <p className="card-desc" style={{ marginBottom: "0.25rem" }}>
            Select who ate or drank each item. Shared items will be split equally among selected consumers.
          </p>
        </div>

        <button type="button" className="btn btn-secondary btn-sm" onClick={splitAllEvenly}>
          <Sparkles size={14} /> Split All Items Evenly
        </button>
      </div>

      {error && (
        <div className="banner banner-danger">
          <AlertTriangle size={20} />
          <div>{error}</div>
        </div>
      )}

      {unassignedPrompt && (
        <div className="banner banner-warning" style={{ flexDirection: "column", gap: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700 }}>
            <AlertTriangle size={20} style={{ color: "var(--warning)" }} />
            Calculation Blocked: Unassigned Items Detected!
          </div>
          <p style={{ fontSize: "0.875rem" }}>
            {unassignedPrompt.message}
          </p>
          <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
            <button
              type="button"
              className="btn btn-warning btn-sm"
              onClick={() => handleCalculate(true)}
              disabled={calculating}
            >
              Proceed Anyway (Exclude Unassigned)
            </button>
          </div>
        </div>
      )}

      {/* Items Assignment List */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginBottom: "1.5rem" }}>
        {items.map((item) => {
          const selectedPeople = assignments[item.id] || [];
          const isUnassigned = selectedPeople.length === 0;

          return (
            <div
              key={item.id}
              style={{
                background: "#FAF7F2",
                border: isUnassigned ? "1px solid var(--danger-border)" : "1px solid var(--surface-border)",
                borderRadius: "12px",
                padding: "1rem 1.25rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <div>
                  <span style={{ fontWeight: 700, fontSize: "1rem" }}>{item.name}</span>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginLeft: "0.5rem" }}>
                    (Qty: {item.quantity})
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <span style={{ fontWeight: 800, fontFamily: "var(--font-mono)", fontSize: "1.05rem" }}>
                    ₹{parseFloat(item.price).toFixed(2)}
                  </span>
                  {isUnassigned && (
                    <span className="badge badge-danger">
                      ⚠️ Unassigned
                    </span>
                  )}
                </div>
              </div>

              {/* Checkboxes for each person */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "center" }}>
                {people.map((person) => {
                  const isChecked = selectedPeople.includes(person.id);
                  return (
                    <label
                      key={person.id}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.4rem",
                        background: isChecked ? "var(--primary-light)" : "#FFFFFF",
                        border: isChecked ? "1px solid var(--primary-brand)" : "1px solid var(--surface-border)",
                        color: isChecked ? "var(--primary-brand)" : "var(--text-main)",
                        padding: "0.4rem 0.75rem",
                        borderRadius: "8px",
                        cursor: "pointer",
                        fontSize: "0.875rem",
                        fontWeight: isChecked ? 600 : 400,
                        transition: "all 0.15s ease",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => togglePerson(item.id, person.id)}
                        style={{ cursor: "pointer", accentColor: "var(--primary-brand)" }}
                      />
                      {person.name}
                    </label>
                  );
                })}

                <div style={{ marginLeft: "auto", display: "flex", gap: "0.4rem" }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                    onClick={() => assignAllToItem(item.id)}
                  >
                    All
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                    onClick={() => clearItem(item.id)}
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          {unassignedCount > 0 ? (
            <span style={{ color: "#f87171" }}>⚠️ {unassignedCount} item(s) unassigned</span>
          ) : (
            <span style={{ color: "#34d399" }}>✅ All {items.length} items assigned</span>
          )}
        </span>
      </div>

      <div className="action-bar">
        <button type="button" className="btn btn-secondary" onClick={onBack}>
          Back to People
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => handleCalculate(false)}
          disabled={calculating}
        >
          <Calculator size={16} />
          {calculating ? "Calculating Deterministic Split..." : "Calculate Split Breakdown"}
        </button>
      </div>
    </div>
  );
}
