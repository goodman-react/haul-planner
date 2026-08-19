const ROWS = [
  { key: "offDuty", label: "1. Off Duty" },
  { key: "sleeper", label: "2. Sleeper Berth" },
  { key: "driving", label: "3. Driving" },
  { key: "onDuty", label: "4. On Duty (not driving)" },
];

const GRID_X = 150;
const HOUR_W = 30;
const GRID_W = 24 * HOUR_W;
const ROW_H = 44;
const GRID_Y = 96;
const GRID_H = ROWS.length * ROW_H;
const TOTALS_X = GRID_X + GRID_W + 12;
const SVG_W = TOTALS_X + 70;

function hourLabel(h) {
  if (h === 0 || h === 24) return "Mid";
  if (h === 12) return "Noon";
  return String(h > 12 ? h - 12 : h);
}

function rowY(statusKey) {
  const idx = ROWS.findIndex((r) => r.key === statusKey);
  return GRID_Y + idx * ROW_H + ROW_H / 2;
}

function fmtClock(hourFloat) {
  const h = Math.floor(hourFloat);
  const m = Math.round((hourFloat - h) * 60);
  const ampm = h < 12 ? "AM" : "PM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${ampm}`;
}

export default function LogSheet({ log, index, locations }) {
  const date = new Date(`${log.date}T00:00:00`);
  const [month, day, year] = [
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
    date.getFullYear(),
  ];

  // Duty-status step line.
  const path = log.entries
    .map((e, i) => {
      const x1 = GRID_X + e.startHour * HOUR_W;
      const x2 = GRID_X + e.endHour * HOUR_W;
      const y = rowY(e.status);
      return `${i === 0 ? `M ${x1} ${y}` : `L ${x1} ${y}`} L ${x2} ${y}`;
    })
    .join(" ");

  const remarks = log.entries.filter(
    (e) => !e.label.startsWith("Off duty (") && e.label !== "Drive to pickup" &&
      e.label !== "Drive to drop-off"
  );

  const svgH = GRID_Y + GRID_H + 40;

  return (
    <article className="log-sheet">
      <div className="log-sheet-head">
        <div>
          <div className="log-sheet-title">Driver&apos;s Daily Log</div>
          <div className="log-sheet-sub">(24 hours) — Page {index + 1}</div>
        </div>
        <div className="log-head-fields">
          <div className="head-field">
            <span className="head-value">
              {month} / {day} / {year}
            </span>
            <span className="head-label">(month / day / year)</span>
          </div>
          <div className="head-field">
            <span className="head-value">{log.milesToday.toLocaleString()}</span>
            <span className="head-label">Total miles driving today</span>
          </div>
        </div>
      </div>

      <div className="log-route-row">
        <div className="head-field wide">
          <span className="head-value">{locations.pickup.name.split(",").slice(0, 2).join(",")}</span>
          <span className="head-label">From</span>
        </div>
        <div className="head-field wide">
          <span className="head-value">{locations.dropoff.name.split(",").slice(0, 2).join(",")}</span>
          <span className="head-label">To</span>
        </div>
      </div>

      <div className="log-grid-scroll">
        <svg
          viewBox={`0 0 ${SVG_W} ${svgH}`}
          width={SVG_W}
          className="log-grid-svg"
          role="img"
          aria-label={`Daily log grid for ${log.date}`}
        >
          {/* Hour labels */}
          {Array.from({ length: 25 }, (_, h) => (
            <text
              key={`hl-${h}`}
              x={GRID_X + h * HOUR_W}
              y={GRID_Y - 8}
              textAnchor="middle"
              className="svg-hour-label"
            >
              {hourLabel(h)}
            </text>
          ))}
          <text x={TOTALS_X + 28} y={GRID_Y - 8} textAnchor="middle" className="svg-hour-label">
            Total
          </text>

          {/* Row backgrounds + labels + totals */}
          {ROWS.map((row, i) => {
            const y = GRID_Y + i * ROW_H;
            return (
              <g key={row.key}>
                <rect
                  x={GRID_X}
                  y={y}
                  width={GRID_W}
                  height={ROW_H}
                  className={i % 2 ? "svg-row-alt" : "svg-row"}
                />
                <text x={8} y={y + ROW_H / 2 + 4} className="svg-row-label">
                  {row.label}
                </text>
                <rect
                  x={TOTALS_X}
                  y={y}
                  width={56}
                  height={ROW_H}
                  className="svg-total-box"
                />
                <text
                  x={TOTALS_X + 28}
                  y={y + ROW_H / 2 + 4}
                  textAnchor="middle"
                  className="svg-total-value"
                >
                  {log.totals[row.key].toFixed(2)}
                </text>
              </g>
            );
          })}

          {/* Vertical hour + quarter-hour ticks */}
          {Array.from({ length: 25 }, (_, h) => (
            <g key={`v-${h}`}>
              <line
                x1={GRID_X + h * HOUR_W}
                y1={GRID_Y}
                x2={GRID_X + h * HOUR_W}
                y2={GRID_Y + GRID_H}
                className="svg-hour-line"
              />
              {h < 24 &&
                [1, 2, 3].map((q) => (
                  <g key={q}>
                    {ROWS.map((_, ri) => (
                      <line
                        key={ri}
                        x1={GRID_X + h * HOUR_W + (q * HOUR_W) / 4}
                        y1={GRID_Y + ri * ROW_H}
                        x2={GRID_X + h * HOUR_W + (q * HOUR_W) / 4}
                        y2={GRID_Y + ri * ROW_H + (q === 2 ? 14 : 8)}
                        className="svg-tick"
                      />
                    ))}
                  </g>
                ))}
            </g>
          ))}

          {/* Horizontal row borders */}
          {Array.from({ length: ROWS.length + 1 }, (_, i) => (
            <line
              key={`h-${i}`}
              x1={GRID_X}
              y1={GRID_Y + i * ROW_H}
              x2={GRID_X + GRID_W}
              y2={GRID_Y + i * ROW_H}
              className="svg-row-line"
            />
          ))}

          {/* Duty-status step line */}
          <path d={path} className="svg-duty-line" fill="none" />

          {/* Total-hours check */}
          <text
            x={TOTALS_X + 28}
            y={GRID_Y + GRID_H + 24}
            textAnchor="middle"
            className="svg-total-sum"
          >
            = {(
              log.totals.offDuty +
              log.totals.sleeper +
              log.totals.driving +
              log.totals.onDuty
            ).toFixed(2)}
          </text>
        </svg>
      </div>

      {remarks.length > 0 && (
        <div className="log-remarks">
          <div className="remarks-title">Remarks</div>
          <ul>
            {remarks.map((e, i) => (
              <li key={i}>
                <b>{fmtClock(e.startHour)}</b> — {e.label}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
