import { useState, useEffect } from "react";

export default function CountdownWidget({ nextRace }) {
  const [timeLeft, setTimeLeft] = useState(null);

  useEffect(() => {
    if (!nextRace?.race_date) return;
    const tick = () => {
      const diff = new Date(nextRace.race_date) - new Date();
      if (diff <= 0) { setTimeLeft(null); return; }
      setTimeLeft({
        days:    Math.floor(diff / 86400000),
        hours:   Math.floor((diff % 86400000) / 3600000),
        minutes: Math.floor((diff % 3600000) / 60000),
        seconds: Math.floor((diff % 60000) / 1000),
      });
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [nextRace]);

  if (!nextRace) return null;

  return (
    <div className="flex items-center justify-between bg-gray-800 rounded-xl px-5 py-4 border border-gray-700 mb-6">
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Next Race</p>
        <p className="text-white font-bold text-lg leading-tight">{nextRace.race_name}</p>
      </div>
      {timeLeft ? (
        <div className="flex gap-5 flex-shrink-0">
          {[["Days", timeLeft.days], ["Hours", timeLeft.hours], ["Mins", timeLeft.minutes], ["Secs", timeLeft.seconds]].map(([label, val]) => (
            <div key={label} className="text-center">
              <p className="text-2xl font-mono font-black text-red-500">{String(val).padStart(2, "0")}</p>
              <p className="text-xs text-gray-500 mt-0.5 uppercase tracking-wide">{label}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-green-400 text-sm font-medium">Race weekend is here!</p>
      )}
    </div>
  );
}
