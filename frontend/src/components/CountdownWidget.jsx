import { useState, useEffect } from "react";

// The countdown to the next race in the header, "Race in 3d 02:14:09".
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
    <div className="flex items-baseline gap-2 flex-shrink-0">
      <span className="text-xs text-pw-muted">{timeLeft ? "Race in" : ""}</span>
      {timeLeft ? (
        <span className="cond-x font-bold text-xl text-pw-red num">
          {timeLeft.days}d {pad(timeLeft.hours)}:{pad(timeLeft.minutes)}:{pad(timeLeft.seconds)}
        </span>
      ) : (
        <span className="text-pw-safe font-bold text-sm">Lights out</span>
      )}
    </div>
  );
}
