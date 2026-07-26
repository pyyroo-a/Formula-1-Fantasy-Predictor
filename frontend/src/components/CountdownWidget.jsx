import { useState, useEffect } from "react";

// Compact "T-MINUS  DD:HH:MM:SS" clock for the header, matching the pit-wall look.
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

  const pad = (n) => String(n).padStart(2, "0");

  return (
    <div className="flex items-center gap-3">
      <span className="text-[10.5px] tracking-widest text-pw-muted hidden sm:inline">T-MINUS</span>
      {timeLeft ? (
        <span className="text-pw-red font-bold text-[13px] tabular-nums tracking-tight">
          {pad(timeLeft.days)}:{pad(timeLeft.hours)}:{pad(timeLeft.minutes)}:{pad(timeLeft.seconds)}
        </span>
      ) : (
        <span className="text-pw-safe font-bold text-[12px]">LIGHTS OUT</span>
      )}
    </div>
  );
}
