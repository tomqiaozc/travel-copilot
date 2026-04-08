import type { Place } from "../types";

export function getGoogleMapsUrl(place: Place): string | null {
  if (place.google_maps_url) {
    return place.google_maps_url;
  }
  if (place.google_place_id) {
    return `https://www.google.com/maps/place/?q=place_id:${place.google_place_id}`;
  }
  if (place.latitude != null && place.longitude != null) {
    // Use place name in the query so Google Maps shows the actual place info,
    // not just a pin at coordinates
    const query = encodeURIComponent(place.name);
    return `https://www.google.com/maps/search/?api=1&query=${query}&query_place_id=&center=${place.latitude},${place.longitude}`;
  }
  return null;
}
