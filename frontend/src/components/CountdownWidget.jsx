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
    <div className="text-right">
      <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-0.5">Next Race</p>
      <p className="text-white font-bold text-base leading-tight mb-2">{nextRace.race_name}</p>
      {timeLeft ? (
        <div className="flex items-end gap-3 justify-end">
          {[["D", timeLeft.days], ["H", timeLeft.hours], ["M", timeLeft.minutes], ["S", timeLeft.seconds]].map(([label, val]) => (
            <div key={label} className="text-center">
              <p className="text-3xl font-mono font-black text-red-500 leading-none">{String(val).padStart(2, "0")}</p>
              <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-wider">{label}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-green-400 text-sm font-medium">Race weekend is here!</p>
      )}
    </div>
  );
}
