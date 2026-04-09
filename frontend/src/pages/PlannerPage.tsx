import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { DragDropContext, type DropResult } from "@hello-pangea/dnd";
import { toast } from "sonner";
import { useTripStore } from "../stores/trip";
import { DayGroup } from "../components/DayGroup";
import { TripMap } from "../components/TripMap";
import { PlanPromptModal } from "../components/PlanPromptModal";
import { SkeletonPlannerPage } from "../components/Skeleton";
import { api } from "../api/client";
import { getWeekday, getWeekdayName } from "../utils/openingHours";
import type { Place } from "../types";

const GOOGLE_MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "";

export function PlannerPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const {
    currentTrip,
    places,
    loading,
    fetchTripDetail,
    updatePlace,
    deletePlace,
    reorderPlaces,
    planTrip,
  } = useTripStore();
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);

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

    const srcDay = result.source.droppableId === "unassigned"
      ? null
      : parseInt(result.source.droppableId.replace("day-", ""));
    const destDay = result.destination.droppableId === "unassigned"
      ? null
      : parseInt(result.destination.droppableId.replace("day-", ""));
    const srcIndex = result.source.index;
    const destIndex = result.destination.index;

    if (srcDay === destDay && srcIndex === destIndex) return;

    const srcPlaces = [...(dayGroups.get(srcDay) || [])];
    const destPlaces = srcDay === destDay
      ? srcPlaces
      : [...(dayGroups.get(destDay) || [])];

    const [moved] = srcPlaces.splice(srcIndex, 1);

    if (srcDay === destDay) {
      srcPlaces.splice(destIndex, 0, moved);
    } else {
      destPlaces.splice(destIndex, 0, moved);
    }

    const placements: {
      place_id: string;
      day_number: number | null;
      order_in_day: number;
    }[] = [];

    if (srcDay !== destDay) {
      srcPlaces.forEach((p, i) => {
        placements.push({ place_id: p.id, day_number: srcDay, order_in_day: i + 1 });
      });
    }

    const targetPlaces = srcDay === destDay ? srcPlaces : destPlaces;
    targetPlaces.forEach((p, i) => {
      placements.push({ place_id: p.id, day_number: destDay, order_in_day: i + 1 });
    });

    await reorderPlaces(tripId, placements);
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

  const handleExportKml = async () => {
    if (!tripId) return;
    try {
      const blob = await api.exportKml(tripId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${currentTrip?.name || "trip"}.kml`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("KML file downloaded");
    } catch {
      toast.error("Failed to export KML");
    }
  };

  const handleUpdatePlace = async (placeId: string, data: Record<string, unknown>) => {
    if (tripId) await updatePlace(tripId, placeId, data);
  };

  const handleDeletePlace = async (placeId: string) => {
    if (tripId) await deletePlace(tripId, placeId);
  };

  if (loading || !currentTrip) {
    return <SkeletonPlannerPage />;
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
            onClick={handleExportKml}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
          >
            Export KML
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
                label={`Day ${day} · ${getWeekdayName(getWeekday(currentTrip.start_date, day))}`}
                startDate={currentTrip.start_date}
                onPlaceClick={(p) => setSelectedPlaceId(p.id)}
                tripId={tripId}
                onUpdatePlace={handleUpdatePlace}
                onDeletePlace={handleDeletePlace}
              />
            ))}
            <DayGroup
              dayNumber={null}
              places={dayGroups.get(null) || []}
              label="Unassigned"
              onPlaceClick={(p) => setSelectedPlaceId(p.id)}
              tripId={tripId}
              onUpdatePlace={handleUpdatePlace}
              onDeletePlace={handleDeletePlace}
            />
          </DragDropContext>
        </div>

        {/* Right: Map */}
        <div className="flex-1 bg-white rounded-lg shadow-sm overflow-hidden">
          <TripMap places={places} googleMapsApiKey={GOOGLE_MAPS_KEY} selectedPlaceId={selectedPlaceId} />
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
    </div>
  );
}
