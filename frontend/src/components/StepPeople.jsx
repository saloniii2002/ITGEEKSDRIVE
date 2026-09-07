import React, { useState } from "react";
import { Users, UserPlus, Trash2, ArrowRight, Sparkles } from "lucide-react";
import { addPeople } from "../api";

export default function StepPeople({ billData, onPeopleComplete, onBack }) {
  const [people, setPeople] = useState([
    { name: "Alice", email: "", phone: "" },
    { name: "Bob", email: "", phone: "" },
    { name: "Charlie", email: "", phone: "" },
  ]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handlePersonChange = (index, field, value) => {
    const updated = [...people];
    updated[index] = { ...updated[index], [field]: value };
    setPeople(updated);
  };

  const handleAddPerson = () => {
    setPeople([...people, { name: "", email: "", phone: "" }]);
  };

  const handleRemovePerson = (index) => {
    if (people.length <= 1) {
      setError("Must have at least one person.");
      return;
    }
    const updated = people.filter((_, i) => i !== index);
    setPeople(updated);
    setError(null);
  };

  const handleSave = async () => {
    const validPeople = people.filter((p) => p.name.trim().length > 0);
    if (validPeople.length === 0) {
      setError("Please provide a name for at least one person.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const savedPeople = await addPeople(billData.bill_id, validPeople);
      onPeopleComplete(savedPeople);
    } catch (err) {
      setError(err.message || "Failed to save people.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <h2 className="card-title">
        <Users size={22} style={{ color: "#60a5fa" }} />
        Add People (2–3+ Consumers)
      </h2>
      <p className="card-desc">
        Enter the names of the people sharing this meal. You will assign bill items to them in the next step.
      </p>

      {error && (
        <div className="banner banner-danger" style={{ marginBottom: "1rem" }}>
          <div>{error}</div>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1.5rem" }}>
        {people.map((person, index) => (
          <div
            key={index}
            style={{
              display: "grid",
              gridTemplateColumns: "1.5fr 1.5fr 1fr auto",
              gap: "0.75rem",
              alignItems: "center",
              background: "#0d1322",
              padding: "0.75rem 1rem",
              borderRadius: "8px",
              border: "1px solid var(--surface-border)",
            }}
          >
            <div>
              <label className="form-label" style={{ fontSize: "0.75rem" }}>Name *</label>
              <input
                type="text"
                placeholder="e.g. Alice"
                className="input-text"
                value={person.name}
                onChange={(e) => handlePersonChange(index, "name", e.target.value)}
              />
            </div>
            <div>
              <label className="form-label" style={{ fontSize: "0.75rem" }}>Email (Optional)</label>
              <input
                type="email"
                placeholder="alice@example.com"
                className="input-text"
                value={person.email}
                onChange={(e) => handlePersonChange(index, "email", e.target.value)}
              />
            </div>
            <div>
              <label className="form-label" style={{ fontSize: "0.75rem" }}>Phone (Optional)</label>
              <input
                type="tel"
                placeholder="+91..."
                className="input-text"
                value={person.phone}
                onChange={(e) => handlePersonChange(index, "phone", e.target.value)}
              />
            </div>
            <button
              type="button"
              onClick={() => handleRemovePerson(index)}
              style={{ background: "transparent", border: "none", color: "#f87171", cursor: "pointer", marginTop: "1rem" }}
              title="Remove Person"
            >
              <Trash2 size={18} />
            </button>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem" }}>
        <button type="button" className="btn btn-secondary btn-sm" onClick={handleAddPerson}>
          <UserPlus size={14} /> Add Another Person
        </button>
      </div>

      <div className="action-bar">
        <button type="button" className="btn btn-secondary" onClick={onBack}>
          Back to Review
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving || people.filter((p) => p.name.trim()).length === 0}
        >
          {saving ? "Saving People..." : "Continue to Assign Items"} <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
