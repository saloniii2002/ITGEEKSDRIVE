import React, { useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { addPeople } from "../api";
import TableBlock from "@/components/ui/team-members-data-table";

export default function StepPeople({ billData, onPeopleComplete, onBack }) {
  const [members, setMembers] = useState([
    {
      id: "m-01",
      name: "Alice Smith",
      initials: "AS",
      avatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80",
      email: "alice@example.com",
      status: "Active",
      role: "Admin",
      joined: "2026-06-12",
    },
    {
      id: "m-02",
      name: "Bob Johnson",
      initials: "BJ",
      avatar: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
      email: "bob@example.com",
      status: "Active",
      role: "Editor",
      joined: "2026-06-10",
    },
    {
      id: "m-03",
      name: "Charlie Brown",
      initials: "CB",
      avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
      email: "charlie@example.com",
      status: "Active",
      role: "Viewer",
      joined: "2026-06-08",
    },
  ]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSave = async (dinerList = members) => {
    const list = Array.isArray(dinerList) ? dinerList : members;
    const validPeople = list
      .filter((p) => p.name && p.name.trim().length > 0)
      .map((p) => ({
        name: p.name.trim(),
        email: p.email || "",
        phone: "",
      }));

    if (validPeople.length === 0) {
      setError("Please add at least one person to split the bill.");
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
    <div className="flex flex-col gap-4">
      {error && (
        <div className="banner banner-danger">
          <div>{error}</div>
        </div>
      )}

      <TableBlock
        membersData={members}
        onMembersChange={(updated) => setMembers(updated)}
        onProceed={(selected) => handleSave(selected)}
      />

      <div className="flex items-center justify-between pt-2">
        <button
          type="button"
          className="btn btn-secondary inline-flex items-center gap-2"
          onClick={onBack}
        >
          <ArrowLeft size={16} /> Back to Review
        </button>
        <button
          type="button"
          className="btn btn-primary inline-flex items-center gap-2"
          onClick={() => handleSave(members)}
          disabled={saving || members.length === 0}
        >
          {saving ? "Saving Diners..." : "Proceed to Assign Items"} <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
