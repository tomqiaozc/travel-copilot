import { useState, useMemo } from "react";
import type { ExtractedPlace } from "../types";

interface Props {
  places: ExtractedPlace[];
  onConfirm: (selected: ExtractedPlace[]) => void;
  onClose: () => void;
}

export function ExtractionModal({ places, onConfirm, onClose }: Props) {
  const [selected, setSelected] = useState<Set<number>>(
    new Set(places.map((_, i) => i))
  );
  const [edits, setEdits] = useState<Map<number, ExtractedPlace>>(new Map());

  const toggle = (index: number) => {
    const next = new Set(selected);
    if (next.has(index)) {
      next.delete(index);
    } else {
      next.add(index);
    }
    setSelected(next);
  };

  const editPlace = (index: number, field: string, value: string) => {
    const current = edits.get(index) || { ...places[index] };
    setEdits(new Map(edits.set(index, { ...current, [field]: value })));
  };

  const handleConfirm = () => {
    const result = Array.from(selected).map(
      (i) => edits.get(i) || places[i]
    );
    onConfirm(result);
  };

  // Group places by day_number
  const dayGroups = useMemo(() => {
    const groups = new Map<number | null, { index: number; place: ExtractedPlace }[]>();
    places.forEach((place, index) => {
      const key = place.day_number ?? null;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push({ index, place });
    });
    // Sort day keys: numbered days first (ascending), then null (unassigned)
    const sortedKeys = Array.from(groups.keys()).sort((a, b) => {
      if (a === null) return 1;
      if (b === null) return -1;
      return a - b;
    });
    return sortedKeys.map((key) => ({ dayNumber: key, items: groups.get(key)! }));
  }, [places]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] flex flex-col">
        <div className="p-4 border-b flex justify-between items-center">
          <h3 className="font-bold text-gray-800">
            AI Extracted Places ({places.length})
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            Close
          </button>
        </div>
        <div className="p-4 overflow-y-auto flex-1 space-y-1">
          {dayGroups.map(({ dayNumber, items }) => (
            <div key={dayNumber ?? "unassigned"}>
              <div className="text-xs font-semibold text-gray-500 mt-3 mb-1">
                {dayNumber != null ? `Day ${dayNumber}` : "Unassigned"}
              </div>
              {items.map(({ index }) => {
                const edited = edits.get(index) || places[index];
                const confidence = edited.geocode_confidence || (edited.latitude != null ? "high" : "none");
                const dotColor = confidence === "high" ? "text-green-500" : confidence === "low" ? "text-orange-500" : "text-gray-300";
                const dotTitle = confidence === "high" ? "Geocoded" : confidence === "low" ? "Location uncertain" : "Not geocoded";
                const nameColor = confidence === "low" ? "text-orange-600" : "";
                return (
                  <div
                    key={index}
                    className={`border rounded-lg p-3 flex items-start gap-3 mb-2 ${
                      selected.has(index) ? "border-blue-300 bg-blue-50" : "border-gray-200"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(index)}
                      onChange={() => toggle(index)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`text-[8px] ${dotColor}`}
                          title={dotTitle}
                        >
                          ●
                        </span>
                        <input
                          type="text"
                          value={edited.name}
                          onChange={(e) => editPlace(index, "name", e.target.value)}
                          className={`w-full border-none bg-transparent font-medium text-sm p-0 focus:outline-none ${nameColor}`}
                        />
                      </div>
                      {edited.name_local && (
                        <div className="text-xs text-gray-400 mt-0.5 ml-4">{edited.name_local}</div>
                      )}
                      <select
                        value={edited.type}
                        onChange={(e) => editPlace(index, "type", e.target.value)}
                        className="text-xs text-gray-500 mt-1 ml-4 bg-transparent border-none p-0"
                      >
                        <option value="attraction">attraction</option>
                        <option value="restaurant">restaurant</option>
                        <option value="hotel">hotel</option>
                        <option value="other">other</option>
                      </select>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="p-4 border-t flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border rounded-lg py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm hover:bg-blue-700"
          >
            Add {selected.size} Places
          </button>
        </div>
      </div>
    </div>
  );
}
