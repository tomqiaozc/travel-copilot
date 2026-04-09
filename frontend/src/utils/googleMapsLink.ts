import type { Place } from "../types";

/**
 * Build a Google Maps URL using the Maps URLs API format.
 * These URLs automatically open the Google Maps app on iOS/Android
 * when installed, and fall back to the web on desktop.
 * https://developers.google.com/maps/documentation/urls/get-started
 */
export function getGoogleMapsUrl(place: Place): string | null {
  if (place.google_maps_url) {
    return place.google_maps_url;
  }
  if (place.google_place_id) {
    const query = encodeURIComponent(place.name);
    return `https://www.google.com/maps/search/?api=1&query=${query}&query_place_id=${place.google_place_id}`;
  }
  if (place.latitude != null && place.longitude != null) {
    return `https://www.google.com/maps/search/?api=1&query=${place.latitude},${place.longitude}`;
  }
  return null;
}
