import { useEffect, useReducer, useState } from "react";
import { API } from "../api";
import { fetchJson } from "../lib/api";
import { fmt1 } from "../lib/format";
import { raceVerdict, honestLine, dotX, chartMax, pointsText, nextOpenDot } from "../lib/insights";
import Loading, { ErrorLine } from "../ui/Loading";

// The track record (project 5): what PitWall's locked team 1 really scored each weekend
// vs simple picks anyone could make, in the game's official points. The numbers come
// from data/track_record_2026.json, rebuilt by the Monday job with the scorecard's code.
// Colours checked for colourblind eyes on the panel colour (dataviz validator).

const SERIES = [
  { key: "Locked",         label: "PitWall",           color: "#F0504F" },
  { key: "FP3 order",      label: "Copy the FP3 order", color: "#5B8DEF" },
  { key: "Most expensive", label: "Most expensive team", color: "#B08A22" },
  { key: "Crowd",          label: "Copy the crowd",    color: "#A274E0" },
];
const shortRace = name => name.replace(/ Grand Prix$/, " GP");

// the little bubble above a dot: who it is, their points, and the best possible. Near
// the ends of the line it hangs inwards so it never gets cut off on a phone
function Bubble({ s, value, best, x }) {
  const side = x < 18 ? "left-0" : x > 82 ? "right-0" : "left-1/2 -translate-x-1/2";
  const arrow = x < 18 ? "left-1.5" : x > 82 ? "right-1.5" : "left-1/2 -translate-x-1/2";
  return (
    <span role="tooltip" className={`absolute bottom-full mb-2.5 ${side} z-20 pointer-events-none whitespace-nowrap rounded-lg bg-pw-text text-pw-bg px-2.5 py-1.5 shadow-lg text-left`}>
      <span className="flex items-center gap-1.5 text-xs font-bold"><i className="w-2 h-2 rounded-full" style={{ background: s.color }} />{s.label}</span>
      <span className="block cond-x font-extrabold text-lg leading-tight num">{pointsText(value)} pts</span>
      {best != null && <span className="block text-[11px] text-pw-bg/70 num">best possible {pointsText(best)}</span>}
      <span className={`absolute top-full ${arrow} w-0 h-0 border-x-[6px] border-x-transparent border-t-[6px] border-t-pw-text`} />
    </span>
  );
}

function Dot({ id, s, value, best, max, open, dispatch }) {
  if (value == null) return null;
  const x = dotX(value, max);
  return (
    <span data-dot className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2" style={{ left: `${x}%`, zIndex: open ? 20 : undefined }}>
      <button
        onPointerEnter={e => dispatch({ type: "enter", id, pointer: e.pointerType })}
        onPointerLeave={e => dispatch({ type: "leave", id, pointer: e.pointerType })}
        // a finger or pen taps, a mouse just hovers. detail 0 = Enter or Space on a keyboard
        onPointerUp={e => { if (e.pointerType !== "mouse") dispatch({ type: "tap", id }); }}
        onClick={e => { if (e.detail === 0) dispatch({ type: "tap", id }); }}
        aria-label={`${s.label}: ${pointsText(value)}`}
        aria-expanded={open}
        className={`relative block w-3 h-3 rounded-full shadow-[0_0_0_2px_#141821] ${open ? "ring-2 ring-pw-text" : ""}`}
        style={{ background: s.color }}
      >
        {/* a bigger invisible target so a thumb can hit it */}
        <span className="absolute -inset-2" />
      </button>
      {open && <Bubble s={s} value={value} best={best} x={x} />}
    </span>
  );
}

function RaceLine({ row, series, max, openDot, dispatch }) {
  const c = row.cells;
  const v = raceVerdict(c);
  const shown = series.map(s => c[s.key]).filter(x => x != null);
  const lo = Math.min(...shown);
  const best = c["Hindsight best"];
  return (
    <div className="py-2 border-b border-pw-line last:border-0">
      <div className="flex justify-between gap-2 text-[13px] mb-1.5 sm:mb-0">
        <span>R{row.round} {shortRace(row.race)}</span>
        <span className={`sm:hidden text-xs font-bold ${v.won ? "text-pw-safe" : v.won === false ? "text-pw-caution" : "text-pw-muted"}`}>{v.text}</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="relative flex-1 h-5">
          {best != null && <span className="absolute top-1/2 h-0.5 bg-pw-edge" style={{ left: `${dotX(lo, max)}%`, width: `${dotX(best, max) - dotX(lo, max)}%` }} />}
          {best != null && <span className="absolute top-0 h-full w-0.5 bg-pw-muted -translate-x-1/2" title={`Best possible: ${pointsText(best)}`} style={{ left: `${dotX(best, max)}%` }} />}
          {/* PitWall last so it sits on top when two dots land on the same spot */}
          {[...series].reverse().map(s => {
            const id = `R${row.round}|${s.key}`;
            return <Dot key={s.key} id={id} s={s} value={c[s.key]} best={best} max={max} open={openDot === id} dispatch={dispatch} />;
          })}
        </div>
        <span className={`hidden sm:block w-40 text-right text-xs font-bold ${v.won ? "text-pw-safe" : v.won === false ? "text-pw-caution" : "text-pw-muted"}`}>{v.text}</span>
      </div>
    </div>
  );
}

