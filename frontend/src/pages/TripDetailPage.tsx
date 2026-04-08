import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useTripStore } from "../stores/trip";
import { ImageUploader } from "../components/ImageUploader";
import { PlaceForm } from "../components/PlaceForm";
import { ExtractionModal } from "../components/ExtractionModal";
import { getGoogleMapsUrl } from "../utils/googleMapsLink";
import type { ExtractedPlace, Place } from "../types";

function PlaceCard({
  place,
  onDelete,
  onUpdate,
}: {
  place: Place;
  onDelete: () => void;
  onUpdate: (data: { name: string; type: string; note: string }) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(place.name);
  const [type, setType] = useState(place.type);
  const [note, setNote] = useState(place.note);

  const googleMapsUrl = getGoogleMapsUrl(place);
  const TYPES = ["attraction", "restaurant", "hotel", "other"] as const;

  const handleSave = () => {
    onUpdate({ name, type, note });
    setEditing(false);
  };

  const handleCancel = () => {
    setName(place.name);
    setType(place.type);
    setNote(place.note);
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="border rounded-lg p-3 space-y-2">
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
        />
        <div className="flex gap-2 justify-end">
          <button
            onClick={handleCancel}
            className="text-gray-500 hover:text-gray-700 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            Save
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-3 flex justify-between items-start">
      <div>
        <div className="font-medium text-sm text-gray-800">{place.name}</div>
        <div className="text-xs text-gray-500 mt-1">
          {place.type}
          {place.note && ` · ${place.note}`}
        </div>
        <div className="text-xs text-gray-400 mt-1">
          Source: {place.source}
        </div>
        {googleMapsUrl && (
          <a
            href={googleMapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:text-blue-700 mt-1 inline-flex items-center gap-1"
          >
            Google Maps &#8599;
          </a>
        )}
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => setEditing(true)}
          className="text-gray-400 hover:text-blue-600 text-sm"
        >
          Edit
        </button>
        <button
          onClick={onDelete}
          className="text-red-400 hover:text-red-600 text-sm"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

export function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const {
    currentTrip,
    places,
    loading,
    fetchTripDetail,
    addPlace,
    updatePlace,
    deletePlace,
    extractPlaces,
  } = useTripStore();
  const [extracting, setExtracting] = useState(false);
  const [extracted, setExtracted] = useState<ExtractedPlace[] | null>(null);

  useEffect(() => {
    if (tripId) fetchTripDetail(tripId);
  }, [tripId, fetchTripDetail]);

  const handleExtract = async (files: File[]) => {
    if (!tripId) return;
    setExtracting(true);
    try {
      const result = await extractPlaces(tripId, files);
      setExtracted(result);
    } finally {
      setExtracting(false);
    }
  };

  const handleConfirmExtracted = async (selected: ExtractedPlace[]) => {
    if (!tripId) return;
    for (const place of selected) {
      await addPlace(tripId, {
        name: place.name,
        type: place.type,
        note: "",
        name_local: place.name_local || "",
        name_en: place.name_en || "",
        latitude: place.latitude,
        longitude: place.longitude,
        day_number: place.day_number,
        order_in_day: place.order_in_day,
        source: "ai_extracted",
      });
    }
    setExtracted(null);
  };

  const handleAddManual = async (data: { name: string; type: string; note: string; latitude?: number | null; longitude?: number | null; google_place_id?: string; source?: string }) => {
    if (tripId) await addPlace(tripId, data);
  };

  const handleDeletePlace = async (placeId: string) => {
    if (tripId) await deletePlace(tripId, placeId);
  };

  const handleUpdatePlace = async (placeId: string, data: { name: string; type: string; note: string }) => {
    if (tripId) await updatePlace(tripId, placeId, data);
  };

  if (loading || !currentTrip) {
    return <div className="text-center py-20 text-gray-500">Loading...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">{currentTrip.name}</h2>
          <p className="text-sm text-gray-500">
            {currentTrip.start_date} ~ {currentTrip.end_date}
          </p>
        </div>
        <Link
          to={`/trips/${tripId}/plan`}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
        >
          Plan Itinerary
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: Upload & Add */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-gray-700 mb-3">Upload Screenshots</h3>
            <ImageUploader onUpload={handleExtract} loading={extracting} />
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-gray-700 mb-3">Add Place</h3>
            <PlaceForm onSubmit={handleAddManual} tripId={tripId!} />
          </div>
        </div>

        {/* Right: Place list */}
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <h3 className="font-medium text-gray-700 mb-3">
            Places ({places.length})
          </h3>
          <div className="space-y-2">
            {places.map((place) => (
              <PlaceCard
                key={place.id}
                place={place}
                onDelete={() => handleDeletePlace(place.id)}
                onUpdate={(data) => handleUpdatePlace(place.id, data)}
              />
            ))}
            {places.length === 0 && (
              <p className="text-gray-400 text-sm text-center py-8">
                No places yet. Upload screenshots or add manually.
              </p>
            )}
          </div>
        </div>
      </div>

      {extracted && (
        <ExtractionModal
          places={extracted}
          onConfirm={handleConfirmExtracted}
          onClose={() => setExtracted(null)}
        />
      )}
    </div>
  );
}
