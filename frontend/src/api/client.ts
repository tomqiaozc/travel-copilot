const API_BASE = "/api";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (resp.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!resp.ok) {
    throw new Error(`API error: ${resp.status}`);
  }

  if (resp.status === 204) {
    return undefined as T;
  }

  return resp.json();
}

export const api = {
  // Auth
  googleAuth: (code: string) =>
    request<{ token: string; user: any }>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  getMe: () => request<any>("/auth/me"),

  // Trips
  listTrips: () => request<any[]>("/trips"),

  createTrip: (data: { name: string; start_date: string; end_date: string }) =>
    request<any>("/trips", { method: "POST", body: JSON.stringify(data) }),

  getTrip: (id: string) => request<any>(`/trips/${id}`),

  deleteTrip: (id: string) =>
    request<void>(`/trips/${id}`, { method: "DELETE" }),

  // Places
  listPlaces: (tripId: string) => request<any[]>(`/trips/${tripId}/places`),

  addPlace: (tripId: string, data: { name: string; type: string; note: string }) =>
    request<any>(`/trips/${tripId}/places`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updatePlace: (tripId: string, placeId: string, data: Record<string, any>) =>
    request<any>(`/trips/${tripId}/places/${placeId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deletePlace: (tripId: string, placeId: string) =>
    request<void>(`/trips/${tripId}/places/${placeId}`, { method: "DELETE" }),

  // AI
  extractPlaces: (tripId: string, images: File[]) => {
    const form = new FormData();
    images.forEach((img) => form.append("images", img));
    return request<{ places: any[] }>(`/trips/${tripId}/extract`, {
      method: "POST",
      body: form,
    });
  },

  planTrip: (tripId: string, userPrompt: string = "") =>
    request<{ schedule: any[] }>(`/trips/${tripId}/plan`, {
      method: "POST",
      body: JSON.stringify({ user_prompt: userPrompt }),
    }),

  // Export
  exportGoogleMaps: (tripId: string) =>
    request<{ links: any[] }>(`/trips/${tripId}/export/google-maps`),
};
