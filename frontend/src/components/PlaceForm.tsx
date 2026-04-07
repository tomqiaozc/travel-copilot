import { useState } from "react";

interface Props {
  onSubmit: (data: { name: string; type: string; note: string }) => void;
}

const TYPES = ["attraction", "restaurant", "hotel", "other"];

export function PlaceForm({ onSubmit }: Props) {
  const [name, setName] = useState("");
  const [type, setType] = useState("attraction");
  const [note, setNote] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name, type, note });
    setName("");
    setNote("");
  };

  return (
    <form onSubmit={handleSubmit} className="border rounded-lg p-4 space-y-3">
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
    </form>
  );
}
