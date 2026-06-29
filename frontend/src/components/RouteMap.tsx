"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Polyline, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { RouteStop } from "@/lib/atlas";

function numberedIcon(n: number) {
  return L.divIcon({
    className: "",
    html: `<div style="display:flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:#1D4ED8;border:2px solid #fff;box-shadow:0 1px 6px rgba(0,0,0,.35)"><span style="transform:rotate(45deg);font-family:ui-monospace,monospace;font-weight:700;font-size:11px;color:#fff">${n}</span></div>`,
    iconSize: [26, 26], iconAnchor: [13, 26], popupAnchor: [0, -22],
  });
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    if (points.length === 1) map.setView(points[0], 9);
    else map.fitBounds(points, { padding: [50, 50] });
  }, [map, points]);
  return null;
}

export default function RouteMap({ route }: { route: RouteStop[] }) {
  const points = route.map((s) => [s.latitude, s.longitude] as [number, number]);
  return (
    <MapContainer center={points[0] ?? [35.68, 139.76]} zoom={6} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
      <TileLayer attribution='&copy; OpenStreetMap &copy; CARTO' url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png" />
      {points.length > 1 && <Polyline positions={points} pathOptions={{ color: "#1D4ED8", weight: 3, opacity: 0.8, dashArray: "6 8" }} />}
      {route.map((stop, i) => (
        <Marker key={stop.name} position={[stop.latitude, stop.longitude]} icon={numberedIcon(i + 1)}>
          <Popup><strong>{stop.name}</strong><br />{stop.day_start === stop.day_end ? `Day ${stop.day_start}` : `Days ${stop.day_start}–${stop.day_end}`}</Popup>
        </Marker>
      ))}
      <FitBounds points={points} />
    </MapContainer>
  );
}