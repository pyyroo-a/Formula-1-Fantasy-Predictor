import { DRIVER_NAMES, teamAccent } from "../constants";

function PriceChange({ change }) {
  if (!change || change === 0) return <span className="text-gray-600 text-xs">—</span>;
  if (change > 0) return <span className="text-green-400 text-xs font-medium">+{change.toFixed(1)} ↑</span>;
  return <span className="text-red-400 text-xs font-medium">{change.toFixed(1)} ↓</span>;
}

export function DriverPricesCard({ priceChanges }) {
  const drivers = priceChanges?.drivers
    ? Object.entries(priceChanges.drivers)
        .sort(([, a], [, b]) => b.price - a.price)
        .map(([abbr, d]) => ({ abbr, price: d.price, change: d.change }))
    : [];

  return (
    <div className="bg-gray-800 rounded-xl overflow-hidden h-full flex flex-col">
      <div className="px-4 pt-4 pb-2 flex-shrink-0">
        <p className="text-sm font-bold text-white">Driver Prices</p>
      </div>
      <div className="overflow-y-auto no-scrollbar flex-1 px-2 pb-3">
        {drivers.length === 0
          ? <p className="text-xs text-gray-500 text-center py-4">Loading...</p>
          : drivers.map(({ abbr, price, change }) => (
            <div key={abbr} className="flex items-center justify-between px-2 py-1.5">
              <div className="flex items-center gap-2 min-w-0">
                <p className="text-sm text-gray-200 truncate">{DRIVER_NAMES[abbr]?.split(" ").slice(-1)[0] || abbr}</p>
                <PriceChange change={change} />
              </div>
              <p className="text-sm font-bold text-white flex-shrink-0">${price.toFixed(1)}M</p>
            </div>
          ))
        }
      </div>
    </div>
  );
}

export function ConstructorPricesCard({ priceChanges }) {
  const constructors = priceChanges?.constructors
    ? Object.entries(priceChanges.constructors)
        .sort(([, a], [, b]) => b.price - a.price)
        .map(([name, d]) => ({ name, price: d.price, change: d.change }))
    : [];

  return (
    <div className="bg-gray-800 rounded-xl overflow-hidden h-full flex flex-col">
      <div className="px-4 pt-4 pb-2 flex-shrink-0">
        <p className="text-sm font-bold text-white">Constructor Prices</p>
      </div>
      <div className="overflow-y-auto no-scrollbar flex-1 px-2 pb-3">
        {constructors.length === 0
          ? <p className="text-xs text-gray-500 text-center py-4">Loading...</p>
          : constructors.map(({ name, price, change }) => {
            const accent = teamAccent(name);
            return (
              <div key={name} className="flex items-center justify-between px-2 py-1.5 border-l-2 ml-2 mb-0.5 rounded-r" style={{ borderLeftColor: accent }}>
                <div className="flex items-center gap-2 min-w-0">
                  <p className="text-sm text-gray-200 truncate">{name}</p>
                  <PriceChange change={change} />
                </div>
                <p className="text-sm font-bold text-white flex-shrink-0">${price.toFixed(1)}M</p>
              </div>
            );
          })
        }
      </div>
    </div>
  );
}

export default function PricesSidebar({ priceChanges }) {
  return (
    <div className="space-y-3">
      <DriverPricesCard priceChanges={priceChanges} />
      <ConstructorPricesCard priceChanges={priceChanges} />
    </div>
  );
}
