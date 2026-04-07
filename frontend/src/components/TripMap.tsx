import { useEffect, useRef } from "react";
import * as atlas from "azure-maps-control";
import type { Place } from "../types";

const DAY_COLORS = [
  "#ef4444", "#3b82f6", "#22c55e", "#eab308",
  "#a855f7", "#ec4899", "#6366f1",
];

interface Props {
  places: Place[];
  azureMapsKey: string;
}

export function TripMap({ places, azureMapsKey }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<atlas.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || !azureMapsKey) return;

    const map = new atlas.Map(mapRef.current, {
      authOptions: {
        authType: atlas.AuthenticationType.subscriptionKey as any,
        subscriptionKey: azureMapsKey,
      },
      center: [139.7671, 35.6812], // Default: Tokyo
      zoom: 11,
      style: "road",
    });

    mapInstance.current = map;

    return () => {
      map.dispose();
    };
  }, [azureMapsKey]);

  useEffect(() => {
    const map = mapInstance.current;
    if (!map) return;

    const onReady = () => {
      // Clear existing layers
      map.sources.clear();
      map.layers.clear();

      const dataSource = new atlas.source.DataSource();
      map.sources.add(dataSource);

      const placesWithCoords = places.filter((p) => p.latitude && p.longitude);
      if (placesWithCoords.length === 0) return;

      // Group by day
      const byDay = new Map<number | null, Place[]>();
      placesWithCoords.forEach((p) => {
        const day = p.day_number;
        if (!byDay.has(day)) byDay.set(day, []);
        byDay.get(day)!.push(p);
      });

      // Add markers per day with different colors
      byDay.forEach((dayPlaces, dayNum) => {
        const color =
          dayNum !== null
            ? DAY_COLORS[(dayNum - 1) % DAY_COLORS.length]
            : "#999999";

        dayPlaces
          .sort((a, b) => a.order_in_day - b.order_in_day)
          .forEach((place) => {
            const point = new atlas.data.Point([place.longitude!, place.latitude!]);
            const feature = new atlas.data.Feature(point, {
              name: place.name,
              type: place.type,
              day: dayNum,
              color,
            });
            dataSource.add(feature as any);
          });

        // Draw lines connecting same-day places
        if (dayPlaces.length > 1) {
          const coords = dayPlaces.map((p) => [p.longitude!, p.latitude!]);
          const line = new atlas.data.LineString(coords);
          dataSource.add(new atlas.data.Feature(line, { color }) as any);
        }
      });

      // Bubble layer for points
      map.layers.add(
        new atlas.layer.BubbleLayer(dataSource, undefined, {
          radius: 8,
          color: ["get", "color"] as any,
          strokeColor: "white",
          strokeWidth: 2,
          filter: ["==", ["geometry-type"], "Point"] as any,
        })
      );

      // Line layer for routes
      map.layers.add(
        new atlas.layer.LineLayer(dataSource, undefined, {
          strokeColor: ["get", "color"] as any,
          strokeWidth: 2,
          strokeDashArray: [2, 2],
          filter: ["==", ["geometry-type"], "LineString"] as any,
        })
      );

      // Fit bounds
      const positions = placesWithCoords.map(
        (p) => new atlas.data.Position(p.longitude!, p.latitude!)
      );
      if (positions.length > 0) {
        map.setCamera({
          bounds: atlas.data.BoundingBox.fromPositions(positions),
          padding: 50,
        });
      }
    };

    map.events.addOnce("ready", onReady);
  }, [places]);

  if (!azureMapsKey) {
    return (
      <div className="w-full h-full min-h-[400px] rounded-lg bg-gray-100 flex items-center justify-center text-gray-400 text-sm">
        Set VITE_AZURE_MAPS_KEY to enable map
      </div>
    );
  }

  return (
    <div ref={mapRef} className="w-full h-full min-h-[400px] rounded-lg" />
  );
}
