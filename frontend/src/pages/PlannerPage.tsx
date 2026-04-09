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
  const [mobileTab, setMobileTab] = useState<"list" | "map">("list");

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

  // Group places by day, with hotel virtual expansion
  const dayGroups: Map<number | null, Place[]> = new Map();
  places.forEach((p) => {
    if (p.type === "hotel" && p.check_in_day != null && p.check_out_day != null) {
      // Hotel appears in each day from check_in to check_out
      for (let d = p.check_in_day; d <= p.check_out_day; d++) {
        if (!dayGroups.has(d)) dayGroups.set(d, []);
        dayGroups.get(d)!.push(p);
      }
    } else {
      const day = p.day_number;
      if (!dayGroups.has(day)) dayGroups.set(day, []);
      dayGroups.get(day)!.push(p);
    }
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

    // Hotel drag: update check_in/check_out instead of reorder
    if (moved.type === "hotel") {
      const prevNights = moved.check_in_day != null
        ? (moved.check_out_day ?? moved.check_in_day + 1) - moved.check_in_day
        : 1; // default 1 night for first-time assignment
      await updatePlace(tripId, moved.id, {
        check_in_day: destDay,
        check_out_day: destDay != null ? destDay + prevNights : null,
        day_number: destDay,
      });
      return;
    }

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
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <Link to={`/trips/${tripId}`} className="text-gray-400 hover:text-gray-600 flex-shrink-0">
            &larr;
          </Link>
          <h2 className="text-lg sm:text-xl font-bold text-gray-800 truncate">
            {currentTrip.name}
            <span className="hidden sm:inline"> — Itinerary</span>
          </h2>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <button
            onClick={() => setShowPlanModal(true)}
            className="bg-white border border-blue-600 text-blue-600 px-3 sm:px-4 py-2 rounded-lg text-sm hover:bg-blue-50"
          >
            <span className="sm:hidden">AI</span>
            <span className="hidden sm:inline">AI Plan</span>
          </button>
          <button
            onClick={handleExportKml}
            className="bg-blue-600 text-white px-3 sm:px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
          >
            <span className="sm:hidden">KML</span>
            <span className="hidden sm:inline">Export KML</span>
          </button>
        </div>
      </div>

      {/* Mobile tab bar */}
      <div className="flex md:hidden mb-3 bg-gray-100 rounded-lg p-1">
        <button
          onClick={() => setMobileTab("list")}
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
            mobileTab === "list"
              ? "bg-white text-blue-600 shadow-sm"
              : "text-gray-500"
          }`}
        >
          Itinerary
        </button>
        <button
          onClick={() => setMobileTab("map")}
          className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
            mobileTab === "map"
              ? "bg-white text-blue-600 shadow-sm"
              : "text-gray-500"
          }`}
        >
          Map
        </button>
      </div>

      {/* Desktop: side-by-side / Mobile: tab-switched */}
      <div className="md:flex md:gap-4 md:h-[calc(100vh-160px)]">
        {/* Itinerary list */}
        <div className={`md:w-80 md:overflow-y-auto md:flex-shrink-0 overflow-y-auto h-[calc(100vh-220px)] ${
          mobileTab !== "list" ? "hidden md:block" : ""
        }`}>
          <DragDropContext onDragEnd={handleDragEnd}>
            {Array.from({ length: numDays }, (_, i) => i + 1).map((day) => (
              <DayGroup
                key={day}
                dayNumber={day}
                places={dayGroups.get(day) || []}
                label={`Day ${day} · ${getWeekdayName(getWeekday(currentTrip.start_date, day))}`}
                startDate={currentTrip.start_date}
                onPlaceClick={(p) => { setSelectedPlaceId(p.id); setMobileTab("map"); }}
                tripId={tripId}
                onUpdatePlace={handleUpdatePlace}
                onDeletePlace={handleDeletePlace}
              />
            ))}
            <DayGroup
              dayNumber={null}
              places={dayGroups.get(null) || []}
              label="Unassigned"
              onPlaceClick={(p) => { setSelectedPlaceId(p.id); setMobileTab("map"); }}
              tripId={tripId}
              onUpdatePlace={handleUpdatePlace}
              onDeletePlace={handleDeletePlace}
            />
          </DragDropContext>
        </div>

        {/* Map */}
        <div className={`flex-1 bg-white rounded-lg shadow-sm overflow-hidden h-[calc(100vh-220px)] ${
          mobileTab !== "map" ? "hidden md:block" : ""
        }`}>
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
