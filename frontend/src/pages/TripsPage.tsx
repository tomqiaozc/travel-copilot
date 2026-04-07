import { useEffect, useState } from "react";
import { useTripStore } from "../stores/trip";
import { TripCard } from "../components/TripCard";

export function TripsPage() {
  const { trips, loading, fetchTrips, createTrip, deleteTrip } = useTripStore();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    fetchTrips();
  }, [fetchTrips]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await createTrip({ name, start_date: startDate, end_date: endDate });
    setName("");
    setStartDate("");
    setEndDate("");
    setShowForm(false);
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this trip?")) {
      await deleteTrip(id);
    }
  };

  if (loading) {
    return <div className="text-center py-20 text-gray-500">Loading...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold text-gray-800">My Trips</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
        >
          + New Trip
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white p-4 rounded-lg shadow mb-6 space-y-3">
          <input
            type="text"
            placeholder="Trip name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full border rounded-lg px-3 py-2 text-sm"
          />
          <div className="flex gap-3">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
              className="flex-1 border rounded-lg px-3 py-2 text-sm"
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
              className="flex-1 border rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm">
            Create
          </button>
        </form>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {trips.map((trip) => (
          <TripCard key={trip.id} trip={trip} onDelete={handleDelete} />
        ))}
      </div>

      {trips.length === 0 && (
        <div className="text-center py-20 text-gray-400">
          No trips yet. Create your first trip!
        </div>
      )}
    </div>
  );
}
