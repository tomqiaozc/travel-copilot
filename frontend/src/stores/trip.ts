import { create } from "zustand";
import { toast } from "sonner";
import { api } from "../api/client";
import type { Trip, Place, ExtractedPlace, ExportLink, ResolvedPlace, GoogleImportPreviewResponse } from "../types";

interface TripState {
  trips: Trip[];
  currentTrip: Trip | null;
  places: Place[];
  loading: boolean;

  fetchTrips: () => Promise<void>;
  createTrip: (data: { name: string; start_date: string; end_date: string; country_code?: string }) => Promise<Trip>;
  deleteTrip: (id: string) => Promise<void>;
  fetchTripDetail: (id: string) => Promise<void>;
  fetchPlaces: (tripId: string) => Promise<void>;
  addPlace: (tripId: string, data: { name: string; type: string; note: string; name_local?: string; name_en?: string; latitude?: number | null; longitude?: number | null; google_place_id?: string; google_maps_url?: string; geocode_confidence?: string; day_number?: number | null; order_in_day?: number | null; source?: string }) => Promise<void>;
  updatePlace: (tripId: string, placeId: string, data: Record<string, unknown>) => Promise<void>;
  deletePlace: (tripId: string, placeId: string) => Promise<void>;
  reorderPlaces: (tripId: string, placements: { place_id: string; day_number: number | null; order_in_day: number }[]) => Promise<void>;
  extractPlaces: (tripId: string, images: File[]) => Promise<ExtractedPlace[]>;
  updateTrip: (tripId: string, data: Record<string, unknown>) => Promise<void>;
  planTrip: (tripId: string, userPrompt?: string) => Promise<void>;
  exportGoogleMaps: (tripId: string) => Promise<ExportLink[]>;
  resolveGoogleLink: (tripId: string, url: string) => Promise<ResolvedPlace>;
  googleImportPreview: (tripId: string, files: File[]) => Promise<GoogleImportPreviewResponse>;
  googleImportConfirm: (tripId: string, places: { title: string; note: string; url: string }[]) => Promise<void>;
}

export const useTripStore = create<TripState>((set, get) => ({
  trips: [],
  currentTrip: null,
  places: [],
  loading: false,

  fetchTrips: async () => {
    set({ loading: true });
    try {
      const trips = await api.listTrips();
      set({ trips, loading: false });
    } catch (e) {
      toast.error("Failed to load trips");
      set({ loading: false });
      throw e;
    }
  },

  createTrip: async (data) => {
    try {
      const trip = await api.createTrip(data);
      set((s) => ({ trips: [trip, ...s.trips] }));
      return trip;
    } catch (e) {
      toast.error("Failed to create trip");
      throw e;
    }
  },

  deleteTrip: async (id) => {
    try {
      await api.deleteTrip(id);
      set((s) => ({ trips: s.trips.filter((t) => t.id !== id) }));
    } catch (e) {
      toast.error("Failed to delete trip");
      throw e;
    }
  },

  fetchTripDetail: async (id) => {
    set({ loading: true });
    try {
      const [trip, places] = await Promise.all([
        api.getTrip(id),
        api.listPlaces(id),
      ]);
      set({ currentTrip: trip, places, loading: false });
    } catch (e) {
      toast.error("Failed to load trip details");
      set({ loading: false });
      throw e;
    }
  },

  fetchPlaces: async (tripId) => {
    const places = await api.listPlaces(tripId);
    set({ places });
  },

  addPlace: async (tripId, data) => {
    try {
      const place = await api.addPlace(tripId, data);
      set((s) => ({ places: [...s.places, place] }));
    } catch (e) {
      toast.error("Failed to add place");
      throw e;
    }
  },

  updatePlace: async (tripId, placeId, data) => {
    try {
      const updated = await api.updatePlace(tripId, placeId, data);
      set((s) => ({
        places: s.places.map((p) => (p.id === placeId ? updated : p)),
      }));
    } catch (e) {
      toast.error("Failed to update place");
      throw e;
    }
  },

  deletePlace: async (tripId, placeId) => {
    try {
      await api.deletePlace(tripId, placeId);
      set((s) => ({ places: s.places.filter((p) => p.id !== placeId) }));
    } catch (e) {
      toast.error("Failed to delete place");
      throw e;
    }
  },

  reorderPlaces: async (tripId, placements) => {
    const prevPlaces = get().places;
    const placementMap = new Map(placements.map(p => [p.place_id, p]));
    set({
      places: prevPlaces.map(p => {
        const placement = placementMap.get(p.id);
        return placement
          ? { ...p, day_number: placement.day_number, order_in_day: placement.order_in_day }
          : p;
      }),
    });
    try {
      await api.reorderPlaces(tripId, placements);
    } catch {
      set({ places: prevPlaces });
      toast.error("Failed to reorder places");
    }
  },

  extractPlaces: async (tripId, images) => {
    try {
      const result = await api.extractPlaces(tripId, images);
      // Auto-set country_code on trip if AI detected one and trip doesn't have it
      const trip = get().currentTrip;
      if (result.country_code && trip && !trip.country_code) {
        await api.updateTrip(tripId, { country_code: result.country_code });
        set({ currentTrip: { ...trip, country_code: result.country_code } });
      }
      return result.places;
    } catch (e) {
      toast.error("Failed to extract places from images");
      throw e;
    }
  },

  updateTrip: async (tripId, data) => {
    const updated = await api.updateTrip(tripId, data);
    set({ currentTrip: updated });
  },

  planTrip: async (tripId, userPrompt = "") => {
    try {
      await api.planTrip(tripId, userPrompt);
      // Refresh places to get updated day assignments
      await get().fetchPlaces(tripId);
    } catch (e) {
      toast.error("Failed to plan trip");
      throw e;
    }
  },

  exportGoogleMaps: async (tripId) => {
    const result = await api.exportGoogleMaps(tripId);
    return result.links;
  },

  resolveGoogleLink: async (tripId, url) => {
    try {
      return await api.resolveGoogleLink(tripId, url);
    } catch (e) {
      toast.error("Failed to resolve Google Maps link");
      throw e;
    }
  },

  googleImportPreview: async (tripId, files) => {
    try {
      return await api.googleImportPreview(tripId, files);
    } catch (e) {
      toast.error("Failed to preview import");
      throw e;
    }
  },

  googleImportConfirm: async (tripId, places) => {
    try {
      await api.googleImportConfirm(tripId, places);
      await get().fetchPlaces(tripId);
    } catch (e) {
      toast.error("Failed to import places");
      throw e;
    }
  },
}));
