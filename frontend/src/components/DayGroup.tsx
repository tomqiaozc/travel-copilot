import { Droppable, Draggable } from "@hello-pangea/dnd";
import { PlaceCard } from "./PlaceCard";
import type { Place } from "../types";

const DAY_COLORS = [
  "border-red-400",
  "border-blue-400",
  "border-green-400",
  "border-yellow-400",
  "border-purple-400",
  "border-pink-400",
  "border-indigo-400",
];

const DAY_BG_COLORS = [
  "bg-red-50",
  "bg-blue-50",
  "bg-green-50",
  "bg-yellow-50",
  "bg-purple-50",
  "bg-pink-50",
  "bg-indigo-50",
];

function haversineKm(
  lat1: number, lon1: number,
  lat2: number, lon2: number
): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  return (
    Math.acos(
      Math.sin(toRad(lat1)) * Math.sin(toRad(lat2)) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(toRad(lon2 - lon1))
    ) * 6371
  );
}

interface Props {
  dayNumber: number | null;
  places: Place[];
  label: string;
  onPlaceClick?: (place: Place) => void;
  tripId?: string;
  onUpdatePlace?: (placeId: string, data: Record<string, unknown>) => void;
  onDeletePlace?: (placeId: string) => void;
}

export function DayGroup({ dayNumber, places, label, onPlaceClick, tripId, onUpdatePlace, onDeletePlace }: Props) {
  const droppableId = dayNumber !== null ? `day-${dayNumber}` : "unassigned";
  const colorIdx = dayNumber !== null ? (dayNumber - 1) % DAY_COLORS.length : -1;
  const borderColor = colorIdx >= 0 ? DAY_COLORS[colorIdx] : "border-gray-300";
  const bgColor = colorIdx >= 0 ? DAY_BG_COLORS[colorIdx] : "bg-gray-50";

  return (
    <div className={`border-l-4 ${borderColor} ${bgColor} rounded-lg p-3 mb-4`}>
      <div className="font-bold text-sm text-gray-700 mb-2">{label}</div>
      <Droppable droppableId={droppableId}>
        {(provided, snapshot) => (
          <div ref={provided.innerRef} {...provided.droppableProps} className={`space-y-2 min-h-[40px] transition-colors ${snapshot.isDraggingOver ? "bg-blue-100/50 rounded-lg" : ""}`}>
            {places.map((place, index) => {
              let dist: number | undefined;
              if (index > 0) {
                const prev = places[index - 1];
                if (
                  prev.latitude != null && prev.longitude != null &&
                  place.latitude != null && place.longitude != null
                ) {
                  dist = haversineKm(
                    prev.latitude, prev.longitude,
                    place.latitude, place.longitude
                  );
                }
              }
              return (
                <Draggable key={place.id} draggableId={place.id} index={index}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.draggableProps}
                      {...provided.dragHandleProps}
                      className={snapshot.isDragging ? "opacity-90 scale-[1.02] z-10" : ""}
                      style={{
                        ...provided.draggableProps.style,
                        ...(snapshot.isDragging ? { boxShadow: "0 8px 25px rgba(0,0,0,0.15)" } : {}),
                      }}
                    >
                      <PlaceCard
                        place={place}
                        distanceFromPrev={dist}
                        onPlaceClick={onPlaceClick}
                        tripId={tripId}
                        onUpdate={onUpdatePlace ? (data) => onUpdatePlace(place.id, data) : undefined}
                        onDelete={onDeletePlace ? () => onDeletePlace(place.id) : undefined}
                      />
                    </div>
                  )}
                </Draggable>
              );
            })}
            {provided.placeholder}
            {places.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-2">
                Drag places here
              </p>
            )}
          </div>
        )}
      </Droppable>
    </div>
  );
}
