"""Free external services: Nominatim (geocoding) and OSRM (routing)."""

import math

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
USER_AGENT = "haulplanner-assessment/1.0"

METERS_PER_MILE = 1609.344


class ExternalServiceError(Exception):
    pass


def geocode(query):
    """Resolve a free-text place to {name, lat, lon}."""
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ExternalServiceError(f'Could not find a location for "{query}".')
    top = results[0]
    return {
        "query": query,
        "name": top["display_name"],
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
    }


def route(points):
    """OSRM driving route through the given points.

    points: [{lat, lon}, ...]  (2+ points; extra points become waypoints)
    Returns {"distanceMi", "durationHr", "geometry": [[lat, lon], ...],
             "legs": [{"distanceMi", "durationHr"}]}
    """
    coords = ";".join(f"{p['lon']},{p['lat']}" for p in points)
    resp = requests.get(
        f"{OSRM_URL}/{coords}",
        params={"overview": "full", "geometries": "geojson", "steps": "false"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ExternalServiceError("No drivable route found between those locations.")

    best = data["routes"][0]
    return {
        "distanceMi": best["distance"] / METERS_PER_MILE,
        "durationHr": best["duration"] / 3600.0,
        "geometry": [[lat, lon] for lon, lat in best["geometry"]["coordinates"]],
        "legs": [
            {
                "distanceMi": leg["distance"] / METERS_PER_MILE,
                "durationHr": leg["duration"] / 3600.0,
            }
            for leg in best["legs"]
        ],
    }


def haversine_miles(a, b):
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 3958.7613 * 2 * math.asin(math.sqrt(h))


def point_at_mile(geometry, target_mi):
    """Interpolate the [lat, lon] at a given odometer mile along the geometry."""
    if not geometry:
        return None
    if target_mi <= 0:
        return geometry[0]
    travelled = 0.0
    for i in range(1, len(geometry)):
        step = haversine_miles(geometry[i - 1], geometry[i])
        if travelled + step >= target_mi and step > 0:
            f = (target_mi - travelled) / step
            lat = geometry[i - 1][0] + f * (geometry[i][0] - geometry[i - 1][0])
            lon = geometry[i - 1][1] + f * (geometry[i][1] - geometry[i - 1][1])
            return [lat, lon]
        travelled += step
    return geometry[-1]
