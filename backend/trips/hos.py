"""FMCSA Hours-of-Service trip simulator.

Property-carrying driver, 70 hr / 8 day cycle, no adverse-driving exception.

Rules implemented (49 CFR 395.3):
  - 11-hour driving limit per shift.
  - 14-hour driving window from the start of the shift (breaks do not pause it;
    driving is forbidden past the 14th hour, other on-duty work is allowed).
  - 30-minute break from driving after 8 cumulative hours of driving.
    Any consecutive non-driving period of >= 30 min (fuel stop, pickup, drop-off)
    satisfies it.
  - 10 consecutive hours off duty reset the 11-hour and 14-hour clocks
    (logged as sleeper berth).
  - 70-hour on-duty limit over the rolling cycle; when exhausted, a 34-hour
    restart resets it to zero.

Assessment assumptions:
  - Fuel stop (30 min, on duty) at least every 1,000 miles.
  - 1 hour on duty for pickup and 1 hour for drop-off.
"""

from datetime import datetime, timedelta

# Duty statuses (match the four rows of the paper log grid).
OFF_DUTY = "offDuty"
SLEEPER = "sleeper"
DRIVING = "driving"
ON_DUTY = "onDuty"

MAX_DRIVE_PER_SHIFT = 11.0
DRIVING_WINDOW = 14.0
DRIVE_BEFORE_BREAK = 8.0
BREAK_HOURS = 0.5
DAILY_REST_HOURS = 10.0
CYCLE_MAX_HOURS = 70.0
RESTART_HOURS = 34.0
FUEL_INTERVAL_MILES = 1000.0
FUEL_STOP_HOURS = 0.5
PICKUP_HOURS = 1.0
DROPOFF_HOURS = 1.0

EPS = 1e-9


class Segment:
    """One contiguous duty-status period on the timeline."""

    def __init__(self, status, start, end, label, odometer_mi, miles=0.0):
        self.status = status
        self.start = start
        self.end = end
        self.label = label
        self.odometer_mi = odometer_mi  # odometer at the START of the segment
        self.miles = miles              # miles driven during the segment

    @property
    def hours(self):
        return (self.end - self.start).total_seconds() / 3600.0

    def as_dict(self):
        return {
            "status": self.status,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "label": self.label,
            "odometerMi": round(self.odometer_mi, 1),
            "miles": round(self.miles, 1),
            "hours": round(self.hours, 4),
        }


class TripSimulator:
    def __init__(self, cycle_used_hours, start_time):
        self.t = start_time
        self.cycle_used = float(cycle_used_hours)
        self.drive_in_shift = 0.0
        self.drive_since_break = 0.0
        self.window_start = None  # set when the first on-duty work of a shift begins
        self.miles_since_fuel = 0.0
        self.odometer = 0.0
        self.segments = []

    # ------------------------------------------------------------------ helpers

    def _window_elapsed(self):
        if self.window_start is None:
            return 0.0
        return (self.t - self.window_start).total_seconds() / 3600.0

    def _add(self, status, hours, label, miles=0.0):
        seg = Segment(
            status,
            self.t,
            self.t + timedelta(hours=hours),
            label,
            self.odometer,
            miles,
        )
        self.segments.append(seg)
        self.t = seg.end
        self.odometer += miles

    # ------------------------------------------------------------------ events

    def take_break(self):
        self._add(OFF_DUTY, BREAK_HOURS, "30-min rest break")
        self.drive_since_break = 0.0

    def take_daily_rest(self):
        self._add(SLEEPER, DAILY_REST_HOURS, "10-hr rest (sleeper berth)")
        self.drive_in_shift = 0.0
        self.drive_since_break = 0.0
        self.window_start = None

    def take_restart(self):
        self._add(OFF_DUTY, RESTART_HOURS, "34-hr cycle restart")
        self.cycle_used = 0.0
        self.drive_in_shift = 0.0
        self.drive_since_break = 0.0
        self.window_start = None

    def do_task(self, hours, label):
        """On-duty, not-driving work (pickup, drop-off, fueling)."""
        if self.cycle_used + hours > CYCLE_MAX_HOURS + EPS:
            self.take_restart()
        if self.window_start is None:
            self.window_start = self.t
        self._add(ON_DUTY, hours, label)
        self.cycle_used += hours
        if hours >= BREAK_HOURS - EPS:
            # A consecutive non-driving period of 30+ minutes satisfies the
            # 30-minute break requirement.
            self.drive_since_break = 0.0

    def fuel_stop(self):
        self.do_task(FUEL_STOP_HOURS, "Fuel stop")
        self.miles_since_fuel = 0.0

    # ------------------------------------------------------------------ driving

    def drive(self, miles, hours, label):
        """Drive a leg, inserting breaks/rests/restarts/fuel stops as required."""
        if hours <= EPS or miles <= EPS:
            return
        speed = miles / hours
        remaining = hours

        while remaining > EPS:
            # Resolve any constraint that forbids driving right now.
            if self.cycle_used >= CYCLE_MAX_HOURS - EPS:
                self.take_restart()
                continue
            if (
                self.drive_in_shift >= MAX_DRIVE_PER_SHIFT - EPS
                or (self.window_start is not None and self._window_elapsed() >= DRIVING_WINDOW - EPS)
            ):
                self.take_daily_rest()
                continue
            if self.drive_since_break >= DRIVE_BEFORE_BREAK - EPS:
                self.take_break()
                continue
            if self.miles_since_fuel >= FUEL_INTERVAL_MILES - EPS:
                self.fuel_stop()
                continue

            if self.window_start is None:
                self.window_start = self.t

            chunk = min(
                remaining,
                MAX_DRIVE_PER_SHIFT - self.drive_in_shift,
                DRIVING_WINDOW - self._window_elapsed(),
                DRIVE_BEFORE_BREAK - self.drive_since_break,
                CYCLE_MAX_HOURS - self.cycle_used,
                (FUEL_INTERVAL_MILES - self.miles_since_fuel) / speed,
            )
            chunk = max(chunk, 0.0)
            if chunk <= EPS:
                continue  # a limit was hit exactly; loop back to resolve it

            chunk_miles = chunk * speed
            self._add(DRIVING, chunk, label, miles=chunk_miles)
            self.drive_in_shift += chunk
            self.drive_since_break += chunk
            self.cycle_used += chunk
            self.miles_since_fuel += chunk_miles
            remaining -= chunk


