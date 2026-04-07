import { Link } from "react-router-dom";
import type { Trip } from "../types";

interface Props {
  trip: Trip;
  onDelete: (id: string) => void;
}

export function TripCard({ trip, onDelete }: Props) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition">
      <Link to={`/trips/${trip.id}`} className="block">
        <h3 className="font-bold text-gray-800">{trip.name}</h3>
        <p className="text-sm text-gray-500 mt-1">
          {trip.start_date} ~ {trip.end_date}
        </p>
      </Link>
      <div className="flex justify-between items-center mt-3">
        <Link
          to={`/trips/${trip.id}/plan`}
          className="text-sm text-blue-600 hover:underline"
        >
          View Plan
        </Link>
        <button
          onClick={() => onDelete(trip.id)}
          className="text-sm text-red-500 hover:text-red-700"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
