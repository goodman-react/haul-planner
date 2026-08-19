import { useState } from "react";

const FIELDS = [
  {
    name: "currentLocation",
    label: "You're at",
    placeholder: "e.g. Chicago, IL",
    icon: "📍",
  },
  {
    name: "pickupLocation",
    label: "Grab the load",
    placeholder: "e.g. Indianapolis, IN",
    icon: "📦",
  },
  {
    name: "dropoffLocation",
    label: "Haul it to",
    placeholder: "e.g. Dallas, TX",
    icon: "🏁",
  },
];

export default function TripForm({ onSubmit, loading }) {
  const [values, setValues] = useState({
    currentLocation: "",
    pickupLocation: "",
    dropoffLocation: "",
    cycleUsedHours: "0",
  });

  function update(name, value) {
    setValues((v) => ({ ...v, [name]: value }));
  }

  function submit(e) {
    e.preventDefault();
    onSubmit({ ...values, cycleUsedHours: Number(values.cycleUsedHours || 0) });
  }

  return (
    <form className="panel trip-form" onSubmit={submit}>
      <div className="form-grid">
        {FIELDS.map((f) => (
          <label key={f.name} className="field">
            <span className="field-label">
              {f.icon} {f.label}
            </span>
            <input
              type="text"
              required
              placeholder={f.placeholder}
              value={values[f.name]}
              onChange={(e) => update(f.name, e.target.value)}
            />
          </label>
        ))}
        <label className="field">
          <span className="field-label">⏱ Cycle burned (hrs)</span>
          <input
            type="number"
            min="0"
            max="70"
            step="0.5"
            required
            value={values.cycleUsedHours}
            onChange={(e) => update("cycleUsedHours", e.target.value)}
          />
        </label>
      </div>
      <button className="submit-btn" type="submit" disabled={loading}>
        {loading ? "Rolling…" : "Roll Out!"}
      </button>
    </form>
  );
}
