# HaulPlanner — FMCSA Hours-of-Service Route & Daily Logs

Full-stack app (Django + React) that takes trip details and produces:

- A **route map** (Leaflet + OpenStreetMap) with every stop: pickup, drop-off,
  fuel stops, 30-minute breaks, 10-hour rests and 34-hour restarts.
- **FMCSA Driver's Daily Log sheets**, drawn as the real paper form (24-hour
  graph grid, duty-status step line, per-status totals, remarks), one sheet per
  calendar day.

## Inputs

| Field | Meaning |
| --- | --- |
| Current location | Where the driver is now |
| Pickup location | Where the load is collected (+1 hr on duty) |
| Drop-off location | Destination (+1 hr on duty) |
| Current cycle used (hrs) | Hours already used in the 70 hr / 8 day cycle |

## HOS rules implemented (property-carrying, 70 hr/8 day)

- 11-hour driving limit per shift
- 14-hour driving window (not paused by breaks)
- 30-minute break after 8 cumulative driving hours (any 30+ min non-driving
  period qualifies — fuel stops and pickup/drop-off count)
- 10 consecutive hours off duty (sleeper berth) resets the daily clocks
- 70-hour cycle limit with a 34-hour restart when exhausted
- Fuel stop (30 min) at least every 1,000 miles

## Stack

- **Backend**: Django 5 + Django REST Framework. The HOS engine
  (`backend/trips/hos.py`) is a pure-Python simulator covered by unit tests
  (`backend/trips/tests.py`).
- **Routing**: OSRM public server (free, keyless). **Geocoding**: Nominatim.
- **Frontend**: React 18 + Vite, Leaflet map, hand-drawn SVG log sheets.

## Run locally

Backend:

```bash
cd backend
pip install -r requirements.txt
python manage.py runserver 8001
```

Frontend (proxies `/api` to `127.0.0.1:8001`):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

Tests:

```bash
cd backend
python manage.py test
```

## Deploy (both on Vercel)

Create **two Vercel projects** from this one repo:

1. **Backend** — import the repo, set Root Directory to `backend/`, framework
   "Other". Django runs as a Python serverless function via `api/index.py` +
   `vercel.json`. Set env vars `SECRET_KEY` (random string) and `DEBUG=false`.
2. **Frontend** — import the repo again, Root Directory `frontend/`, framework
   Vite. Set `VITE_API_URL` to the backend project's URL (no trailing slash).

(`backend/build.sh` is only needed for Render-style hosts and is unused on
Vercel.)

## API

`POST /api/trips/`

```json
{
  "currentLocation": "Chicago, IL",
  "pickupLocation": "Indianapolis, IN",
  "dropoffLocation": "Dallas, TX",
  "cycleUsedHours": 20
}
```

Returns route geometry, the stop list, the full duty-status timeline and
per-day log-sheet data.
