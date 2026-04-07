import type { Place } from "../types";

interface Props {
  place: Place;
  distanceFromPrev?: number;
}

export function PlaceCard({ place, distanceFromPrev }: Props) {
  return (
    <div className="bg-white border rounded-lg p-3 shadow-sm">
      <div className="font-medium text-sm text-gray-800">{place.name}</div>
      <div className="text-xs text-gray-500 mt-1">
        {place.type}
        {place.note && (
          <span className="text-gray-400"> · {place.note}</span>
        )}
      </div>
      {distanceFromPrev !== undefined && distanceFromPrev > 0 && (
        <div className="text-xs text-blue-500 mt-1">
          {distanceFromPrev.toFixed(1)} km from previous
        </div>
      )}
    </div>
  );
}
