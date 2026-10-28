import { useEffect, useState } from "react";
import { API } from "../api";
import { CHIP_META } from "../constants";
import { fetchJson } from "../lib/api";
import Loading, { ErrorLine } from "../ui/Loading";

// Chip history (project 6): what 3x, Limitless and No Negative would really have been
// worth at each track, from the game's official points. Facts to weigh up before a
// race, never "play this now". Reads data/chip_history.json via /chip-history.

const CHIPS = [
  { key: "3x",          label: "3x Boost",    sub: "the top scorer's points", sign: "", color: CHIP_META.x3_boost.color },
  { key: "Limitless",   label: "Limitless",   sub: "extra over the best $100M team", sign: "+", color: CHIP_META.limitless.color },
  { key: "No Negative", label: "No Negative", sub: "what an average team gets back", sign: "", color: CHIP_META.no_negative.color, decimals: true },
];

const OTHER_CHIPS = [
  ["Wildcard", "unlimited free transfers for one weekend, within your budget, and the new team stays. For a stale team, not a track."],
  ["Final Fix", "swap one driver after qualifying. Insurance for a bad quali or a problem."],
  ["Autopilot", "the game gives your 2x to your top scorer after the weekend, so you can't pick the wrong one."],
];

// 3x and Limitless are whole points, No Negative always gets one decimal (31.0 next to 37.8)
const fmt = (v, decimals = false) => (v == null ? "-" : decimals ? v.toFixed(1) : Number.isInteger(v) ? String(v) : v.toFixed(1));
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

// one of the best (or the worst) tracks for a chip, with a little bar against the top one
function BestRow({ label, value, sign, top, color, who, worst = false, decimals = false }) {
  return (
    <div className={`py-1 ${worst ? "mt-1.5 pt-2 border-t border-dashed border-pw-edge text-pw-muted" : ""}`}>
      <div className="flex justify-between gap-2 text-[13px] num">
        <span className="min-w-0 truncate">{worst ? `Worst: ${label}` : label}</span>
        <b className="flex-shrink-0">{sign}{fmt(value, decimals)}</b>
      </div>
      {who && <p className="text-[11px] text-pw-muted">{who}</p>}
      <i className="block h-1 rounded-sm mt-1" style={{ width: `${Math.max(4, (value / top) * 100)}%`, background: worst ? "#3A404C" : color }} />
    </div>
  );
}

