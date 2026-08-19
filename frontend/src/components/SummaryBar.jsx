function fmtDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function SummaryBar({ summary, route }) {
  return (
    <div className="bento">
      <div className="bx bx-hero">
        <b>{route.distanceMi.toLocaleString()} mi</b>
        <span>Total haul</span>
        <span className="bx-truck" aria-hidden="true">
          🚚
        </span>
        <div className="bx-road" />
      </div>
      <div className="bx bx-wheel">
        <b>{route.drivingHr} h</b>
        <span>Wheel time</span>
      </div>
      <div className="bx bx-door">
        <b>{summary.totalTripHr} h</b>
        <span>Door to door</span>
      </div>
      <div className="bx bx-pages">
        <b>{summary.days}</b>
        <span>Logbook page{summary.days === 1 ? "" : "s"}</span>
      </div>
      <div className="bx bx-rests">
        <b>
          {summary.restStops} + {summary.fuelStops}
        </b>
        <span>Rests + diesel</span>
      </div>
      <div className="bx bx-sched">
        <div className="sched-row">
          <b>{fmtDate(summary.startTime)}</b>
        </div>
        <div className="sched-row sched-mid">
          <span className="sched-arrow">⬇</span>
          <span>{summary.totalTripHr} h on the road</span>
        </div>
        <div className="sched-row">
          <b>{fmtDate(summary.endTime)}</b>
        </div>
      </div>
    </div>
  );
}
