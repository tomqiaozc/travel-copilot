import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useTripStore } from "../stores/trip";
import { ImageUploader } from "../components/ImageUploader";
import { PlaceForm } from "../components/PlaceForm";
import { ExtractionModal } from "../components/ExtractionModal";
import type { ExtractedPlace } from "../types";

export function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const {
    currentTrip,
    places,
    loading,
    fetchTripDetail,
    addPlace,
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
      await addPlace(tripId, { name: place.name, type: place.type, note: "" });
    }
    setExtracted(null);
  };

  const handleAddManual = async (data: { name: string; type: string; note: string }) => {
    if (tripId) await addPlace(tripId, data);
  };

  const handleDeletePlace = async (placeId: string) => {
    if (tripId) await deletePlace(tripId, placeId);
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
            <h3 className="font-medium text-gray-700 mb-3">Add Place Manually</h3>
            <PlaceForm onSubmit={handleAddManual} />
          </div>
        </div>

        {/* Right: Place list */}
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <h3 className="font-medium text-gray-700 mb-3">
            Places ({places.length})
          </h3>
          <div className="space-y-2">
            {places.map((place) => (
              <div
                key={place.id}
                className="border rounded-lg p-3 flex justify-between items-start"
              >
                <div>
                  <div className="font-medium text-sm text-gray-800">{place.name}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {place.type}
                    {place.note && ` · ${place.note}`}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    Source: {place.source}
                  </div>
                </div>
                <button
                  onClick={() => handleDeletePlace(place.id)}
                  className="text-red-400 hover:text-red-600 text-sm"
                >
                  Delete
                </button>
              </div>
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
