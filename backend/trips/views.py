from datetime import datetime

import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import external, hos


STOP_TYPES = {
    "30-min rest break": "break",
    "10-hr rest (sleeper berth)": "rest",
    "34-hr cycle restart": "restart",
    "Fuel stop": "fuel",
    "Pickup (1 hr)": "pickup",
    "Drop-off (1 hr)": "dropoff",
}


class PlanTripView(APIView):
    def post(self, request):
        data = request.data
        errors = {}
        for field in ("currentLocation", "pickupLocation", "dropoffLocation"):
            if not str(data.get(field, "")).strip():
                errors[field] = "This field is required."
        try:
            cycle_used = float(data.get("cycleUsedHours", 0))
            if not 0 <= cycle_used <= 70:
                errors["cycleUsedHours"] = "Must be between 0 and 70."
        except (TypeError, ValueError):
            errors["cycleUsedHours"] = "Must be a number between 0 and 70."
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            current = external.geocode(data["currentLocation"].strip())
            pickup = external.geocode(data["pickupLocation"].strip())
            dropoff = external.geocode(data["dropoffLocation"].strip())
            routed = external.route([current, pickup, dropoff])
        except external.ExternalServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except requests.RequestException:
            return Response(
                {"detail": "A routing service is unavailable right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        leg_to_pickup, leg_to_dropoff = routed["legs"]
        start_time = self._start_time(data)

        segments = hos.simulate_trip(
            [
                {**self._leg(leg_to_pickup), "label": "Drive to pickup"},
                {**self._leg(leg_to_dropoff), "label": "Drive to drop-off"},
            ],
            cycle_used,
            start_time,
        )

        stops = self._stops(segments, routed["geometry"], current, pickup, dropoff)
        logs = hos.build_daily_logs(segments)

        total_on_duty = sum(
            s.hours for s in segments if s.status in (hos.DRIVING, hos.ON_DUTY)
        )
        return Response(
            {
                "locations": {"current": current, "pickup": pickup, "dropoff": dropoff},
                "route": {
                    "geometry": routed["geometry"],
                    "distanceMi": round(routed["distanceMi"], 1),
                    "drivingHr": round(routed["durationHr"], 2),
                },
                "summary": {
                    "startTime": segments[0].start.isoformat(),
                    "endTime": segments[-1].end.isoformat(),
                    "totalTripHr": round(
                        (segments[-1].end - segments[0].start).total_seconds() / 3600, 2
                    ),
                    "totalOnDutyHr": round(total_on_duty, 2),
                    "cycleUsedAtStart": cycle_used,
                    "days": len(logs),
                    "restStops": sum(1 for s in stops if s["type"] in ("rest", "restart")),
                    "fuelStops": sum(1 for s in stops if s["type"] == "fuel"),
                },
                "segments": [s.as_dict() for s in segments],
                "stops": stops,
                "dailyLogs": logs,
            }
        )

    @staticmethod
    def _leg(leg):
        return {"miles": leg["distanceMi"], "hours": leg["durationHr"]}

    @staticmethod
    def _start_time(data):
        raw = data.get("startTime")
        if raw:
            try:
                return datetime.fromisoformat(raw).replace(tzinfo=None)
            except ValueError:
                pass
        now = datetime.now()
        return now.replace(minute=0 if now.minute < 30 else 30, second=0, microsecond=0)

    @staticmethod
    def _stops(segments, geometry, current, pickup, dropoff):
        stops = [
            {
                "type": "start",
                "label": "Trip start",
                "lat": current["lat"],
                "lon": current["lon"],
                "start": segments[0].start.isoformat(),
                "end": segments[0].start.isoformat(),
                "durationHr": 0,
            }
        ]
        for seg in segments:
            stop_type = STOP_TYPES.get(seg.label)
            if not stop_type:
                continue
            if stop_type == "pickup":
                lat, lon = pickup["lat"], pickup["lon"]
            elif stop_type == "dropoff":
                lat, lon = dropoff["lat"], dropoff["lon"]
            else:
                point = external.point_at_mile(geometry, seg.odometer_mi)
                lat, lon = point[0], point[1]
            stops.append(
                {
                    "type": stop_type,
                    "label": seg.label,
                    "lat": lat,
                    "lon": lon,
                    "start": seg.start.isoformat(),
                    "end": seg.end.isoformat(),
                    "durationHr": round(seg.hours, 2),
                    "odometerMi": round(seg.odometer_mi, 1),
                }
            )
        return stops