export default function TrackRecord() {
  const [res, setRes] = useState(null);
  const [table, setTable] = useState(false);
  // one open bubble for the whole chart, see nextOpenDot
  const [openDot, dispatch] = useReducer(nextOpenDot, null);

  // on a phone, tapping anywhere that isn't a dot closes the bubble
  useEffect(() => {
    if (!openDot) return;
    const close = e => { if (!e.target.closest?.("[data-dot]")) dispatch({ type: "outside" }); };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [openDot]);

  useEffect(() => {
    let cancelled = false;
    fetchJson(`${API}/track-record`).then(r => { if (!cancelled) setRes(r); });
    return () => { cancelled = true; };
  }, []);

  if (!res) return <Loading text="Loading the track record..." rows={4} />;
  if (!res.ok) return <ErrorLine text={`Couldn't load the track record. ${res.error}`} />;
  const data = res.data;
  if (!data.rows?.length) return <p className="text-pw-muted text-sm">No locked weekends graded yet.</p>;

  const s = data.summary || {};
  // crowd only shows once it has races (ownership is saved from Mexico on)
  const series = SERIES.filter(x => x.key === "Locked" || (s[x.key]?.races || 0) > 0);
  const picks = series.filter(x => x.key !== "Locked");
  const max = chartMax(data.rows);

  return (
    <div>
      <h1 className="cond-x font-extrabold text-[30px] sm:text-[36px] leading-none">How PitWall's locked teams really did</h1>
      <p className="text-sm text-[#C3C8D2] mt-2 mb-4 max-w-[68ch] leading-relaxed">
        Graded with the game's own points, every team at $100M with a 2x pick.{" "}
        {honestLine(s)} The locks up to R18 were made before the fixes from 28 Oct, Mexico (R19) is the first
        weekend with them.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4 num">
        {series.map(x => (
          <div key={x.key} className="bg-pw-panel rounded-xl px-3 py-2.5">
            <p className="flex items-center gap-1.5 text-xs text-pw-muted"><i className="w-2.5 h-2.5 rounded-full" style={{ background: x.color }} />{x.label}</p>
            <p className="cond-x font-extrabold text-[28px] leading-tight">{fmt1(s[x.key]?.avg)}</p>
            <p className="text-xs text-pw-muted">
              {x.key === "Locked" ? `pts a race, ${s.Locked?.races} races` : `PitWall beat it ${s[x.key].beaten} of ${s[x.key].of}`}
            </p>
          </div>
        ))}
        <div className="bg-pw-panel rounded-xl px-3 py-2.5">
          <p className="flex items-center gap-1.5 text-xs text-pw-muted"><i className="w-0.5 h-3 bg-pw-muted" />Best possible</p>
          <p className="cond-x font-extrabold text-[28px] leading-tight">{fmt1(s["Hindsight best"]?.avg)}</p>
          <p className="text-xs text-pw-muted">only known after the race</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-pw-muted">
          {series.map(x => <span key={x.key} className="inline-flex items-center gap-1"><i className="w-2.5 h-2.5 rounded-full" style={{ background: x.color }} />{x.label}</span>)}
          <span className="inline-flex items-center gap-1"><i className="w-0.5 h-3 bg-pw-muted" />Best possible</span>
          <span>Tap a dot for its number</span>
        </div>
        <button onClick={() => setTable(!table)} className="text-xs underline text-pw-muted hover:text-pw-text">{table ? "Show as a chart" : "Show as a table"}</button>
      </div>

      {table ? (
        <div className="bg-pw-panel rounded-xl px-3 py-2 overflow-x-auto">
          <table className="w-full text-[13px] num">
            <thead>
              <tr className="text-xs text-pw-muted border-b border-pw-edge">
                <th className="text-left py-1.5 font-normal">Race</th>
                {series.map(x => <th key={x.key} className="text-right py-1.5 px-1.5 font-normal">{x.label.replace("Copy the ", "").replace(" team", "")}</th>)}
                <th className="text-right py-1.5 pl-1.5 font-normal">Best</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map(r => (
                <tr key={r.round} className="border-b border-pw-line last:border-0">
                  <td className="py-1.5 whitespace-nowrap">R{r.round} {shortRace(r.race)}</td>
                  {series.map(x => (
                    <td key={x.key} className={`text-right py-1.5 px-1.5 ${x.key === "Locked" ? "text-pw-red font-bold" : ""}`} title={r.cells[x.key] == null ? r.why?.[x.key] : undefined}>
                      {pointsText(r.cells[x.key])}
                    </td>
                  ))}
                  <td className="text-right py-1.5 pl-1.5 text-pw-muted">{pointsText(r.cells["Hindsight best"])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-pw-panel rounded-xl px-3.5 py-1">
          {data.rows.map(r => <RaceLine key={r.round} row={r} series={series} max={max} openDot={openDot} dispatch={dispatch} />)}
          <div className="flex justify-between text-[11px] text-pw-muted py-1.5 sm:mr-[172px] num">
            {[0, 1, 2, 3].map(i => <span key={i}>{Math.round((max / 3) * i)}{i === 3 ? " pts" : ""}</span>)}
          </div>
        </div>
      )}

      <p className="text-xs text-pw-muted leading-relaxed mt-3">
        {picks.some(p => p.key === "Crowd") ? "" : "Copy the crowd shows from Mexico on, the first lock that saved ownership. "}
        The result on each line compares PitWall with copying the FP3 order. Updated every Monday after the
        race{data.updated ? ` (last ${data.updated})` : ""}.
      </p>
    </div>
  );
}
