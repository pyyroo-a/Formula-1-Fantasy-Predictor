import { useEffect, useState } from "react";
import { API } from "../api";

// The track record (project 5): what PitWall's locked team 1 really scored each weekend
// vs simple picks anyone could make, in the game's official points. The numbers come
// from data/track_record_2026.json, rebuilt by the Monday job with the scorecard's code.

const PICKS = [
  { key: "FP3 order",      label: "COPY THE FP3 ORDER" },
  { key: "Most expensive", label: "MOST EXPENSIVE" },
  { key: "Crowd",          label: "COPY THE CROWD" },
];

const fmt = v => (v == null ? "-" : Number.isInteger(v) ? String(v) : v.toFixed(1));
const shortRace = name => name.replace(/ Grand Prix$/, "");

function Tile({ label, value, sub, accent }) {
  return (
    <div className="bg-pw-panel2 px-3 py-3 text-center">
      <p className="text-[9.5px] text-pw-muted tracking-[0.05em]">{label}</p>
      {/* averages always get one decimal so 187.0 and 175.2 line up */}
      <p className={`text-lg font-extrabold mt-1 ${accent ? "text-pw-red" : "text-white"}`}>{value == null ? "-" : value.toFixed(1)}</p>
      <p className="text-[9.5px] text-pw-muted mt-0.5">{sub}</p>
    </div>
  );
}

// green = PitWall beat this pick that weekend, amber = it lost, a tie is just white
function cellTone(locked, pick) {
  if (locked == null || pick == null || locked === pick) return "text-white";
  return locked > pick ? "text-pw-safe" : "text-pw-risk";
}

export default function TrackRecord() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/track-record`)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`status ${r.status}`))))
      .then(setData)
      .catch(e => setError(e.message));
  }, []);

  if (error) return <p className="text-pw-red text-xs">Couldn't load the track record ({error}).</p>;
  if (!data) return <p className="text-pw-muted text-xs">Loading the track record...</p>;
  if (!data.rows?.length) return <p className="text-pw-muted text-xs">No locked weekends graded yet.</p>;

  const s = data.summary || {};
  const pw = s["Locked"] || {};
  // crowd only gets a tile once it has races (ownership is saved from Mexico on)
  const tiles = PICKS.filter(p => (s[p.key]?.races || 0) > 0);

  return (
    <div className="space-y-4">
      <p className="text-[10.5px] tracking-[0.05em] text-pw-muted">
        TRACK RECORD · what PitWall's locked team really scored, vs simple picks anyone could make
      </p>

      <div className="pw-hairgrid grid grid-cols-2 sm:grid-cols-4 gap-px border border-white/[0.06] bg-white/[0.06]">
        <Tile label="PITWALL (TEAM 1)" value={pw.avg} sub={`pts per race, ${pw.races} races`} accent />
        {tiles.map(p => (
          <Tile key={p.key} label={p.label} value={s[p.key].avg}
                sub={`PitWall beat it ${s[p.key].beaten} of ${s[p.key].of}`} />
        ))}
        <Tile label="BEST POSSIBLE" value={s["Hindsight best"]?.avg} sub="in hindsight, the ceiling" />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-[11.5px]">
          <thead>
            <tr className="text-[9.5px] text-pw-muted tracking-[0.05em] border-b border-white/10">
              <th className="text-left py-2 pr-2 font-normal">RACE</th>
              <th className="text-right py-2 px-2 font-normal">PITWALL</th>
              <th className="text-right py-2 px-2 font-normal">FP3 ORDER</th>
              <th className="text-right py-2 px-2 font-normal">MOST EXPENSIVE</th>
              <th className="text-right py-2 px-2 font-normal">CROWD</th>
              <th className="text-right py-2 pl-2 font-normal">BEST POSSIBLE</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map(r => {
              const c = r.cells;
              return (
                <tr key={r.round} className="border-b border-white/[0.05]">
                  <td className="py-2 pr-2 text-white whitespace-nowrap">R{r.round} {shortRace(r.race)}</td>
                  <td className="py-2 px-2 text-right text-pw-red font-bold">{fmt(c["Locked"])}</td>
                  {PICKS.map(p => (
                    <td key={p.key} className={`py-2 px-2 text-right ${cellTone(c["Locked"], c[p.key])}`}
                        title={c[p.key] == null ? r.why?.[p.key] : undefined}>
                      {fmt(c[p.key])}
                    </td>
                  ))}
                  <td className="py-2 pl-2 text-right text-pw-muted">{fmt(c["Hindsight best"])}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-[10.5px] text-pw-muted leading-relaxed">
        Green = PitWall beat that pick that weekend, amber = it lost. Every team is at $100M with a
        2x pick, graded with the game's own points. Copy the crowd starts from Mexico, the first lock
        that saved ownership. The locks up to R18 were made before the fixes from 28 Oct, Mexico (R19)
        is the first weekend with them. Updated every Monday after the race{data.updated ? ` (last ${data.updated})` : ""}.
      </p>
    </div>
  );
}
