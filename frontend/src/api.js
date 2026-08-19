const API_BASE = import.meta.env.VITE_API_URL || "";

export async function planTrip(payload) {
  const resp = await fetch(`${API_BASE}/api/trips/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const message =
      data.detail ||
      (data.errors && Object.values(data.errors).join(" ")) ||
      "Something went wrong while planning the trip.";
    throw new Error(message);
  }
  return data;
}
