import { Droppable, Draggable } from "@hello-pangea/dnd";
import { PlaceCard } from "./PlaceCard";
import { getWeekday } from "../utils/openingHours";
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
  startDate?: string;
  onPlaceClick?: (place: Place) => void;
  tripId?: string;
  onUpdatePlace?: (placeId: string, data: Record<string, unknown>) => void;
  onDeletePlace?: (placeId: string) => void;
}

export function DayGroup({ dayNumber, places, label, startDate, onPlaceClick, tripId, onUpdatePlace, onDeletePlace }: Props) {
  const weekday = startDate && dayNumber !== null ? getWeekday(startDate, dayNumber) : undefined;
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
            {(() => {
              // Compute hotel roles and sort accordingly
              type HotelRole = "check_in" | "check_out" | "mid_stay" | null;
              const getHotelRole = (p: Place): HotelRole => {
                if (p.type !== "hotel" || p.check_in_day == null) return null;
                if (dayNumber === p.check_in_day) return "check_in";
                if (dayNumber === p.check_out_day) return "check_out";
                if (dayNumber != null && dayNumber > p.check_in_day && dayNumber < (p.check_out_day ?? p.check_in_day + 1))
                  return "mid_stay";
                return null;
              };

              // Sort: check_out hotels first, then regular + check_in hotels, check_in hotels last
              const sortedPlaces = [...places].sort((a, b) => {
                const roleA = getHotelRole(a);
                const roleB = getHotelRole(b);
                const orderA = roleA === "check_out" ? -1 : roleA === "check_in" ? 1 : 0;
                const orderB = roleB === "check_out" ? -1 : roleB === "check_in" ? 1 : 0;
                if (orderA !== orderB) return orderA - orderB;
                return a.order_in_day - b.order_in_day;
              });

              return sortedPlaces.map((place, index) => {
                const role = getHotelRole(place);

                // Mid-stay hotel: lightweight non-draggable label
                if (role === "mid_stay") {
                  return (
                    <div key={`${place.id}-midstay`} className="text-xs text-gray-400 bg-gray-50 border border-dashed border-gray-200 rounded px-2 py-1.5 text-center">
                      🏨 {place.name} · 住宿中
                    </div>
                  );
                }

                let dist: number | undefined;
                if (index > 0) {
                  const prev = sortedPlaces[index - 1];
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
                          weekday={weekday}
                          hotelRole={role}
                          onPlaceClick={onPlaceClick}
                          tripId={tripId}
                          onUpdate={onUpdatePlace ? (data) => onUpdatePlace(place.id, data) : undefined}
                          onDelete={onDeletePlace ? () => onDeletePlace(place.id) : undefined}
                        />
                      </div>
                    )}
                  </Draggable>
                );
              });
            })()}
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
