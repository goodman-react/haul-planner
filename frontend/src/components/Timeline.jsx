const STATUS_META = {
  offDuty: { label: "Off Duty", color: "#4f6f52" },
  sleeper: { label: "Sleeper Berth", color: "#8c5a2b" },
  driving: { label: "Driving", color: "#d94f2b" },
  onDuty: { label: "On Duty", color: "#b97a1e" },
};

function fmt(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function Timeline({ segments }) {
  return (
    <ol className="timeline">
      {segments.map((seg, i) => {
        const meta = STATUS_META[seg.status];
        return (
          <li key={i} className="timeline-item">
            <span className="timeline-dot" style={{ background: meta.color }} />
            <div className="timeline-body">
              <div className="timeline-title">
                {seg.label}
                <span className="status-chip" style={{ color: meta.color }}>
                  {meta.label}
                </span>
              </div>
              <div className="timeline-sub">
                {fmt(seg.start)} → {fmt(seg.end)} · {seg.hours.toFixed(2)} h
                {seg.miles > 0 && ` · ${seg.miles.toFixed(0)} mi`}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
