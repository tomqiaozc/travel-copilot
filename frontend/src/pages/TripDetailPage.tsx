import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useTripStore } from "../stores/trip";
import { ImageUploader } from "../components/ImageUploader";
import { PlaceForm } from "../components/PlaceForm";
import { ExtractionModal } from "../components/ExtractionModal";
import { ImportModal } from "../components/ImportModal";
import { SkeletonTripDetail } from "../components/Skeleton";
import { getGoogleMapsUrl } from "../utils/googleMapsLink";
import type { ExtractedPlace, Place } from "../types";

function PlaceCard({
  place,
  tripId,
  onDelete,
  onUpdate,
}: {
  place: Place;
  tripId: string;
  onDelete: () => void;
  onUpdate: (data: Record<string, unknown>) => void;
}) {
  const { resolveGoogleLink } = useTripStore();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(place.name);
  const [type, setType] = useState(place.type);
  const [note, setNote] = useState(place.note);
  const [googleMapsUrlInput, setGoogleMapsUrlInput] = useState(place.google_maps_url || getGoogleMapsUrl(place) || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const googleMapsUrl = getGoogleMapsUrl(place);
  const confidence = place.geocode_confidence || (place.latitude != null ? "high" : "none");
  const TYPES = ["attraction", "restaurant", "hotel", "other", "google_saved"] as const;

  const handleSave = async () => {
    const urlChanged = googleMapsUrlInput && googleMapsUrlInput !== (place.google_maps_url || getGoogleMapsUrl(place) || "");

    if (urlChanged && googleMapsUrlInput.includes("google.com/maps") || urlChanged && googleMapsUrlInput.includes("goo.gl")) {
      // Validate and resolve the new Google Maps link
      setSaving(true);
      setError(null);
      try {
        const resolved = await resolveGoogleLink(tripId, googleMapsUrlInput);
        onUpdate({
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
      onUpdate({ name, type, note, google_maps_url: googleMapsUrlInput || undefined });
      setEditing(false);
    }
  };

  const handleCancel = () => {
    setName(place.name);
    setType(place.type);
    setNote(place.note);
    setGoogleMapsUrlInput(place.google_maps_url || getGoogleMapsUrl(place) || "");
    setError(null);
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

  return (
    <div className="border rounded-lg p-3 flex justify-between items-start">
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
    updateTrip,
    deletePlace,
    extractPlaces,
  } = useTripStore();
  const [extracting, setExtracting] = useState(false);
  const [extracted, setExtracted] = useState<ExtractedPlace[] | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleInput, setTitleInput] = useState("");
  const [showImportModal, setShowImportModal] = useState(false);
  const [showImportHelp, setShowImportHelp] = useState(false);

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
        google_place_id: place.google_place_id,
        geocode_confidence: place.geocode_confidence,
        day_number: place.day_number,
        order_in_day: place.order_in_day,
        source: "ai_extracted",
      });
    }
    setExtracted(null);
  };

  const handleAddManual = async (data: { name: string; type: string; note: string; latitude?: number | null; longitude?: number | null; google_place_id?: string; google_maps_url?: string; geocode_confidence?: string; source?: string }) => {
    if (tripId) await addPlace(tripId, data);
  };

  const handleDeletePlace = async (placeId: string) => {
    if (tripId) await deletePlace(tripId, placeId);
  };

  const handleUpdatePlace = async (placeId: string, data: Record<string, unknown>) => {
    if (tripId) await updatePlace(tripId, placeId, data);
  };

  if (loading || !currentTrip) {
    return <SkeletonTripDetail />;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          {editingTitle ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={titleInput}
                onChange={(e) => setTitleInput(e.target.value)}
                className="text-xl font-bold text-gray-800 border rounded px-2 py-1"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    if (tripId && titleInput.trim()) {
                      updateTrip(tripId, { name: titleInput.trim() });
                    }
                    setEditingTitle(false);
                  }
                  if (e.key === "Escape") setEditingTitle(false);
                }}
              />
              <button
                onClick={() => {
                  if (tripId && titleInput.trim()) {
                    updateTrip(tripId, { name: titleInput.trim() });
                  }
                  setEditingTitle(false);
                }}
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                Save
              </button>
              <button
                onClick={() => setEditingTitle(false)}
                className="text-gray-400 hover:text-gray-600 text-sm"
              >
                Cancel
              </button>
            </div>
          ) : (
            <h2
              className="text-xl font-bold text-gray-800 cursor-pointer hover:text-blue-600"
              onClick={() => { setTitleInput(currentTrip.name); setEditingTitle(true); }}
              title="Click to edit"
            >
              {currentTrip.name}
            </h2>
          )}
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
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-700">Import from Google Maps</h3>
              <button
                onClick={() => setShowImportHelp(!showImportHelp)}
                className="text-gray-400 hover:text-blue-500 text-xs flex items-center gap-1"
                title="How to export from Google Maps"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                How to export?
              </button>
            </div>
            {showImportHelp && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3 text-xs text-gray-600 space-y-2">
                <p className="font-medium text-gray-700">How to export saved places from Google Maps:</p>
                <ol className="list-decimal list-inside space-y-1.5">
                  <li>Go to <a href="https://takeout.google.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 underline">takeout.google.com</a></li>
                  <li>Click <span className="font-medium">"Deselect all"</span>, then scroll down and check only <span className="font-medium">"Saved"</span></li>
                  <li>Click <span className="font-medium">"Next step"</span>, then <span className="font-medium">"Create export"</span></li>
                  <li>Wait for the export to be ready, then download and unzip</li>
                  <li>Find the CSV files in the <span className="font-mono bg-gray-100 px-1 rounded">Saved/</span> folder</li>
                </ol>
                <p className="text-gray-400 pt-1">Each CSV file represents a list (e.g. "Want to go", "Favorites"). You can upload one or more CSV files below.</p>
              </div>
            )}
            <button
              onClick={() => setShowImportModal(true)}
              className="w-full border-2 border-dashed border-gray-300 rounded-lg p-4 text-gray-500 hover:border-blue-400 hover:text-blue-500 transition-colors text-sm"
            >
              Upload Google Takeout CSV files
            </button>
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
                tripId={tripId!}
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

      {showImportModal && (
        <ImportModal
          tripId={tripId!}
          onClose={() => setShowImportModal(false)}
          onComplete={() => setShowImportModal(false)}
        />
      )}
    </div>
  );
}