def simulate_trip(legs, cycle_used_hours, start_time):
    """Simulate the full trip.

    legs: [{"miles": float, "hours": float, "label": str}] — drive to pickup,
          then drive to drop-off.
    Returns the list of Segment objects (chronological, gap-free).
    """
    sim = TripSimulator(cycle_used_hours, start_time)

    to_pickup, to_dropoff = legs
    sim.drive(to_pickup["miles"], to_pickup["hours"], to_pickup["label"])
    sim.do_task(PICKUP_HOURS, "Pickup (1 hr)")
    sim.drive(to_dropoff["miles"], to_dropoff["hours"], to_dropoff["label"])
    sim.do_task(DROPOFF_HOURS, "Drop-off (1 hr)")

    return sim.segments


# ---------------------------------------------------------------------- output


def _day_bounds(day):
    start = datetime(day.year, day.month, day.day)
    return start, start + timedelta(days=1)


def build_daily_logs(segments, trip_meta=None):
    """Split the timeline into per-calendar-day log sheets.

    Each sheet covers midnight-to-midnight; time before the trip starts on the
    first day and after it ends on the last day is padded as off duty so every
    sheet's totals sum to 24 hours (a partial last day sums to the elapsed part).
    """
    if not segments:
        return []

    logs = []
    day = segments[0].start.date()
    last_day = segments[-1].end.date()
    trip_start = segments[0].start
    trip_end = segments[-1].end

    while day <= last_day:
        day_start, day_end = _day_bounds(day)
        entries = []

        if day_start < trip_start:
            pad_end = min(trip_start, day_end)
            entries.append(
                {
                    "status": OFF_DUTY,
                    "startHour": 0.0,
                    "endHour": (pad_end - day_start).total_seconds() / 3600.0,
                    "label": "Off duty (before trip)",
                    "miles": 0.0,
                }
            )

        for seg in segments:
            s = max(seg.start, day_start)
            e = min(seg.end, day_end)
            if e <= s:
                continue
            frac = (e - s).total_seconds() / max((seg.end - seg.start).total_seconds(), 1)
            entries.append(
                {
                    "status": seg.status,
                    "startHour": (s - day_start).total_seconds() / 3600.0,
                    "endHour": (e - day_start).total_seconds() / 3600.0,
                    "label": seg.label,
                    "miles": seg.miles * frac,
                }
            )

        if trip_end < day_end and trip_end.date() == day:
            entries.append(
                {
                    "status": OFF_DUTY,
                    "startHour": (trip_end - day_start).total_seconds() / 3600.0,
                    "endHour": 24.0,
                    "label": "Off duty (after trip)",
                    "miles": 0.0,
                }
            )

        totals = {OFF_DUTY: 0.0, SLEEPER: 0.0, DRIVING: 0.0, ON_DUTY: 0.0}
        for entry in entries:
            totals[entry["status"]] += entry["endHour"] - entry["startHour"]

        logs.append(
            {
                "date": day.isoformat(),
                "entries": [
                    {
                        "status": e["status"],
                        "startHour": round(e["startHour"], 4),
                        "endHour": round(e["endHour"], 4),
                        "label": e["label"],
                    }
                    for e in entries
                ],
                "totals": {k: round(v, 2) for k, v in totals.items()},
                "milesToday": round(sum(e["miles"] for e in entries), 1),
                **(trip_meta or {}),
            }
        )
        day += timedelta(days=1)

    return logs
