import type { Place } from "../types";

export function getGoogleMapsUrl(place: Place): string | null {
  if (place.google_maps_url) {
    return place.google_maps_url;
  }
  if (place.google_place_id) {
    return `https://www.google.com/maps/place/?q=place_id:${place.google_place_id}`;
  }
  if (place.latitude != null && place.longitude != null) {
    const query = encodeURIComponent(place.name);
    return `https://www.google.com/maps/search/${query}`;
  }
  return null;
}
