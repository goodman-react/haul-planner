from datetime import datetime

from django.test import SimpleTestCase

from . import hos


START = datetime(2026, 8, 17, 8, 0)


def run(miles1, hours1, miles2, hours2, cycle=0.0):
    return hos.simulate_trip(
        [
            {"miles": miles1, "hours": hours1, "label": "Drive to pickup"},
            {"miles": miles2, "hours": hours2, "label": "Drive to drop-off"},
        ],
        cycle,
        START,
    )


def total_hours(segments, status):
    return sum(s.hours for s in segments if s.status == status)


class ShortTripTests(SimpleTestCase):
    def test_short_trip_has_no_rest_events(self):
        segs = run(60, 1.0, 120, 2.0)
        labels = [s.label for s in segs]
        self.assertNotIn("30-min rest break", labels)
        self.assertNotIn("10-hr rest (sleeper berth)", labels)
        self.assertNotIn("Fuel stop", labels)
        self.assertAlmostEqual(total_hours(segs, hos.DRIVING), 3.0, places=4)
        # pickup + dropoff
        self.assertAlmostEqual(total_hours(segs, hos.ON_DUTY), 2.0, places=4)

    def test_timeline_is_contiguous(self):
        segs = run(300, 5.5, 400, 7.0)
        for a, b in zip(segs, segs[1:]):
            self.assertEqual(a.end, b.start)


class BreakRuleTests(SimpleTestCase):
    def test_break_inserted_after_8_hours_driving(self):
        # 10 h to pickup: must split at 8 h with a 30-min break.
        segs = run(550, 10.0, 30, 0.5)
        breaks = [s for s in segs if s.label == "30-min rest break"]
        self.assertEqual(len(breaks), 1)
        drive_before = sum(
            s.hours for s in segs if s.status == hos.DRIVING and s.end <= breaks[0].start
        )
        self.assertAlmostEqual(drive_before, 8.0, places=4)

    def test_pickup_hour_resets_break_clock(self):
        # 7 h to pickup, 1 h pickup (>=30 min non-driving), then 7 h more:
        # cumulative driving never exceeds 8 h without a qualifying interruption,
        # so no explicit 30-min break is needed before the 11-h limit matters.
        segs = run(400, 7.0, 220, 4.0)
        self.assertNotIn("30-min rest break", [s.label for s in segs])


class DailyLimitTests(SimpleTestCase):
    def test_rest_inserted_at_11_hour_driving_limit(self):
        segs = run(700, 13.0, 60, 1.0)
        rests = [s for s in segs if s.label == "10-hr rest (sleeper berth)"]
        self.assertGreaterEqual(len(rests), 1)
        # Driving before the first rest must not exceed 11 h.
        drive_before = sum(
            s.hours
            for s in segs
            if s.status == hos.DRIVING and s.end <= rests[0].start
        )
        self.assertLessEqual(drive_before, 11.0 + 1e-6)

    def test_no_driving_past_14_hour_window(self):
        segs = run(600, 11.0, 600, 11.0)
        # Reconstruct shifts: windows start at first work after a rest.
        window_start = None
        for seg in segs:
            if seg.status in (hos.DRIVING, hos.ON_DUTY):
                if window_start is None:
                    window_start = seg.start
                if seg.status == hos.DRIVING:
                    elapsed = (seg.end - window_start).total_seconds() / 3600
                    self.assertLessEqual(elapsed, 14.0 + 1e-6)
            elif seg.hours >= 10 - 1e-6:
                window_start = None


class FuelTests(SimpleTestCase):
    def test_fuel_stop_every_1000_miles(self):
        segs = run(1500, 25.0, 900, 15.0)  # 2400 mi total
        fuels = [s for s in segs if s.label == "Fuel stop"]
        self.assertEqual(len(fuels), 2)
        self.assertAlmostEqual(fuels[0].odometer_mi, 1000.0, delta=1.0)
        self.assertAlmostEqual(fuels[1].odometer_mi, 2000.0, delta=1.0)


class CycleTests(SimpleTestCase):
    def test_restart_when_cycle_exhausted(self):
        # 66 h already used; ~9.5 h of on-duty work ahead forces a restart.
        segs = run(300, 5.0, 150, 2.5, cycle=66.0)
        restarts = [s for s in segs if s.label == "34-hr cycle restart"]
        self.assertEqual(len(restarts), 1)
        self.assertAlmostEqual(restarts[0].hours, 34.0, places=4)

    def test_no_restart_with_fresh_cycle(self):
        segs = run(300, 5.0, 150, 2.5, cycle=0.0)
        self.assertNotIn("34-hr cycle restart", [s.label for s in segs])


class DailyLogTests(SimpleTestCase):
    def test_each_full_day_totals_24_hours(self):
        segs = run(1200, 20.0, 800, 14.0)
        logs = hos.build_daily_logs(segs)
        self.assertGreaterEqual(len(logs), 2)
        for log in logs[:-1]:
            self.assertAlmostEqual(sum(log["totals"].values()), 24.0, places=2)

    def test_miles_split_across_days_sum_to_total(self):
        segs = run(1200, 20.0, 800, 14.0)
        logs = hos.build_daily_logs(segs)
        total = sum(log["milesToday"] for log in logs)
        self.assertAlmostEqual(total, 2000.0, delta=2.0)

    def test_entries_are_contiguous_within_day(self):
        segs = run(600, 10.0, 700, 12.0)
        for log in hos.build_daily_logs(segs):
            entries = log["entries"]
            self.assertAlmostEqual(entries[0]["startHour"], 0.0, places=3)
            for a, b in zip(entries, entries[1:]):
                self.assertAlmostEqual(a["endHour"], b["startHour"], places=3)
