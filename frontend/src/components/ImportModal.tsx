import { useState, useRef } from "react";
import { toast } from "sonner";
import { useTripStore } from "../stores/trip";
import { StepProgress } from "./StepProgress";
import type { ImportedPlace } from "../types";

interface Props {
  tripId: string;
  onClose: () => void;
  onComplete: () => void;
}

const IMPORT_STEPS = [
  { label: "Geocoding places...", duration: 3000 },
  { label: "Computing optimal routes...", duration: 2000 },
  { label: "Creating places...", duration: 2000 },
];

export function ImportModal({ tripId, onClose, onComplete }: Props) {
  const { googleImportPreview, googleImportConfirm } = useTripStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [phase, setPhase] = useState<"upload" | "importing">("upload");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lists, setLists] = useState<{ name: string; places: ImportedPlace[] }[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const placeKey = (listName: string, idx: number) => `${listName}::${idx}`;

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const result = await googleImportPreview(tripId, Array.from(files));
      setLists(result.lists);
      // Pre-check nearby places
      const preSelected = new Set<string>();
      result.lists.forEach((list) => {
        list.places.forEach((place, idx) => {
          if (place.nearby) {
            preSelected.add(placeKey(list.name, idx));
          }
        });
      });
      setSelected(preSelected);
    } catch {
      setError("Failed to parse CSV files. Please check the file format.");
    } finally {
      setLoading(false);
    }
  };

  const togglePlace = (key: string) => {
    const next = new Set(selected);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    setSelected(next);
  };

  const toggleList = (listName: string, places: ImportedPlace[]) => {
    const keys = places.map((_, idx) => placeKey(listName, idx));
    const allSelected = keys.every((k) => selected.has(k));
    const next = new Set(selected);
    if (allSelected) {
      keys.forEach((k) => next.delete(k));
    } else {
      keys.forEach((k) => next.add(k));
    }
    setSelected(next);
  };

  const selectedCount = selected.size;

  const handleImport = async () => {
    const placesToImport: { title: string; note: string; url: string }[] = [];
    lists.forEach((list) => {
      list.places.forEach((place, idx) => {
        if (selected.has(placeKey(list.name, idx))) {
          placesToImport.push({ title: place.title, note: place.note, url: place.url });
        }
      });
    });

    setPhase("importing");
    setError(null);
    try {
      await googleImportConfirm(tripId, placesToImport);
      toast.success("Places imported successfully");
      onComplete();
    } catch {
      setError("Import failed. Please try again.");
      setPhase("upload");
    }
  };

  if (phase === "importing") {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
          <h3 className="font-bold text-gray-800 mb-4">Importing Places</h3>
          <div className="bg-blue-50 rounded-lg p-3">
            <StepProgress steps={IMPORT_STEPS} active={true} />
          </div>
          {error && (
            <div className="mt-3">
              <p className="text-sm text-red-600 mb-2">{error}</p>
              <button
                onClick={handleImport}
                className="w-full bg-blue-600 text-white rounded-lg py-2 text-sm hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] flex flex-col">
        <div className="p-4 border-b flex justify-between items-center">
          <h3 className="font-bold text-gray-800">Import from Google Maps</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            Close
          </button>
        </div>

        <div className="p-4 overflow-y-auto flex-1">
          {/* File input */}
          {lists.length === 0 && (
            <div className="space-y-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                multiple
                onChange={handleFileChange}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                className="w-full border-2 border-dashed border-gray-300 rounded-lg p-8 text-gray-500 hover:border-blue-400 hover:text-blue-500 transition-colors text-sm"
              >
                {loading ? (
                  <div className="flex items-center justify-center gap-2">
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Parsing CSV files...
                  </div>
                ) : (
                  "Click to select CSV files"
                )}
              </button>
            </div>
          )}

          {error && lists.length === 0 && (
            <p className="text-sm text-red-600 mt-2">{error}</p>
          )}

          {/* Place list grouped by list_name */}
          {lists.map((list) => {
            const keys = list.places.map((_, idx) => placeKey(list.name, idx));
            const allSelected = keys.every((k) => selected.has(k));
            return (
              <div key={list.name} className="mb-4">
                <div className="flex justify-between items-center mb-2">
                  <div className="text-xs font-semibold text-gray-500">
                    {list.name} ({list.places.length})
                  </div>
                  <button
                    onClick={() => toggleList(list.name, list.places)}
                    className="text-xs text-blue-500 hover:text-blue-700"
                  >
                    {allSelected ? "Deselect All" : "Select All"}
                  </button>
                </div>
                {list.places.map((place, idx) => {
                  const key = placeKey(list.name, idx);
                  return (
                    <div
                      key={key}
                      className={`border rounded-lg p-3 flex items-start gap-3 mb-2 ${
                        selected.has(key) ? "border-blue-300 bg-blue-50" : "border-gray-200"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selected.has(key)}
                        onChange={() => togglePlace(key)}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm text-gray-800 truncate">
                            {place.title}
                          </span>
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 ${
                              place.nearby
                                ? "bg-green-100 text-green-700"
                                : "bg-gray-100 text-gray-500"
                            }`}
                          >
                            {place.nearby ? "Nearby" : "Far"}
                          </span>
                        </div>
                        {place.note && (
                          <div className="text-xs text-gray-400 mt-0.5 truncate">
                            {place.note}
                          </div>
                        )}
                        {place.distance_km != null && (
                          <div className="text-xs text-gray-400 mt-0.5">
                            {place.distance_km.toFixed(1)} km away
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>

        <div className="p-4 border-t flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border rounded-lg py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          {lists.length > 0 && (
            <button
              onClick={handleImport}
              disabled={selectedCount === 0}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm hover:bg-blue-700 disabled:bg-gray-400"
            >
              Import Selected ({selectedCount})
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
