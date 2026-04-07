import { useState } from "react";

interface Props {
  onSubmit: (prompt: string) => void;
  onClose: () => void;
  loading: boolean;
}

export function PlanPromptModal({ onSubmit, onClose, loading }: Props) {
  const [prompt, setPrompt] = useState("");

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="font-bold text-gray-800 mb-2">AI Itinerary Planning</h3>
        <p className="text-sm text-gray-500 mb-4">
          Optionally provide instructions to guide the AI planning.
        </p>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Day 1 should be relaxing with fewer places, put all ramen shops at lunchtime..."
          className="w-full border rounded-lg px-3 py-2 text-sm h-24 resize-none mb-4"
        />
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border rounded-lg py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onSubmit(prompt)}
            disabled={loading}
            className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? "Planning..." : "Plan Itinerary"}
          </button>
        </div>
      </div>
    </div>
  );
}
