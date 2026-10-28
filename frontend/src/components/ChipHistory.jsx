import { useEffect, useState } from "react";
import { API } from "../api";

// Chip history (project 6): what 3x, Limitless and No Negative would really have been
// worth at each track, from the game's official points. Facts to weigh up before a
// race, never "play this now". Reads data/chip_history.json via /chip-history.

const CHIPS = [
  { key: "3x",          label: "3X",          sub: "top scorer's points", sign: "" },
  { key: "Limitless",   label: "LIMITLESS",   sub: "extra over the best $100M team", sign: "+" },
  { key: "No Negative", label: "NO NEGATIVE", sub: "an average team gets back", sign: "" },
];

const OTHER_CHIPS = [
  ["Wildcard", "unlimited free transfers for one weekend, within your budget, and the new team stays. For a stale team, not a track."],
  ["Final Fix", "swap one driver after qualifying. Insurance for a bad quali or a problem."],
  ["Autopilot", "the game gives your 2x to your top scorer after the weekend, so you can't pick the wrong one."],
];

const fmt = v => (v == null ? "-" : Number.isInteger(v) ? String(v) : v.toFixed(1));
const shortRace = name => (name || "").replace(/ Grand Prix$/, "");
// "Bahrain (Kuala Lumpur)": the race name alone can't tell two tracks apart
const trackLabel = (name, track) => (shortRace(name) === track ? track : `${shortRace(name)} (${track})`);

function checkLine(check, seasons) {
  if (!check || check.spearman == null) {
    return `${seasons} season so far. Whether a track's past predicts its future gets tested once there are two seasons.`;
  }
  const weak = check.spearman < 0.3;
  return `Last season's best 5 vs this season's: ${check.top5_hits} of 5 repeated (rank correlation ${check.spearman}).`
    + (weak ? " Track history hasn't predicted much so far." : "");
}

export default function ChipHistory() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/chip-history`)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`status ${r.status}`))))
      .then(setData)
      .catch(e => setError(e.message));
  }, []);

  if (error) return <p className="text-pw-red text-xs">Couldn't load the chip history ({error}).</p>;
  if (!data) return <p className="text-pw-muted text-xs">Loading the chip history...</p>;
  if (!data.tracks?.length) return <p className="text-pw-muted text-xs">No chip history yet.</p>;

  const byTrack = Object.fromEntries(data.tracks.map(t => [t.track, t]));
  const top = chip => new Set((data.best?.[chip]?.top || []).map(t => t.track));
  const tracks = [...data.tracks].sort((a, b) => shortRace(a.name).localeCompare(shortRace(b.name)));

  return (
    <div className="space-y-4">
      <p className="text-[10.5px] tracking-[0.05em] text-pw-muted">
        CHIP HISTORY · what each chip would really have been worth at each track
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {CHIPS.map(c => {
          const best = data.best?.[c.key] || {};
          return (
            <div key={c.key} className="bg-pw-panel2 border border-white/[0.06] p-3">
              <p className="text-[10.5px] text-white font-bold tracking-[0.05em]">BEST FOR {c.label}</p>
              <p className="text-[9.5px] text-pw-muted mb-2">{c.sub}</p>
              <ol className="space-y-1 text-[11.5px]">
                {(best.top || []).map((t, i) => {
                  const who = c.key === "3x" ? byTrack[t.track]?.chips?.["3x"]?.values?.slice(-1)[0]?.who : null;
                  return (
                    <li key={t.track} className="text-white">
                      {i + 1}. {trackLabel(t.name, t.track)} <span className="text-pw-safe">{c.sign}{fmt(t.median)}</span>
                      {who && <span className="block text-[10px] text-pw-muted pl-3">{who}</span>}
                    </li>
                  );
                })}
              </ol>
              {best.worst && (
                <p className="text-[10.5px] text-pw-muted mt-2">
                  Worst: {trackLabel(best.worst.name, best.worst.track)} {c.sign}{fmt(best.worst.median)}
                </p>
              )}
              <p className="text-[10px] text-pw-muted mt-2 leading-relaxed">
                {checkLine(data.check?.[c.key], data.seasons?.length || 1)}
              </p>
            </div>
          );
        })}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-[11.5px]">
          <thead>
            <tr className="text-[9.5px] text-pw-muted tracking-[0.05em] border-b border-white/10">
              <th className="text-left py-2 pr-2 font-normal">TRACK</th>
              {CHIPS.map(c => <th key={c.key} className="text-right py-2 px-2 font-normal">{c.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {tracks.map(t => (
              <tr key={t.track} className="border-b border-white/[0.05] align-top">
                <td className="py-2 pr-2 text-white whitespace-nowrap">
                  {trackLabel(t.name, t.track)}
                  {t.sprint && <span className="text-[9.5px] text-pw-risk ml-1.5">sprint</span>}
                </td>
                {CHIPS.map(c => {
                  const cell = t.chips?.[c.key] || {};
                  const values = cell.values || [];
                  return (
                    <td key={c.key} className={`py-2 px-2 text-right ${top(c.key).has(t.track) ? "text-pw-safe" : "text-white"}`}>
                      {cell.median == null ? "-" : `${c.sign}${fmt(cell.median)}`}
                      {/* every season's value, with who for 3x, so a one-off is out in the open */}
                      {values.length > 0 && (cell.seasons > 1 || c.key === "3x") && (
                        <span className="block text-[10px] text-pw-muted whitespace-nowrap">
                          {values.map(v => `${v.season}${cell.seasons > 1 ? ` ${fmt(v.value)}` : ""}${v.who ? ` ${v.who}` : ""}`).join(" · ")}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-pw-panel2 border border-white/[0.06] p-3 space-y-1">
        {OTHER_CHIPS.map(([name, text]) => (
          <p key={name} className="text-[11px] text-pw-muted"><span className="text-white font-bold">{name}</span>: {text}</p>
        ))}
      </div>

      <p className="text-[10.5px] text-pw-muted leading-relaxed">
        Best possible picks, graded with the game's own official points, so seasons {(data.seasons || []).join(", ")} only.
        Green = one of the best 3 tracks for that chip. One season means one weekend per track, so a one-off like a
        P19 to P1 win can top a list: check who scored it. Facts to weigh up, not advice. Updated every Monday
        {data.updated ? ` (last ${data.updated})` : ""}.
      </p>
    </div>
  );
}
