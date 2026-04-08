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

export interface Place {
  id: string;
  trip_id: string;
  name: string;
  name_local?: string;
  name_en?: string;
  type: "attraction" | "restaurant" | "hotel" | "other";
  note: string;
  latitude: number | null;
  longitude: number | null;
  source: "ai_extracted" | "manual";
  day_number: number | null;
  order_in_day: number;
}

export interface ExtractedPlace {
  name: string;
  name_local?: string;
  name_en?: string;
  type: string;
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
