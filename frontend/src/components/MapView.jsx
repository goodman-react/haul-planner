import L from "leaflet";
import { useEffect, useRef } from "react";

const STOP_STYLE = {
  start: { color: "#4f6f52", emoji: "🚚", title: "Trip start" },
  pickup: { color: "#e8a13c", emoji: "📦", title: "Pickup" },
  dropoff: { color: "#d94f2b", emoji: "🏁", title: "Drop-off" },
  fuel: { color: "#8c5a2b", emoji: "⛽", title: "Fuel stop" },
  break: { color: "#c96f3a", emoji: "☕", title: "30-min break" },
  rest: { color: "#3b2417", emoji: "😴", title: "10-hr rest" },
  restart: { color: "#5b4636", emoji: "🔄", title: "34-hr restart" },
};

function fmt(iso) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function MapView({ result }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (!mapRef.current) {
      mapRef.current = L.map(containerRef.current, { scrollWheelZoom: true });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
      }).addTo(mapRef.current);
    }
    const map = mapRef.current;

    const layer = L.layerGroup().addTo(map);
    // Retro two-tone "highway" line: dark road with amber dashes.
    const line = L.polyline(result.route.geometry, {
      color: "#3b2417",
      weight: 7,
      opacity: 0.95,
    }).addTo(layer);
    L.polyline(result.route.geometry, {
      color: "#e8a13c",
      weight: 2.5,
      opacity: 0.95,
      dashArray: "10 12",
    }).addTo(layer);

    result.stops.forEach((stop) => {
      const style = STOP_STYLE[stop.type] || STOP_STYLE.start;
      const icon = L.divIcon({
        className: "stop-marker",
        html: `<div class="stop-pin" style="--pin:${style.color}">${style.emoji}</div>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });
      const duration =
        stop.durationHr > 0 ? `<br/>Duration: <b>${stop.durationHr} h</b>` : "";
      L.marker([stop.lat, stop.lon], { icon })
        .bindPopup(
          `<b>${style.emoji} ${stop.label || style.title}</b><br/>` +
            `${fmt(stop.start)}${duration}` +
            (stop.odometerMi ? `<br/>Mile ${stop.odometerMi.toLocaleString()}` : "")
        )
        .addTo(layer);
    });

    // Wait a frame so the container has its final size before fitting bounds,
    // and refit whenever the container is resized (e.g. rotating a phone).
    const fit = () => {
      map.invalidateSize();
      map.fitBounds(line.getBounds(), { padding: [30, 30] });
    };
    const raf = requestAnimationFrame(fit);
    const observer = new ResizeObserver(() => fit());
    observer.observe(containerRef.current);
    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      layer.remove();
    };
  }, [result]);

  return <div ref={containerRef} className="map-container" />;
}
