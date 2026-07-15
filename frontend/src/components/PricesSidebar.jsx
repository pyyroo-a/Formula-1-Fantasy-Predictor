import { DRIVER_NAMES, teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";

function PriceChange({ change }) {
  if (!change || change === 0) return <span className="text-gray-600 text-xs">—</span>;
  if (change > 0) return <span className="text-green-400 text-xs font-medium">+{change.toFixed(1)} ↑</span>;
  return <span className="text-red-400 text-xs font-medium">{change.toFixed(1)} ↓</span>;
}

export default function PricesSidebar({ priceChanges }) {
  if (!priceChanges?.drivers) {
    return (
      <>
        <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-4 mb-3">
          <p className="text-xs text-gray-500 text-center">Loading prices...</p>
        </div>
        <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-4">
          <p className="text-xs text-gray-500 text-center">Loading prices...</p>
        </div>
      </>
    );
  }

  const drivers = Object.entries(priceChanges.drivers)
    .sort(([, a], [, b]) => b.price - a.price)
    .map(([abbr, d]) => ({ abbr, price: d.price, change: d.change }));

  const constructors = Object.entries(priceChanges.constructors || {})
    .sort(([, a], [, b]) => b.price - a.price)
    .map(([name, d]) => ({ name, price: d.price, change: d.change }));

  return (
    <>
      {/* Drivers card */}
      <div className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden mb-3">
        <div className="px-4 py-3 border-b border-gray-700 bg-gray-800/80">
          <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Driver Prices</p>
          <p className="text-xs text-gray-600 mt-0.5">vs last round</p>
        </div>
        <div className="overflow-y-auto no-scrollbar" style={{ maxHeight: "340px" }}>
          <div className="divide-y divide-gray-700/40">
            {drivers.map(({ abbr, price, change }, i) => (
              <div key={abbr} className="flex items-center gap-2.5 px-3 py-2">
                <span className="text-xs text-gray-600 w-4 text-right flex-shrink-0">{i + 1}</span>
                <DriverAvatar abbreviation={abbr} size="sm" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium leading-tight truncate">{DRIVER_NAMES[abbr] || abbr}</p>
                  <PriceChange change={change} />
                </div>
                <p className="text-sm font-bold text-white flex-shrink-0">${price.toFixed(1)}M</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Constructors card */}
      <div className="bg-gray-800/50 rounded-xl border border-gray-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-700 bg-gray-800/80">
          <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Constructor Prices</p>
          <p className="text-xs text-gray-600 mt-0.5">vs last round</p>
        </div>
        <div className="overflow-y-auto no-scrollbar" style={{ maxHeight: "220px" }}>
          <div className="divide-y divide-gray-700/40">
            {constructors.map(({ name, price, change }) => {
              const accent = teamAccent(name);
              return (
                <div key={name} className="flex items-center gap-2 px-3 py-2.5 border-l-4" style={{ borderLeftColor: accent }}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{name}</p>
                    <PriceChange change={change} />
                  </div>
                  <p className="text-sm font-bold text-white flex-shrink-0">${price.toFixed(1)}M</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
