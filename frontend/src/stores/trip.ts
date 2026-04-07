import { create } from "zustand";
import { api } from "../api/client";
import type { Trip, Place, ExtractedPlace, ExportLink } from "../types";

interface TripState {
  trips: Trip[];
  currentTrip: Trip | null;
  places: Place[];
  loading: boolean;

  fetchTrips: () => Promise<void>;
  createTrip: (data: { name: string; start_date: string; end_date: string }) => Promise<Trip>;
  deleteTrip: (id: string) => Promise<void>;
  fetchTripDetail: (id: string) => Promise<void>;
  fetchPlaces: (tripId: string) => Promise<void>;
  addPlace: (tripId: string, data: { name: string; type: string; note: string }) => Promise<void>;
  updatePlace: (tripId: string, placeId: string, data: Record<string, unknown>) => Promise<void>;
  deletePlace: (tripId: string, placeId: string) => Promise<void>;
  extractPlaces: (tripId: string, images: File[]) => Promise<ExtractedPlace[]>;
  planTrip: (tripId: string, userPrompt?: string) => Promise<void>;
  exportGoogleMaps: (tripId: string) => Promise<ExportLink[]>;
}

export const useTripStore = create<TripState>((set, get) => ({
  trips: [],
  currentTrip: null,
  places: [],
  loading: false,

  fetchTrips: async () => {
    set({ loading: true });
    const trips = await api.listTrips();
    set({ trips, loading: false });
  },

  createTrip: async (data) => {
    const trip = await api.createTrip(data);
    set((s) => ({ trips: [trip, ...s.trips] }));
    return trip;
  },

  deleteTrip: async (id) => {
    await api.deleteTrip(id);
    set((s) => ({ trips: s.trips.filter((t) => t.id !== id) }));
  },

  fetchTripDetail: async (id) => {
    set({ loading: true });
    const [trip, places] = await Promise.all([
      api.getTrip(id),
      api.listPlaces(id),
    ]);
    set({ currentTrip: trip, places, loading: false });
  },

  fetchPlaces: async (tripId) => {
    const places = await api.listPlaces(tripId);
    set({ places });
  },

  addPlace: async (tripId, data) => {
    const place = await api.addPlace(tripId, data);
    set((s) => ({ places: [...s.places, place] }));
  },

  updatePlace: async (tripId, placeId, data) => {
    const updated = await api.updatePlace(tripId, placeId, data);
    set((s) => ({
      places: s.places.map((p) => (p.id === placeId ? updated : p)),
    }));
  },

  deletePlace: async (tripId, placeId) => {
    await api.deletePlace(tripId, placeId);
    set((s) => ({ places: s.places.filter((p) => p.id !== placeId) }));
  },

  extractPlaces: async (tripId, images) => {
    const result = await api.extractPlaces(tripId, images);
    return result.places;
  },

  planTrip: async (tripId, userPrompt = "") => {
    await api.planTrip(tripId, userPrompt);
    // Refresh places to get updated day assignments
    await get().fetchPlaces(tripId);
  },

  exportGoogleMaps: async (tripId) => {
    const result = await api.exportGoogleMaps(tripId);
    return result.links;
  },
}));
