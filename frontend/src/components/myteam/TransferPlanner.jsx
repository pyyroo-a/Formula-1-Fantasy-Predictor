import { useState, useEffect } from "react";
import { API } from "../../api";
import { DRIVER_NAMES } from "../../constants";
import { INPUT_CLS, PRIMARY_BTN_CLS, SECTION_HEAD_CLS } from "../../styles";
import { loadTeams, saveTeams } from "../../plannerTeams";
import { ConfidencePill, ConfidenceReason } from "../BudgetTeam";
import { CONFIDENCE_LEGEND } from "../../confidence";

// The transfer planner (project 3). Put in one of my real teams, budget and free
// transfers, and it shows the ladder: keep the team, or the best team with 1, 2, 3
// free transfers, what each one is expected to score, and why. Facts only, I make the
// call. The maths is in src/planner.py, this page just shows it. It gets its proper
// look in the one redesign at the end.

function rowLabel(row, free) {
  if (row.transfers === 0) return "Keep your team";
  const n = row.transfers === 1 ? "1 transfer" : `${row.transfers} transfers`;
  if (row.paid) return `${n} (one costs -10)`;
  if (row.transfers === free) return free === 1 ? `${n} (your free one)` : free === 2 ? `${n} (both free)` : `${n} (all ${free} free)`;
  return `${n} (free)`;
}

