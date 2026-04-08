import { useEffect, useState, useMemo } from "react";
import { APIProvider, Map as GoogleMap, AdvancedMarker, InfoWindow, useMap } from "@vis.gl/react-google-maps";
import type { Place } from "../types";

const DAY_COLORS = [
  "#ef4444", "#3b82f6", "#22c55e", "#eab308",
  "#a855f7", "#ec4899", "#6366f1",
];

const DAY_LABELS = [
  "Day 1", "Day 2", "Day 3", "Day 4",
  "Day 5", "Day 6", "Day 7",
];

interface Props {
  places: Place[];
  googleMapsApiKey: string;
  selectedPlaceId?: string | null;
}

function MapContent({ places, selectedPlaceId }: { places: Place[]; selectedPlaceId?: string | null }) {
  const map = useMap();
  const [selectedPlace, setSelectedPlace] = useState<Place | null>(null);

  const placesWithCoords = useMemo(
    () => places.filter((p) => p.latitude && p.longitude),
    [places]
  );

  // Group by day
  const byDay = useMemo(() => {
    const groups = new Map<number | null, Place[]>();
    placesWithCoords.forEach((p) => {
      const day = p.day_number;
      if (!groups.has(day)) groups.set(day, []);
      groups.get(day)!.push(p);
    });
    // Sort within each day
    groups.forEach((group) => {
      group.sort((a, b) => a.order_in_day - b.order_in_day);
    });
    return groups;
  }, [placesWithCoords]);

  const legendDays = useMemo(
    () => Array.from(byDay.keys())
      .filter((d): d is number => d !== null)
      .sort((a, b) => a - b),
    [byDay]
  );

  // Fit bounds when places change
  useEffect(() => {
    if (!map || placesWithCoords.length === 0) return;
    const bounds = new google.maps.LatLngBounds();
    placesWithCoords.forEach((p) => {
      bounds.extend({ lat: p.latitude!, lng: p.longitude! });
    });
    map.fitBounds(bounds, 50);
  }, [map, placesWithCoords]);

  // Fly to selected place
  useEffect(() => {
    if (!map || !selectedPlaceId) return;
    const place = places.find((p) => p.id === selectedPlaceId);
    if (!place?.latitude || !place?.longitude) return;
    map.panTo({ lat: place.latitude, lng: place.longitude });
    map.setZoom(15);
  }, [map, selectedPlaceId, places]);

  // Draw polylines
  useEffect(() => {
    if (!map) return;
    const polylines: google.maps.Polyline[] = [];

    byDay.forEach((dayPlaces, dayNum) => {
      if (dayPlaces.length < 2) return;
      const color = dayNum !== null
        ? DAY_COLORS[(dayNum - 1) % DAY_COLORS.length]
        : "#999999";
      const path = dayPlaces.map((p) => ({ lat: p.latitude!, lng: p.longitude! }));
      const polyline = new google.maps.Polyline({
        path,
        strokeColor: color,
        strokeWeight: 2,
        strokeOpacity: 0.8,
        geodesic: true,
        map,
      });
      polylines.push(polyline);
    });

    return () => {
      polylines.forEach((p) => p.setMap(null));
    };
  }, [map, byDay]);

  return (
    <>
      {placesWithCoords.map((place) => {
        const dayNum = place.day_number;
        const color = dayNum !== null
          ? DAY_COLORS[(dayNum - 1) % DAY_COLORS.length]
          : "#999999";
        return (
          <AdvancedMarker
            key={place.id}
            position={{ lat: place.latitude!, lng: place.longitude! }}
            onClick={() => setSelectedPlace(place)}
          >
            <div
              style={{
                width: 16,
                height: 16,
                borderRadius: "50%",
                backgroundColor: color,
                border: "2px solid white",
                boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
              }}
            />
          </AdvancedMarker>
        );
      })}

      {selectedPlace && selectedPlace.latitude && selectedPlace.longitude && (
        <InfoWindow
          position={{ lat: selectedPlace.latitude, lng: selectedPlace.longitude }}
          onCloseClick={() => setSelectedPlace(null)}
        >
          <div style={{ padding: "4px 8px" }}>
            <div style={{ fontWeight: 600, fontSize: 14 }}>{selectedPlace.name}</div>
            <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
              {selectedPlace.type}
              {selectedPlace.day_number != null ? ` · Day ${selectedPlace.day_number}` : ""}
            </div>
            {selectedPlace.note && (
              <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>{selectedPlace.note}</div>
            )}
          </div>
        </InfoWindow>
      )}

      {legendDays.length > 0 && (
        <div className="absolute bottom-3 left-3 bg-white/90 rounded-lg px-3 py-2 shadow text-xs flex gap-3" style={{ zIndex: 1 }}>
          {legendDays.map((day) => (
            <div key={day} className="flex items-center gap-1">
              <span
                className="inline-block w-3 h-3 rounded-full"
                style={{ backgroundColor: DAY_COLORS[(day - 1) % DAY_COLORS.length] }}
              />
              <span className="text-gray-600">
                {DAY_LABELS[(day - 1) % DAY_LABELS.length] || `Day ${day}`}
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export function TripMap({ places, googleMapsApiKey, selectedPlaceId }: Props) {
  if (!googleMapsApiKey) {
    return (
      <div className="w-full h-full min-h-[400px] rounded-lg bg-gray-100 flex items-center justify-center text-gray-400 text-sm">
        Set VITE_GOOGLE_MAPS_API_KEY to enable map
      </div>
    );
  }

  return (
    <div className="relative w-full h-full min-h-[400px]">
      <APIProvider apiKey={googleMapsApiKey}>
        <GoogleMap
          className="w-full h-full min-h-[400px] rounded-lg"
          defaultCenter={{ lat: 35.6812, lng: 139.7671 }}
          defaultZoom={11}
          mapId="travel-copilot-map"
          gestureHandling="greedy"
          disableDefaultUI={false}
        >
          <MapContent places={places} selectedPlaceId={selectedPlaceId} />
        </GoogleMap>
      </APIProvider>
    </div>
  );
}
