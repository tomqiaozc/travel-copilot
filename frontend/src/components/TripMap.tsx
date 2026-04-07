import { useEffect, useRef, useState } from "react";
import * as atlas from "azure-maps-control";
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
  azureMapsKey: string;
}

export function TripMap({ places, azureMapsKey }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<atlas.Map | null>(null);
  const isReady = useRef(false);
  const popupRef = useRef<atlas.Popup | null>(null);
  const [legendDays, setLegendDays] = useState<number[]>([]);

  // Initialize map once
  useEffect(() => {
    if (!mapRef.current || !azureMapsKey) return;

    const map = new atlas.Map(mapRef.current, {
      authOptions: {
        authType: atlas.AuthenticationType.subscriptionKey as any,
        subscriptionKey: azureMapsKey,
      },
      center: [139.7671, 35.6812],
      zoom: 11,
      style: "road",
    });

    mapInstance.current = map;

    map.events.addOnce("ready", () => {
      isReady.current = true;
      popupRef.current = new atlas.Popup({ closeButton: true, pixelOffset: [0, -10] });
    });

    return () => {
      isReady.current = false;
      popupRef.current = null;
      map.dispose();
      mapInstance.current = null;
    };
  }, [azureMapsKey]);

  // Update markers/lines when places change
  useEffect(() => {
    const map = mapInstance.current;
    if (!map) return;

    const renderData = () => {
      map.sources.clear();
      map.layers.clear();

      const dataSource = new atlas.source.DataSource();
      map.sources.add(dataSource);

      const placesWithCoords = places.filter((p) => p.latitude && p.longitude);
      if (placesWithCoords.length === 0) {
        setLegendDays([]);
        return;
      }

      // Group by day
      const byDay = new Map<number | null, Place[]>();
      placesWithCoords.forEach((p) => {
        const day = p.day_number;
        if (!byDay.has(day)) byDay.set(day, []);
        byDay.get(day)!.push(p);
      });

      // Track which days appear for the legend
      const days = Array.from(byDay.keys())
        .filter((d): d is number => d !== null)
        .sort((a, b) => a - b);
      setLegendDays(days);

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
              note: place.note || "",
              type: place.type,
              day: dayNum,
              color,
            });
            dataSource.add(feature as any);
          });

        if (dayPlaces.length > 1) {
          const coords = dayPlaces.map((p) => [p.longitude!, p.latitude!]);
          const line = new atlas.data.LineString(coords);
          dataSource.add(new atlas.data.Feature(line, { color }) as any);
        }
      });

      const bubbleLayer = new atlas.layer.BubbleLayer(dataSource, undefined, {
        radius: 8,
        color: ["get", "color"] as any,
        strokeColor: "white",
        strokeWidth: 2,
        filter: ["==", ["geometry-type"], "Point"] as any,
      });

      map.layers.add(bubbleLayer);

      map.layers.add(
        new atlas.layer.LineLayer(dataSource, undefined, {
          strokeColor: ["get", "color"] as any,
          strokeWidth: 2,
          strokeDashArray: [2, 2],
          filter: ["==", ["geometry-type"], "LineString"] as any,
        })
      );

      // Click-to-view popup on markers
      map.events.add("click", bubbleLayer, (e: any) => {
        if (!e.shapes || e.shapes.length === 0 || !popupRef.current) return;
        const shape = e.shapes[0];
        const props = typeof shape.getProperties === "function"
          ? shape.getProperties()
          : shape.properties;
        const coords = typeof shape.getCoordinates === "function"
          ? shape.getCoordinates()
          : (shape.geometry as any)?.coordinates;
        if (!props || !coords) return;

        const noteHtml = props.note
          ? `<div style="font-size:12px;color:#666;margin-top:4px">${props.note}</div>`
          : "";
        popupRef.current.setOptions({
          position: coords,
          content: `<div style="padding:8px 12px">
            <div style="font-weight:600;font-size:14px">${props.name}</div>
            <div style="font-size:12px;color:#888;margin-top:2px">${props.type}${props.day != null ? ` · Day ${props.day}` : ""}</div>
            ${noteHtml}
          </div>`,
        });
        popupRef.current.open(map);
      });

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

    if (isReady.current) {
      renderData();
    } else {
      map.events.addOnce("ready", renderData);
    }
  }, [places]);

  if (!azureMapsKey) {
    return (
      <div className="w-full h-full min-h-[400px] rounded-lg bg-gray-100 flex items-center justify-center text-gray-400 text-sm">
        Set VITE_AZURE_MAPS_KEY to enable map
      </div>
    );
  }

  return (
    <div className="relative w-full h-full min-h-[400px]">
      <div ref={mapRef} className="w-full h-full min-h-[400px] rounded-lg" />
      {legendDays.length > 0 && (
        <div className="absolute bottom-3 left-3 bg-white/90 rounded-lg px-3 py-2 shadow text-xs flex gap-3">
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
    </div>
  );
}
