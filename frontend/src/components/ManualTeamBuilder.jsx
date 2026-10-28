import { useState, useEffect } from "react";
import { API } from "../api";
import { BUDGET, CAT_BADGE, DRIVER_NAMES, teamAccent } from "../constants";
import { INPUT_CLS } from "../styles";
import { postJson } from "../lib/api";
import { fmt1, money } from "../lib/format";
import { pickTeam1 } from "../lib/picker";
import TeamPicker from "../ui/TeamPicker";
import Loading, { ErrorLine } from "../ui/Loading";
import SessionSchedule from "./SessionSchedule";

// From 2026 your fantasy team value grows as your drivers get more expensive, so
// most people end up with more than the base 100M. We keep your number in the
// browser because it's personal to you, unlike the locked teams which are shared
// and live in the snapshots. Falls back to 100 if nothing is saved.
function readSavedBudget() {
  try {
    const saved = parseFloat(localStorage.getItem("pitwall_budget"));
    if (Number.isFinite(saved) && saved > 0) return saved;
  } catch { /* blocked storage, just use 100 */ }
  return BUDGET;
}

const CHECK_EVERY_MS = 60000;

// My team > Manual team. Pick your own 5 and 2 from this weekend's practice pool and
// see how it scores. It loads by itself now: no button, it checks if practice exists
// and if not it keeps checking once a minute until FP1 is in.
export default function ManualTeamBuilder({ upcomingRaces, weekendTeam }) {
  const [race, setRace] = useState("");
  const raceName = race || upcomingRaces?.[0]?.race_name || "";
  const isSprint = upcomingRaces.find(r => r.race_name === raceName)?.is_sprint ?? false;

  const [status, setStatus] = useState("checking"); // checking | waiting | loading | ready | error
  const [sessions, setSessions] = useState(null);
  const [pool, setPool] = useState(null);
  const [optimalTeam, setOptimalTeam] = useState(null);
  const [sessionUsed, setSessionUsed] = useState(null);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);

  const [pickedDrivers, setPickedDrivers] = useState([]);
  const [pickedConstructors, setPickedConstructors] = useState([]);
  const [sort, setSort] = useState("team");

  // check the sessions, and if practice has run load the pool straight away. Same
  // request as the old "Load driver pool" button: FP3, FP1 on sprint weekends
  useEffect(() => {
    if (!raceName) return;
    let cancelled = false;
    (async () => {
      const s = await postJson(`${API}/race-sessions`, { race_name: raceName });
      if (cancelled) return;
      const list = s.ok ? s.data.sessions : null;
      setSessions(list);
      const practiceIn = list?.some(x => ["FP1", "FP2", "FP3"].includes(x.name) && x.available);
      if (list && !practiceIn) { setStatus("waiting"); return; }
      setStatus("loading");
      const p = await postJson(`${API}/upcoming-race-pool`, { year: 2026, race_name: raceName, session: isSprint ? "FP1" : "FP3" });
      if (cancelled) return;
      if (!p.ok) { setError(p.error); setStatus("error"); return; }
      setPool(p.data.pool);
      setSessionUsed(p.data.session_used);
      setOptimalTeam(p.data.optimal || null);
      setStatus("ready");
    })();
    return () => { cancelled = true; };
  }, [raceName, isSprint, tick]);

  // before FP1, look again once a minute
  useEffect(() => {
    if (status !== "waiting") return;
    const id = setInterval(() => setTick(t => t + 1), CHECK_EVERY_MS);
    return () => clearInterval(id);
  }, [status]);

  const changeRace = (name) => {
    setRace(name);
    setPool(null); setOptimalTeam(null); setSessionUsed(null); setSessions(null);
    setPickedDrivers([]); setPickedConstructors([]); setError(null); setStatus("checking");
  };

  const [budget, setBudget] = useState(readSavedBudget);
  // kept as text as well, so you can clear the box and type without it fighting you
  const [budgetText, setBudgetText] = useState(() => String(readSavedBudget()));
  const onBudgetChange = (text) => {
    setBudgetText(text);
    const n = parseFloat(text);
    if (Number.isFinite(n) && n > 0) {
      setBudget(n);
      try { localStorage.setItem("pitwall_budget", String(n)); } catch { /* it just won't remember */ }
    }
  };

  const toggleDriver = (code) => {
    const d = pool.drivers.find(x => x.Abbreviation === code);
    setPickedDrivers(prev => prev.some(x => x.Abbreviation === code) ? prev.filter(x => x.Abbreviation !== code)
      : prev.length < 5 ? [...prev, d] : prev);
  };
  const toggleConstructor = (name) => {
    const c = pool.constructors.find(x => x.name === name);
    setPickedConstructors(prev => prev.some(x => x.name === name) ? prev.filter(x => x.name !== name)
      : prev.length < 2 ? [...prev, c] : prev);
  };
  const startFromTeam1 = () => {
    const t = pickTeam1(weekendTeam, pool);
    setPickedDrivers(t.drivers);
    setPickedConstructors(t.constructors);
  };

  // the same maths as before the redesign
  const totalCost = pickedDrivers.reduce((s, d) => s + d.Price, 0) + pickedConstructors.reduce((s, c) => s + c.price, 0);
  const remaining = budget - totalCost;
  const overBudget = totalCost > budget;
  const teamComplete = pickedDrivers.length === 5 && pickedConstructors.length === 2;
  const myScore = pickedDrivers.reduce((s, d) => s + d.FantasyValue, 0) + pickedConstructors.reduce((s, c) => s + c.score, 0);
  const scoreVsOptimal = optimalTeam ? Math.round((myScore / optimalTeam.total_score) * 100) : null;
  const qualityColor = !teamComplete ? "text-pw-muted"
    : scoreVsOptimal >= 90 ? "text-pw-safe" : scoreVsOptimal >= 70 ? "text-pw-caution" : "text-pw-low";
  const qualityLabel = !teamComplete ? "-"
    : scoreVsOptimal >= 90 ? "Excellent" : scoreVsOptimal >= 70 ? "Good" : scoreVsOptimal >= 50 ? "Average" : "Weak";
  const budgetPct = Math.min((totalCost / budget) * 100, 100);
  const barColor = overBudget ? "bg-pw-low" : budgetPct > 90 ? "bg-pw-caution" : "bg-pw-safe";
  const withScore = pickedDrivers.filter(d => d.FantasyValue != null && !isNaN(d.FantasyValue));
  const boostCode = withScore.length ? withScore.reduce((best, d) => d.FantasyValue > best.FantasyValue ? d : best).Abbreviation : null;
  const categoryCounts = pickedDrivers.reduce((acc, d) => { acc[d.PickCategory] = (acc[d.PickCategory] || 0) + 1; return acc; }, {});
  const canStartFromTeam1 = pool && weekendTeam?.race_name === raceName && (weekendTeam?.teams?.length || weekendTeam?.team);

  const moneyLine = (
    <div className="flex justify-between text-[13px] num">
      <span className="text-pw-muted">Spent <b className={overBudget ? "text-pw-low" : "text-pw-text"}>{money(totalCost)}</b></span>
      <span className="text-pw-muted">Left <b className={overBudget ? "text-pw-low" : "text-pw-safe"}>{overBudget ? `-${money(totalCost - budget)}` : money(remaining)}</b></span>
    </div>
  );

  return (
    <div className="pb-14 sm:pb-0">
      <div className="flex flex-wrap items-end gap-2.5 mb-3">
        <label className="flex-1 min-w-[180px] text-xs text-pw-muted">Race
          <select value={raceName} onChange={e => changeRace(e.target.value)} className={`${INPUT_CLS} mt-1`}>
            {upcomingRaces.map(r => <option key={r.race_name} value={r.race_name}>{r.race_name}{r.is_sprint ? " (sprint)" : ""}</option>)}
          </select>
        </label>
        <label className="w-32 text-xs text-pw-muted">Your budget ($M)
          <input id="pitwall-budget" type="number" step="0.1" min="0" value={budgetText}
            onChange={e => onBudgetChange(e.target.value)} onBlur={() => setBudgetText(String(budget))}
            className={`${INPUT_CLS} mt-1 num`} />
        </label>
        {canStartFromTeam1 && (
          <button onClick={startFromTeam1} className="px-3 py-2 text-sm rounded-lg border border-pw-edge hover:border-pw-muted">
            Start from PitWall Team 1
          </button>
        )}
      </div>

      {isSprint && <p className="text-pw-caution text-[13px] mb-2">Sprint weekend, so it uses FP1.</p>}
      {sessions && status !== "ready" && <SessionSchedule sessions={sessions} />}

      {status === "checking" && <Loading text="Checking if practice has happened..." rows={2} />}
      {status === "waiting" && (
        <p className="text-sm text-pw-muted bg-pw-panel rounded-lg px-3 py-2.5 my-3">
          No practice yet for {raceName}. This fills in by itself after FP1.
        </p>
      )}
      {status === "loading" && <Loading text="Loading the drivers, please wait. The free server can take up to 30 seconds to wake up." rows={4} />}
      {status === "error" && <ErrorLine text={error} />}

      {status === "ready" && pool && (
        <>
          {sessionUsed && <p className="text-xs text-pw-muted mb-3">Points from <b className="text-pw-text">{sessionUsed}</b> practice.</p>}
          <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-4 items-start">
            <TeamPicker
              drivers={pool.drivers}
              constructors={pool.constructors}
              picked={{ drivers: pickedDrivers.map(d => d.Abbreviation), constructors: pickedConstructors.map(c => c.name) }}
              onToggleDriver={toggleDriver}
              onToggleConstructor={toggleConstructor}
              sort={sort}
              onSort={setSort}
            />

            <aside className="lg:sticky lg:top-4 bg-pw-panel rounded-xl px-3.5 py-3">
              <div className="flex items-baseline justify-between mb-1">
                <h3 className="cond font-bold text-[17px]">Your team</h3>
                <span className="text-xs text-pw-muted num">{pickedDrivers.length}/5 drivers, {pickedConstructors.length}/2 constructors</span>
              </div>
              {moneyLine}
              <div className="h-1.5 bg-pw-edge rounded-full overflow-hidden my-2">
                <div className={`h-full transition-all ${barColor}`} style={{ width: `${budgetPct}%` }} />
              </div>
              {overBudget && <p className="text-pw-low text-xs mb-2">Over budget, take a pick out to fix it.</p>}

              {pickedDrivers.map(d => (
                <div key={d.Abbreviation} className="flex items-center gap-2 py-1.5 border-b border-pw-line text-[13px]">
                  <span className="w-1 h-5 rounded-sm" style={{ background: teamAccent(d.TeamName) }} />
                  <span className="flex-1 min-w-0 truncate cond font-semibold text-[15px]">
                    {DRIVER_NAMES[d.Abbreviation] || d.Abbreviation}
                    {d.Abbreviation === boostCode && <span className="ml-1.5 text-[10px] font-extrabold bg-pw-red text-pw-bg px-1 rounded">2x</span>}
                  </span>
                  <span className="text-pw-muted num">{money(d.Price)}</span>
                  <button onClick={() => toggleDriver(d.Abbreviation)} aria-label={`Take out ${d.Abbreviation}`} className="text-pw-muted hover:text-pw-low px-1">✕</button>
                </div>
              ))}
              {Array.from({ length: 5 - pickedDrivers.length }, (_, i) => (
                <p key={`d${i}`} className="py-1.5 border-b border-dashed border-pw-edge text-[13px] text-pw-muted/70">Pick a driver</p>
              ))}
              {pickedConstructors.map(c => (
                <div key={c.name} className="flex items-center gap-2 py-1.5 border-b border-pw-line text-[13px]">
                  <span className="w-1 h-5 rounded-sm" style={{ background: teamAccent(c.name) }} />
                  <span className="flex-1 min-w-0 truncate cond font-semibold text-[15px]">{c.name}</span>
                  <span className="text-pw-muted num">{money(c.price)}</span>
                  <button onClick={() => toggleConstructor(c.name)} aria-label={`Take out ${c.name}`} className="text-pw-muted hover:text-pw-low px-1">✕</button>
                </div>
              ))}
              {Array.from({ length: 2 - pickedConstructors.length }, (_, i) => (
                <p key={`c${i}`} className="py-1.5 border-b border-dashed border-pw-edge text-[13px] text-pw-muted/70">Pick a constructor</p>
              ))}

              <div className="grid grid-cols-3 gap-2 mt-3 text-center">
                <div className="bg-pw-raised rounded-lg py-2"><p className="text-xs text-pw-muted">Your points</p><p className="cond-x font-extrabold text-xl num">{teamComplete ? fmt1(myScore) : "-"}</p></div>
                <div className="bg-pw-raised rounded-lg py-2"><p className="text-xs text-pw-muted">vs PitWall's best</p><p className={`cond-x font-extrabold text-xl num ${qualityColor}`}>{teamComplete && scoreVsOptimal != null ? `${scoreVsOptimal}%` : "-"}</p></div>
                <div className="bg-pw-raised rounded-lg py-2"><p className="text-xs text-pw-muted">Rating</p><p className={`cond-x font-extrabold text-xl ${qualityColor}`}>{qualityLabel}</p></div>
              </div>
              {teamComplete && optimalTeam && (
                <p className="text-xs text-pw-muted text-center mt-2 num">PitWall's best: {fmt1(optimalTeam.total_score)} pts for {money(optimalTeam.total_cost)}</p>
              )}
              {teamComplete && (
                <div className="flex justify-center gap-1.5 mt-2 flex-wrap">
                  {Object.entries(categoryCounts).map(([cat, n]) => (
                    <span key={cat} className={`text-[11px] px-1.5 rounded ${CAT_BADGE[cat] || "text-pw-muted bg-white/5"}`}>{n}x {cat}</span>
                  ))}
                </div>
              )}
            </aside>
          </div>

          {/* on a phone the team panel is far down the page, so the money and counts ride along at the bottom */}
          <div className="lg:hidden fixed bottom-[45px] sm:bottom-0 inset-x-0 z-20 bg-pw-panel border-t border-pw-edge px-4 py-2">
            <div className="flex justify-between items-center gap-3 text-xs text-pw-muted num">
              <span><b className="text-pw-text">{pickedDrivers.length}/5</b> drivers, <b className="text-pw-text">{pickedConstructors.length}/2</b> constructors</span>
              <span>Left <b className={overBudget ? "text-pw-low" : "text-pw-safe"}>{overBudget ? `-${money(totalCost - budget)}` : money(remaining)}</b></span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
