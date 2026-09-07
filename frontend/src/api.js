const API_BASE = "http://localhost:8000";

export async function uploadBill(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  const res = await fetch(`${API_BASE}/bills/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function getBill(billId) {
  const res = await fetch(`${API_BASE}/bills/${billId}`);
  if (!res.ok) throw new Error("Failed to fetch bill");
  return res.json();
}

export async function updateConfirmedBill(billId, confirmedBill) {
  const res = await fetch(`${API_BASE}/bills/${billId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(confirmedBill),
  });
  if (!res.ok) throw new Error("Failed to update bill corrections");
  return res.json();
}

export async function confirmBill(billId) {
  const res = await fetch(`${API_BASE}/bills/${billId}/confirm`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to confirm bill");
  return res.json();
}

export async function addPeople(billId, peopleList) {
  const res = await fetch(`${API_BASE}/bills/${billId}/people`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(peopleList),
  });
  if (!res.ok) throw new Error("Failed to add people");
  return res.json();
}

export async function getPeople(billId) {
  const res = await fetch(`${API_BASE}/bills/${billId}/people`);
  if (!res.ok) throw new Error("Failed to fetch people");
  return res.json();
}

export async function saveAssignments(billId, assignmentsMap) {
  const res = await fetch(`${API_BASE}/bills/${billId}/assignments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ assignments: assignmentsMap }),
  });
  if (!res.ok) throw new Error("Failed to save assignments");
  return res.json();
}

export async function getAssignments(billId) {
  const res = await fetch(`${API_BASE}/bills/${billId}/assignments`);
  if (!res.ok) throw new Error("Failed to fetch assignments");
  return res.json();
}

export async function calculateSplit(billId, acknowledgeUnassigned = false) {
  const res = await fetch(`${API_BASE}/bills/${billId}/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ acknowledge_unassigned: acknowledgeUnassigned }),
  });

  if (res.status === 409) {
    const errorBody = await res.json();
    const conflictError = new Error("Unassigned items detected");
    conflictError.status = 409;
    conflictError.data = errorBody.detail;
    throw conflictError;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Calculation failed");
  }

  return res.json();
}

export async function getBreakdown(billId) {
  const res = await fetch(`${API_BASE}/bills/${billId}/breakdown`);
  if (!res.ok) throw new Error("Failed to fetch breakdown");
  return res.json();
}

export async function getWhatsAppShare(billId, restaurantName = "") {
  const url = new URL(`${API_BASE}/bills/${billId}/share/whatsapp`);
  if (restaurantName) url.searchParams.set("restaurant_name", restaurantName);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to generate WhatsApp share link");
  return res.json();
}

export async function getShareableBreakdown(token) {
  const res = await fetch(`${API_BASE}/share/${token}`);
  if (!res.ok) throw new Error("Shared breakdown not found");
  return res.json();
}
