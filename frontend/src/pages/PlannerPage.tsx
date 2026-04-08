import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { DragDropContext, type DropResult } from "@hello-pangea/dnd";
import { useTripStore } from "../stores/trip";
import { DayGroup } from "../components/DayGroup";
import { TripMap } from "../components/TripMap";
import { PlanPromptModal } from "../components/PlanPromptModal";
import type { Place } from "../types";

const AZURE_MAPS_KEY = import.meta.env.VITE_AZURE_MAPS_KEY || "";

export function PlannerPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const {
    currentTrip,
    places,
    loading,
    fetchTripDetail,
    updatePlace,
    planTrip,
    exportGoogleMaps,
  } = useTripStore();
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  const [exportLinks, setExportLinks] = useState<
    { day: number; url: string }[] | null
  >(null);

  useEffect(() => {
    if (tripId) fetchTripDetail(tripId);
  }, [tripId, fetchTripDetail]);

  const numDays =
    currentTrip
      ? Math.ceil(
          (new Date(currentTrip.end_date).getTime() -
            new Date(currentTrip.start_date).getTime()) /
            86400000
        ) + 1
      : 0;

  // Group places by day
  const dayGroups: Map<number | null, Place[]> = new Map();
  places.forEach((p) => {
    const day = p.day_number;
    if (!dayGroups.has(day)) dayGroups.set(day, []);
    dayGroups.get(day)!.push(p);
  });

  // Sort within each day
  dayGroups.forEach((group) => {
    group.sort((a, b) => a.order_in_day - b.order_in_day);
  });

  const handleDragEnd = async (result: DropResult) => {
    if (!result.destination || !tripId) return;

    const placeId = result.draggableId;
    const destDay = result.destination.droppableId === "unassigned"
      ? null
      : parseInt(result.destination.droppableId.replace("day-", ""));
    const destIndex = result.destination.index;

    await updatePlace(tripId, placeId, {
      day_number: destDay,
      order_in_day: destIndex + 1,
    });
  };

  const handlePlan = async (prompt: string) => {
    if (!tripId) return;
    setPlanning(true);
    setPlanError(null);
    try {
      await planTrip(tripId, prompt);
      setShowPlanModal(false);
    } catch {
      setPlanError("Planning failed. Please try again.");
    } finally {
      setPlanning(false);
    }
  };

  const handleExport = async () => {
    if (!tripId) return;
    const links = await exportGoogleMaps(tripId);
    setExportLinks(links);
  };

  if (loading || !currentTrip) {
    return <div className="text-center py-20 text-gray-500">Loading...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <Link to={`/trips/${tripId}`} className="text-gray-400 hover:text-gray-600">
            &larr;
          </Link>
          <h2 className="text-xl font-bold text-gray-800">
            {currentTrip.name} — Itinerary
          </h2>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowPlanModal(true)}
            className="bg-white border border-blue-600 text-blue-600 px-4 py-2 rounded-lg text-sm hover:bg-blue-50"
          >
            AI Plan
          </button>
          <button
            onClick={handleExport}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
          >
            Export to Google Maps
          </button>
        </div>
      </div>

      <div className="flex gap-4" style={{ height: "calc(100vh - 160px)" }}>
        {/* Left: Itinerary */}
        <div className="w-80 overflow-y-auto flex-shrink-0">
          <DragDropContext onDragEnd={handleDragEnd}>
            {Array.from({ length: numDays }, (_, i) => i + 1).map((day) => (
              <DayGroup
                key={day}
                dayNumber={day}
                places={dayGroups.get(day) || []}
                label={`Day ${day}`}
                onPlaceClick={(p) => setSelectedPlaceId(p.id)}
              />
            ))}
            <DayGroup
              dayNumber={null}
              places={dayGroups.get(null) || []}
              label="Unassigned"
              onPlaceClick={(p) => setSelectedPlaceId(p.id)}
            />
          </DragDropContext>
        </div>

        {/* Right: Map */}
        <div className="flex-1 bg-white rounded-lg shadow-sm overflow-hidden">
          <TripMap places={places} azureMapsKey={AZURE_MAPS_KEY} selectedPlaceId={selectedPlaceId} />
        </div>
      </div>

      {showPlanModal && (
        <PlanPromptModal
          onSubmit={handlePlan}
          onClose={() => setShowPlanModal(false)}
          loading={planning}
          error={planError}
        />
      )}

      {exportLinks && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="font-bold text-gray-800 mb-4">Google Maps Links</h3>
            <div className="space-y-2">
              {exportLinks.map((link) => (
                <a
                  key={link.day}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block border rounded-lg p-3 hover:bg-blue-50 text-sm"
                >
                  <span className="font-medium">Day {link.day}</span>
                  <span className="text-gray-400 ml-2">Open in Google Maps</span>
                </a>
              ))}
            </div>
            <button
              onClick={() => setExportLinks(null)}
              className="mt-4 w-full border rounded-lg py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