function TeamPicker({ team, prices, onChange }) {
  const drivers = Object.keys(prices?.drivers || {}).sort();
  const constructors = Object.keys(prices?.constructors || {}).sort();
  const set = (field, i, value) => {
    const list = [...team[field]];
    list[i] = value;
    onChange({ ...team, [field]: list });
  };
  // a pick already used in another slot can't be picked twice
  const taken = (field, i, value) => team[field].some((v, j) => j !== i && v === value);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
        {team.drivers.map((d, i) => (
          <select key={i} value={d} onChange={e => set("drivers", i, e.target.value)} className={INPUT_CLS}>
            <option value="">Driver {i + 1}</option>
            {d && !drivers.includes(d) && <option value={d}>{d} (not in the price list)</option>}
            {drivers.map(a => (
              <option key={a} value={a} disabled={taken("drivers", i, a)}>
                {a}{DRIVER_NAMES[a] ? ` ${DRIVER_NAMES[a]}` : ""} ${prices.drivers[a]}M
              </option>
            ))}
          </select>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {team.constructors.map((c, i) => (
          <select key={i} value={c} onChange={e => set("constructors", i, e.target.value)} className={INPUT_CLS}>
            <option value="">Constructor {i + 1}</option>
            {constructors.map(n => (
              <option key={n} value={n} disabled={taken("constructors", i, n)}>{n} ${prices.constructors[n]}M</option>
            ))}
          </select>
        ))}
      </div>
    </div>
  );
}

function Ladder({ data, free }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 bg-pw-panel2 px-3 py-2 border border-white/[0.06]">
        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${data.provisional ? "bg-pw-risk" : "bg-pw-safe"}`} />
        <p className="text-[12px] text-pw-muted">
          {data.provisional
            ? <>Preview from <span className="text-white font-semibold">{data.session_used}</span>, it settles once the weekend locks (FP3, or sprint quali on sprint weekends)</>
            : <>Based on <span className="text-white font-semibold">{data.session_used}</span>, the session this weekend locked on</>}
        </p>
      </div>

      {data.rows.some(r => (r.swaps || []).some(s => s.in_confidence)) && (
        <p className="text-[10.5px] text-pw-muted">{CONFIDENCE_LEGEND}</p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10.5px] text-pw-muted tracking-[0.05em] border-b border-white/10">
              <th className="text-left py-2 pr-3">TRANSFERS</th>
              <th className="text-left py-2 pr-3">CHANGE</th>
              <th className="text-right py-2 pr-3">EXPECTED (WITH YOUR 2X)</th>
              <th className="text-right py-2">VS KEEPING</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map(row => (
              <tr key={row.transfers} className="border-b border-white/[0.06] align-top">
                <td className="py-2 pr-3 text-white whitespace-nowrap">{rowLabel(row, free)}</td>
                <td className="py-2 pr-3">
                  {row.none
                    ? <span className="text-pw-muted">No team fits your budget with this many</span>
                    : row.swaps.length === 0
                      ? <span className="text-pw-muted">No changes, 2x on {row.boost}</span>
                      : <>
                          {row.swaps.map(s => (
                            <div key={`${s.out}-${s.in}`} className="mb-1">
                              <span className="text-white">{s.out} &rarr; {s.in}</span>
                              {s.in_confidence && <> <ConfidencePill level={s.in_confidence} /></>}
                              <p className="text-[11px] text-pw-muted">{s.reason}</p>
                              {s.in_confidence_reason && <ConfidenceReason text={`${s.in}: ${s.in_confidence_reason}`} />}
                            </div>
                          ))}
                          <p className="text-[11px] text-pw-muted">2x on {row.boost}</p>
                        </>}
                </td>
                <td className="py-2 pr-3 text-right text-white font-semibold">{row.none ? "-" : Math.round(row.expected)}</td>
                <td className="py-2 text-right">
                  {row.none || row.transfers === 0 ? "-" : (() => {
                    // whole points first, so this always equals the two numbers on screen
                    const d = Math.round(row.expected) - Math.round(data.rows[0].expected);
                    return `${d >= 0 ? "+" : ""}${d}`;
                  })()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-pw-panel2 border border-white/[0.06] p-3">
        <p className={SECTION_HEAD_CLS}>THE FACTS</p>
        <ul className="space-y-1">
          {data.facts.map(f => <li key={f} className="text-[13px] text-white">{f}</li>)}
        </ul>
        <p className="text-[10.5px] text-pw-muted mt-3">
          Expected points from PitWall's forecast, not a promise. F1 can always surprise.
        </p>
      </div>
    </div>
  );
}

// kept as text while you type, so clearing the box to retype doesn't fight you. it
// snaps back to the last good number when you leave it. keyed by team so switching
// teams starts it fresh
function BudgetInput({ value, onCommit }) {
  const [text, setText] = useState(String(value));
  return (
    <input type="number" step="0.1" min="0" value={text}
      onChange={e => { setText(e.target.value); const n = parseFloat(e.target.value); if (Number.isFinite(n) && n > 0) onCommit(n); }}
      onBlur={() => setText(String(value))}
      className={`${INPUT_CLS} mt-1`} />
  );
}

export default function TransferPlanner({ upcomingRaces }) {
  const [teams, setTeams] = useState(loadTeams);
  const [active, setActive] = useState(0);
  const [prices, setPrices] = useState(null);
  const [race, setRace] = useState("");
  const [ladder, setLadder] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/prices`).then(r => r.json()).then(setPrices).catch(() => setError("Couldn't load the prices."));
  }, []);

  // the next race unless you pick another one
  const raceName = race || upcomingRaces?.[0]?.race_name || "";

  const team = teams[active];
  const update = (next) => {
    const all = teams.map((t, i) => (i === active ? next : t));
    setTeams(all);
    saveTeams(all);
    setLadder(null);
  };

  const complete = team.drivers.every(Boolean) && team.constructors.every(Boolean);

  const showLadder = async () => {
    setLoading(true); setError(null); setLadder(null);
    try {
      const res = await fetch(`${API}/transfer-ladder`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: raceName, drivers: team.drivers, constructors: team.constructors,
                               budget: team.budget, free_transfers: team.freeTransfers }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Check the team, something in it isn't valid.");
      setLadder(data);
    } catch (e) {
      setError(e.message || "Couldn't work out the ladder.");
    }
    setLoading(false);
  };

  return (
    <div>
      <p className="text-pw-muted text-sm text-center mb-4">
        Your real team, your budget, your free transfers. See what keeping it or making each transfer is expected to score.
      </p>

      <div className="grid grid-cols-3 gap-2 mb-4">
        {teams.map((t, i) => (
          <button key={i} onClick={() => { setActive(i); setLadder(null); }}
            className={`p-2 text-sm border ${i === active ? "border-pw-red text-white bg-pw-panel2" : "border-white/10 text-pw-muted"}`}>
            {t.name}
          </button>
        ))}
      </div>

      <div className="bg-pw-panel2 border border-white/[0.06] p-3 space-y-3 mb-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <label className="text-[10.5px] text-pw-muted">TEAM NAME
            <input value={team.name} onChange={e => update({ ...team, name: e.target.value })} className={`${INPUT_CLS} mt-1`} />
          </label>
          <label className="text-[10.5px] text-pw-muted">YOUR BUDGET ($M, team value + bank)
            <BudgetInput key={active} value={team.budget} onCommit={n => update({ ...team, budget: n })} />
          </label>
          <label className="text-[10.5px] text-pw-muted">FREE TRANSFERS THIS WEEK
            <select value={team.freeTransfers} onChange={e => update({ ...team, freeTransfers: Number(e.target.value) })} className={`${INPUT_CLS} mt-1`}>
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3 (you saved one last week)</option>
            </select>
          </label>
        </div>
        {prices ? <TeamPicker team={team} prices={prices} onChange={update} /> : <p className="text-pw-muted text-xs">Loading prices…</p>}
      </div>

      <select value={raceName} onChange={e => { setRace(e.target.value); setLadder(null); }} className={`${INPUT_CLS} mb-3`}>
        {(upcomingRaces || []).map(r => <option key={r.race_name} value={r.race_name}>{r.race_name}{r.is_sprint ? " (sprint)" : ""}</option>)}
      </select>

      <button onClick={showLadder} disabled={!complete || !raceName || loading} className={`${PRIMARY_BTN_CLS} mb-4`}>
        {!complete ? "Pick all 5 drivers and 2 constructors first" : loading ? "Working it out…" : "Show my transfer ladder"}
      </button>

      {loading && <p className="text-pw-muted/60 text-xs text-center mb-4">This can take up to 30 seconds</p>}
      {error && <p className="text-pw-red text-sm text-center mb-4">{error}</p>}
      {ladder && <Ladder data={ladder} free={team.freeTransfers} />}
    </div>
  );
}
