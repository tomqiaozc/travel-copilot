function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`bg-gray-200 rounded animate-pulse ${className}`} />;
}

function SkeletonCard() {
  return (
    <div className="border rounded-lg p-3 space-y-2">
      <SkeletonLine className="h-4 w-3/4" />
      <SkeletonLine className="h-3 w-1/2" />
    </div>
  );
}

function SkeletonDayGroup() {
  return (
    <div className="border-l-4 border-gray-200 bg-gray-50 rounded-lg p-3 mb-4">
      <SkeletonLine className="h-4 w-16 mb-3" />
      <div className="space-y-2">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    </div>
  );
}

export function SkeletonTripDetail() {
  return (
    <div className="animate-pulse">
      <div className="flex justify-between items-center mb-6">
        <SkeletonLine className="h-7 w-48" />
        <div className="flex gap-2">
          <SkeletonLine className="h-9 w-20 rounded-lg" />
          <SkeletonLine className="h-9 w-24 rounded-lg" />
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow-sm p-4 space-y-3">
            <SkeletonLine className="h-5 w-32" />
            <SkeletonLine className="h-32 w-full rounded-lg" />
            <SkeletonLine className="h-9 w-full rounded-lg" />
          </div>
          <div className="space-y-3">
            <SkeletonLine className="h-5 w-24" />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <SkeletonLine className="h-[400px] w-full" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonPlannerPage() {
  return (
    <div className="animate-pulse">
      <div className="flex justify-between items-center mb-4">
        <SkeletonLine className="h-7 w-56" />
        <div className="flex gap-2">
          <SkeletonLine className="h-9 w-20 rounded-lg" />
          <SkeletonLine className="h-9 w-24 rounded-lg" />
        </div>
      </div>
      <div className="flex gap-4" style={{ height: "calc(100vh - 160px)" }}>
        <div className="w-80 flex-shrink-0 space-y-4">
          <SkeletonDayGroup />
          <SkeletonDayGroup />
          <SkeletonDayGroup />
        </div>
        <div className="flex-1 bg-gray-100 rounded-lg">
          <SkeletonLine className="h-full w-full rounded-lg" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonTripsPage() {
  return (
    <div className="animate-pulse">
      <div className="flex justify-between items-center mb-6">
        <SkeletonLine className="h-7 w-24" />
        <SkeletonLine className="h-9 w-24 rounded-lg" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow-sm p-4 space-y-3">
            <SkeletonLine className="h-5 w-3/4" />
            <SkeletonLine className="h-4 w-1/2" />
            <SkeletonLine className="h-4 w-2/3" />
          </div>
        ))}
      </div>
    </div>
  );
}
