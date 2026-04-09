import { useState } from "react";
import { useTripStore } from "../stores/trip";
import { getGoogleMapsUrl } from "../utils/googleMapsLink";
import type { Place } from "../types";

const TYPES = ["attraction", "restaurant", "hotel", "other", "google_saved"] as const;

interface Props {
  place: Place;
  distanceFromPrev?: number;
  onPlaceClick?: (place: Place) => void;
  tripId?: string;
  onUpdate?: (data: Record<string, unknown>) => void;
  onDelete?: () => void;
}

export function PlaceCard({ place, distanceFromPrev, onPlaceClick, tripId, onUpdate, onDelete }: Props) {
  const hasCoords = place.latitude != null && place.longitude != null;
  const editable = !!(onUpdate && onDelete);

  // Editable-mode state
  const { resolveGoogleLink } = useTripStore();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(place.name);
  const [type, setType] = useState(place.type);
  const [note, setNote] = useState(place.note);
  const [googleMapsUrlInput, setGoogleMapsUrlInput] = useState(place.google_maps_url || getGoogleMapsUrl(place) || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confidence = place.geocode_confidence || (place.latitude != null ? "high" : "none");
  const googleMapsUrl = getGoogleMapsUrl(place);

  const handleCancel = () => {
    setName(place.name);
    setType(place.type);
    setNote(place.note);
    setGoogleMapsUrlInput(place.google_maps_url || getGoogleMapsUrl(place) || "");
    setError(null);
    setEditing(false);
  };

  const handleSave = async () => {
    const urlChanged = googleMapsUrlInput && googleMapsUrlInput !== (place.google_maps_url || getGoogleMapsUrl(place) || "");

    if (urlChanged && (googleMapsUrlInput.includes("google.com/maps") || googleMapsUrlInput.includes("goo.gl"))) {
      setSaving(true);
      setError(null);
      try {
        const resolved = await resolveGoogleLink(tripId!, googleMapsUrlInput);
        onUpdate!({
          name, type, note,
          google_maps_url: googleMapsUrlInput,
          latitude: resolved.latitude,
          longitude: resolved.longitude,
          google_place_id: resolved.google_place_id,
          geocode_confidence: "high",
        });
        setEditing(false);
      } catch {
        setError("Invalid Google Maps link");
      } finally {
        setSaving(false);
      }
    } else {
      onUpdate!({ name, type, note, google_maps_url: googleMapsUrlInput || undefined });
      setEditing(false);
    }
  };

  // Edit mode
  if (editable && editing) {
    return (
      <div className="border rounded-lg p-3 space-y-2 bg-white shadow-sm">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border rounded px-2 py-1 text-sm"
        />
        <div className="flex gap-1">
          {TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setType(t)}
              className={`px-2 py-0.5 rounded text-xs border ${
                type === t
                  ? "bg-blue-100 text-blue-700 border-blue-300"
                  : "bg-white text-gray-600 border-gray-200"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="w-full border rounded px-2 py-1 text-sm h-12 resize-none"
          placeholder="Note"
        />
        <input
          type="url"
          value={googleMapsUrlInput}
          onChange={(e) => setGoogleMapsUrlInput(e.target.value)}
          className="w-full border rounded px-2 py-1 text-sm"
          placeholder="Google Maps link (optional)"
        />
        {error && <p className="text-red-500 text-xs">{error}</p>}
        <div className="flex gap-2 justify-end">
          <button
            onClick={handleCancel}
            className="text-gray-500 hover:text-gray-700 text-sm"
            disabled={saving}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            disabled={saving}
          >
            {saving ? "Validating..." : "Save"}
          </button>
        </div>
      </div>
    );
  }

  // Display mode — editable variant
  if (editable) {
    return (
      <div
        className={`bg-white border rounded-lg p-3 shadow-sm${hasCoords && onPlaceClick ? " cursor-pointer hover:border-blue-400" : ""}`}
        onClick={() => hasCoords && onPlaceClick?.(place)}
      >
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-1.5">
              <span
                className={`text-[8px] ${confidence === "high" ? "text-green-500" : confidence === "low" ? "text-orange-500" : "text-red-500"}`}
                title={confidence === "high" ? "Location verified" : confidence === "low" ? "Location uncertain" : "Missing location"}
              >
                ●
              </span>
              <span className={`font-medium text-sm ${confidence === "none" ? "text-red-600" : confidence === "low" ? "text-orange-600" : "text-gray-800"}`}>
                {place.name}
              </span>
              {confidence === "none" && <span className="text-red-500 text-[10px]">缺少定位</span>}
              {confidence === "low" && <span className="text-orange-500 text-[10px]">待确认</span>}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {place.type}
              {place.note && <span className="text-gray-400"> · {place.note}</span>}
            </div>
            {googleMapsUrl && (
              <a
                href={googleMapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 hover:text-blue-700 mt-1 inline-flex items-center gap-1"
                onClick={(e) => e.stopPropagation()}
              >
                Google Maps &#8599;
              </a>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); setEditing(true); }}
              className="text-gray-400 hover:text-blue-600 text-sm"
            >
              Edit
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete!(); }}
              className="text-red-400 hover:text-red-600 text-sm"
            >
              Delete
            </button>
          </div>
        </div>
        {distanceFromPrev !== undefined && distanceFromPrev > 0 && (
          <div className="text-xs text-blue-500 mt-1">
            {distanceFromPrev.toFixed(1)} km from previous
          </div>
        )}
      </div>
    );
  }

  // Display mode — simple (backward-compatible)
  return (
    <div
      className={`bg-white border rounded-lg p-3 shadow-sm${hasCoords && onPlaceClick ? " cursor-pointer hover:border-blue-400" : ""}`}
      onClick={() => hasCoords && onPlaceClick?.(place)}
    >
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