export default function ChipHistory() {
  const [res, setRes] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchJson(`${API}/chip-history`).then(r => { if (!cancelled) setRes(r); });
    return () => { cancelled = true; };
  }, []);

  if (!res) return <Loading text="Loading the chip history..." rows={3} />;
  if (!res.ok) return <ErrorLine text={`Couldn't load the chip history. ${res.error}`} />;
  const data = res.data;
  if (!data.tracks?.length) return <p className="text-pw-muted text-sm">No chip history yet.</p>;

  const byTrack = Object.fromEntries(data.tracks.map(t => [t.track, t]));
  const top = chip => new Set((data.best?.[chip]?.top || []).map(t => t.track));
  const tracks = [...data.tracks].sort((a, b) => shortRace(a.name).localeCompare(shortRace(b.name)));
  const whoFor = track => byTrack[track]?.chips?.["3x"]?.values?.slice(-1)[0]?.who;

  return (
    <div>
      <h1 className="cond-x font-extrabold text-[30px] sm:text-[36px] leading-none">Where each chip was worth the most</h1>
      <p className="text-sm text-pw-muted mt-2 mb-4">
        What each chip would really have been worth at every track, from the game's official points.
        Seasons {(data.seasons || []).join(", ")}, so treat it as a hint, not a rule.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {CHIPS.map(c => {
          const best = data.best?.[c.key] || {};
          const topValue = best.top?.[0]?.median || 1;
          return (
            <div key={c.key} className="bg-pw-panel rounded-xl px-3 py-3 border-t-[3px]" style={{ borderTopColor: c.color }}>
              <h3 className="cond font-extrabold text-[17px]">{c.label}</h3>
              <p className="text-xs text-pw-muted mb-1.5">{c.sub}</p>
              {(best.top || []).map(t => (
                <BestRow key={t.track} label={trackLabel(t.name, t.track)} value={t.median} sign={c.sign} top={topValue}
                         color={c.color} decimals={c.decimals} who={c.key === "3x" ? whoFor(t.track) : null} />
              ))}
              {best.worst && (
                <BestRow worst label={trackLabel(best.worst.name, best.worst.track)} value={best.worst.median} sign={c.sign}
                         top={topValue} color={c.color} decimals={c.decimals} who={c.key === "3x" ? whoFor(best.worst.track) : null} />
              )}
              <p className="text-[11px] text-pw-muted mt-2 leading-relaxed">{checkLine(data.check?.[c.key], data.seasons?.length || 1)}</p>
            </div>
          );
        })}
      </div>

      {/* every track as a list, so nothing scrolls sideways on a phone */}
      <h3 className="cond font-bold text-[17px] mt-5 mb-1.5">Every track</h3>
      <div className="bg-pw-panel rounded-xl px-3 py-1">
        {tracks.map(t => (
          <div key={t.track} className="py-2 border-b border-pw-line last:border-0">
            <p className="text-[14px] font-semibold">
              {trackLabel(t.name, t.track)}
              {t.sprint && <span className="text-[11px] text-pw-caution ml-1.5 font-normal">sprint</span>}
            </p>
            <div className="grid grid-cols-3 gap-2 mt-0.5 num">
              {CHIPS.map(c => {
                const cell = t.chips?.[c.key] || {};
                const values = cell.values || [];
                return (
                  <div key={c.key} className="min-w-0">
                    <p className="text-[11px] text-pw-muted truncate">{c.label}</p>
                    <p className={`text-[13px] font-bold ${top(c.key).has(t.track) ? "text-pw-safe" : ""}`}>
                      {cell.median == null ? "-" : `${c.sign}${fmt(cell.median, c.decimals)}`}
                    </p>
                    {/* every season's value, with who for 3x, so a one-off is out in the open */}
                    {values.length > 0 && (cell.seasons > 1 || c.key === "3x") && (
                      <p className="text-[11px] text-pw-muted leading-snug">
                        {values.map(v => `${cell.seasons > 1 ? `${v.season} ${fmt(v.value, c.decimals)} ` : ""}${v.who || ""}`.trim()).join(", ")}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="bg-pw-panel rounded-xl px-3 py-2.5 mt-3 space-y-1">
        {OTHER_CHIPS.map(([name, text]) => (
          <p key={name} className="text-[13px] text-pw-muted"><b className="text-pw-text">{name}</b>: {text}</p>
        ))}
      </div>

      <details className="bg-pw-panel rounded-xl px-3 py-2.5 mt-3 text-[13px] text-[#C3C8D2] leading-relaxed">
        <summary className="font-bold text-pw-text cursor-pointer">How we picked these tracks</summary>
        <p className="mt-2">
          For every track we worked out what the chip would really have been worth there, from the game's official
          points after the race. Then we ranked the tracks from highest to lowest. The top 3 are shown, plus the lowest
          so you know where not to use it. Once there's more than one season, each track uses its middle value across
          seasons, so one wild race can't decide it on its own.
        </p>
        <p className="mt-2">
          The catch: it's one season so far, so we can't check yet if a track that was good for a chip stays good the
          next year. One season also means one weekend per track, so a one-off like a P19 to P1 win can top a list:
          check who scored it. Green in the list = one of the best 3 tracks for that chip. Facts to weigh up, not
          advice. Updated every Monday{data.updated ? ` (last ${data.updated})` : ""}.
        </p>
      </details>
    </div>
  );
}
