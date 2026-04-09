export interface User {
  user_id: string;
  email: string;
  name: string;
  avatar_url?: string;
}

export interface Trip {
  id: string;
  user_id: string;
  name: string;
  start_date: string;
  end_date: string;
  country_code?: string;
  created_at: string;
}

export interface OpeningPeriod {
  day: number;  // 0=Sunday, 1=Monday, ..., 6=Saturday
  open: string; // "HH:MM"
  close: string; // "HH:MM"
}

export interface Place {
  id: string;
  trip_id: string;
  name: string;
  name_local?: string;
  name_en?: string;
  type: "attraction" | "restaurant" | "hotel" | "other" | "google_saved";
  note: string;
  latitude: number | null;
  longitude: number | null;
  google_place_id?: string;
  google_maps_url?: string;
  opening_hours?: { periods: OpeningPeriod[] } | null;
  geocode_confidence?: "high" | "low" | "none";
  source: "ai_extracted" | "manual" | "google_import";
  day_number: number | null;
  order_in_day: number;
  check_in_day?: number | null;
  check_out_day?: number | null;
}

export interface ExtractedPlace {
  name: string;
  name_local?: string;
  name_en?: string;
  type: string;
  city?: string;
  day_number?: number | null;
  order_in_day?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  google_place_id?: string;
  geocode_confidence?: "high" | "low" | "none";
  opening_hours?: { periods: OpeningPeriod[] } | null;
}

export interface DaySchedule {
  day: number;
  places: { id: string; order: number }[];
}

export interface ExportLink {
  day: number;
  url: string;
  place_count: number;
}

export interface ResolvedPlace {
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  google_place_id: string;
  formatted_address: string;
  google_maps_url: string;
  opening_hours?: { periods: OpeningPeriod[] } | null;
}

export interface ImportedPlace {
  title: string;
  note: string;
  url: string;
  rough_lat: number | null;
  rough_lon: number | null;
  list_name: string;
  nearby: boolean;
  distance_km: number | null;
}

export interface GoogleImportPreviewResponse {
  lists: { name: string; places: ImportedPlace[] }[];
  trip_center: { lat: number; lon: number } | null;
}
