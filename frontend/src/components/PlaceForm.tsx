import { useState } from "react";
import { useTripStore } from "../stores/trip";

interface Props {
  onSubmit: (data: { name: string; type: string; note: string; latitude?: number | null; longitude?: number | null; google_place_id?: string; google_maps_url?: string; source?: string }) => void;
  tripId: string;
}

const TYPES = ["attraction", "restaurant", "hotel", "other"];

export function PlaceForm({ onSubmit, tripId }: Props) {
  const { resolveGoogleLink } = useTripStore();
  const [mode, setMode] = useState<"url" | "manual">("url");
  const [url, setUrl] = useState("");
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Manual fields
  const [name, setName] = useState("");
  const [type, setType] = useState("attraction");
  const [note, setNote] = useState("");

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setResolving(true);
    setError(null);
    try {
      const resolved = await resolveGoogleLink(tripId, url.trim());
      onSubmit({
        name: resolved.name,
        type: resolved.type,
        note: resolved.formatted_address || "",
        latitude: resolved.latitude,
        longitude: resolved.longitude,
        google_place_id: resolved.google_place_id,
        google_maps_url: resolved.google_maps_url,
        source: "manual",
      });
      setUrl("");
    } catch {
      setError("Could not resolve this link. Try a different URL or add manually.");
    } finally {
      setResolving(false);
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name, type, note });
    setName("");
    setNote("");
  };

  return (
    <div className="space-y-3">
      {mode === "url" ? (
        <form onSubmit={handleUrlSubmit} className="border rounded-lg p-4 space-y-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Google Maps Link</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://maps.app.goo.gl/..."
              className="w-full border rounded px-3 py-2 text-sm"
              required
            />
          </div>
          {error && <p className="text-red-500 text-xs">{error}</p>}
          <button
            type="submit"
            disabled={resolving}
            className="w-full border border-blue-600 text-blue-600 py-2 rounded-lg text-sm hover:bg-blue-50 disabled:opacity-50"
          >
            {resolving ? "Resolving..." : "+ Add from Link"}
          </button>
          <button
            type="button"
            onClick={() => setMode("manual")}
            className="w-full text-gray-400 text-xs hover:text-gray-600"
          >
            Or add manually
          </button>
        </form>
      ) : (
        <form onSubmit={handleManualSubmit} className="border rounded-lg p-4 space-y-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Place Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="e.g. Senso-ji Temple"
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Type</label>
            <div className="flex gap-2">
              {TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setType(t)}
                  className={`px-3 py-1 rounded text-xs border ${
                    type === t
                      ? "bg-blue-100 text-blue-700 border-blue-300"
                      : "bg-white text-gray-600 border-gray-200"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Note</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Go early morning to avoid crowds"
              className="w-full border rounded px-3 py-2 text-sm h-16 resize-none"
            />
          </div>
          <button
            type="submit"
            className="w-full border border-blue-600 text-blue-600 py-2 rounded-lg text-sm hover:bg-blue-50"
          >
            + Add Place
          </button>
          <button
            type="button"
            onClick={() => setMode("url")}
            className="w-full text-gray-400 text-xs hover:text-gray-600"
          >
            Or add from Google Maps link
          </button>
        </form>
      )}
    </div>
  );
}
