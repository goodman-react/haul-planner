import { useState } from "react";
import { planTrip } from "./api.js";
import LogSheet from "./components/LogSheet.jsx";
import MapView from "./components/MapView.jsx";
import SummaryBar from "./components/SummaryBar.jsx";
import Timeline from "./components/Timeline.jsx";
import TripForm from "./components/TripForm.jsx";

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(values) {
    setLoading(true);
    setError("");
    try {
      const data = await planTrip(values);
      setResult(data);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <div className="stripes" />
      <header className="hero">
        <div className="hero-inner">
          <div className="hero-topline">
            <div className="logo">HaulPlanner</div>
            <div className="badge">FMCSA · 70 HR / 8 DAY · CH·19</div>
          </div>
          <h1>
            Long haul? <em>We got your back.</em>
          </h1>
          <p>
            Punch in the trip and your cycle hours — get legal miles, mandatory
            shut-eye, fuel stops, and logbook pages done before you finish your
            coffee.
          </p>
        </div>
      </header>

      <main className="content">
        <TripForm onSubmit={handleSubmit} loading={loading} />

        {error && <div className="error-banner">⚠ {error}</div>}

        {loading && (
          <div className="loading">
            <div className="spinner" />
            <p>Geocoding, routing and running the HOS simulation…</p>
          </div>
        )}

        {result && !loading && (
          <>
            <SummaryBar summary={result.summary} route={result.route} />
            <div className="map-timeline">
              <section className="panel map-panel">
                <h2>The Route</h2>
                <MapView result={result} />
              </section>
              <section className="panel timeline-panel">
                <h2>The Rundown</h2>
                <Timeline segments={result.segments} />
              </section>
            </div>
            <section className="panel logs-panel">
              <h2>
                The Logbook{" "}
                <span className="log-count">{result.dailyLogs.length} page(s)</span>
              </h2>
              {result.dailyLogs.map((log, i) => (
                <LogSheet
                  key={log.date}
                  log={log}
                  index={i}
                  locations={result.locations}
                />
              ))}
            </section>
          </>
        )}
      </main>

      <footer className="footer">
        10-4, good buddy · Routing © OSRM &amp; OpenStreetMap contributors ·
        Built for the FMCSA Hours-of-Service assessment
      </footer>
    </div>
  );
}
