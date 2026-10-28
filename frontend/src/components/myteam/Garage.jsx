import { useState, useEffect } from "react";
import { API } from "../../api";
import { CHIP_META, DRIVER_NAMES, teamAccent } from "../../constants";
import { INPUT_CLS } from "../../styles";
import { fetchJson, postJson } from "../../lib/api";
import { fmt1, money, surname } from "../../lib/format";
import { ladderSteps, stepLabel, isComplete, driverTeamMap, chipOrder } from "../../lib/garage";
import { loadTeams, saveTeams } from "../../plannerTeams";
import VerdictTag from "../../ui/VerdictTag";
import Loading, { ErrorLine } from "../../ui/Loading";
import { ConfidencePill, ConfidenceReason } from "../../ui/Confidence";
import GarageEditor from "./GarageEditor";

// My team > Garage. Your real F1 Fantasy teams, put in once (saved in this browser as
// pitwall_planner_teams, same as the old planner, so they carried over). For the team
// you pick it shows the transfer ladder (project 3) and the chips (the old Chip
// Advisor) together. The maths is all the backend's, this just asks and lays it out.

const CHECK_EVERY_MS = 60000;
const isEmpty = t => !t.drivers.some(Boolean) && !t.constructors.some(Boolean);
const swapName = (s, code) => (s.kind === "constructor" ? code : surname(code));

function chipLine(key, chip) {
  switch (key) {
    case "x3_boost": return chip.target ? `On ${DRIVER_NAMES[chip.target] || chip.target} instead of the 2x` : CHIP_META[key].desc;
    case "final_fix": return chip.riskiest_driver ? `Decide after qualifying. Your riskiest driver is ${surname(chip.riskiest_driver)}.` : "Decide after qualifying.";
    case "autopilot": return "Save it, PitWall already picks your 2x.";
    default: return chip.reason || CHIP_META[key]?.desc;
  }
}

function chipNumber(key, chip) {
  if (chip.gain == null) return null;
  return key === "no_negative" ? `${fmt1(chip.gain)} pts at risk` : `+${fmt1(chip.gain)} pts`;
}

function Swaps({ row }) {
  if (row.none) return <p className="text-[13px] text-pw-muted">No team fits your budget with this many.</p>;
  if (!row.swaps?.length) return <p className="text-[13px] text-pw-muted">No changes, 2x on {surname(row.boost)}.</p>;
  return (
    <div>
      {row.swaps.map(s => (
        <div key={`${s.out}-${s.in}`} className="mb-1.5">
          <p className="text-[14px]">
            <b className="cond text-pw-low">{swapName(s, s.out)}</b> out, <b className="cond text-pw-safe">{swapName(s, s.in)}</b> in
            {s.in_confidence && <span className="ml-2"><ConfidencePill level={s.in_confidence} /></span>}
          </p>
          <p className="text-xs text-pw-muted">{s.reason}</p>
          {s.in_confidence_reason && <ConfidenceReason text={`${swapName(s, s.in)}: ${s.in_confidence_reason}`} />}
        </div>
      ))}
      <p className="text-xs text-pw-muted">2x on {surname(row.boost)}</p>
    </div>
  );
}

function Ladder({ data, free }) {
  const steps = ladderSteps(data.rows);
  const [picked, setPicked] = useState(steps.findIndex(s => s.best));
  return (
    <section>
      <h3 className="cond-x font-extrabold text-2xl">Should you make transfers?</h3>
      <p className="text-xs text-pw-muted mb-3">
        You have {free} free transfer{free === 1 ? "" : "s"}. Expected points with your 2x,{" "}
        {data.provisional
          ? `a preview from ${data.session_used}, it settles once the weekend locks.`
          : `from ${data.session_used}, the session this weekend locked on.`}
      </p>
      <div className="grid gap-2 items-end num" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
        {steps.map((s, i) => {
          const { label, sub } = stepLabel(data.rows[i], free);
          return (
            <button key={s.transfers} onClick={() => setPicked(i)} className="text-left flex flex-col min-w-0" aria-pressed={picked === i}>
              <div
                className={`rounded-t-lg flex justify-center pt-1.5 ${s.best ? "bg-pw-red text-pw-bg" : "bg-pw-raised"} ${picked === i ? "ring-2 ring-pw-text/60" : ""}`}
                style={{ height: `${Math.round(s.height * 120)}px` }}
              >
                <span className="cond-x font-extrabold text-3xl">{s.none ? "-" : s.expected}</span>
              </div>
              <span className="text-[13px] font-bold mt-1.5 truncate">{label}</span>
              <span className="text-xs text-pw-muted truncate">{s.none ? "no team fits" : sub}</span>
              {s.vsKeep != null && <span className={`text-xs font-bold ${s.vsKeep >= 0 ? "text-pw-safe" : "text-pw-low"}`}>{s.vsKeep >= 0 ? "+" : ""}{s.vsKeep} vs keeping</span>}
            </button>
          );
        })}
      </div>

      {/* desktop: every option's swaps. phone: just the step you tapped */}
      <div className="hidden sm:block mt-4 border-t border-pw-edge">
        {data.rows.slice(1).map(row => (
          <div key={row.transfers} className="grid grid-cols-[130px_1fr] gap-3 py-2.5 border-b border-pw-line">
            <span className="text-xs text-pw-muted">With {stepLabel(row, free).label}</span>
            <Swaps row={row} />
          </div>
        ))}
      </div>
      <div className="sm:hidden mt-4 border-t border-pw-edge pt-2.5">
        <p className="text-xs text-pw-muted mb-1">{picked === 0 ? "Keeping your team" : `With ${stepLabel(data.rows[picked], free).label}`}, tap a step to see another</p>
        <Swaps row={data.rows[picked]} />
      </div>

      <div className="bg-pw-panel rounded-lg px-3 py-2.5 mt-3 text-[13px] leading-relaxed">
        {data.facts.map(f => <p key={f}>{f}</p>)}
        <p className="text-xs text-pw-muted mt-2">Expected points from PitWall's forecast, not a promise. F1 can always surprise.</p>
      </div>
    </section>
  );
}

function Chips({ data }) {
  return (
    <section>
      <h3 className="cond-x font-extrabold text-2xl">Chips for this team</h3>
      <p className="text-xs text-pw-muted mb-3">Best first. Points are on top of your team as it is ({fmt1(data.my_team_score)} before the 2x).</p>
      {chipOrder(data.chips).map(([key, chip]) => {
        const meta = CHIP_META[key];
        const n = chipNumber(key, chip);
        return (
          <div key={key} className="bg-pw-panel rounded-lg border-l-[3px] px-3 py-2 mb-2" style={{ borderColor: meta.color }}>
            <div className="flex items-center justify-between gap-2">
              <b className="cond text-[16px]">{meta.label}</b>
              <VerdictTag rec={chip.recommendation} />
            </div>
            <p className="text-xs text-pw-muted mt-0.5">{chipLine(key, chip)}</p>
            {n && <p className="text-[13px] font-bold text-pw-safe text-right num">{n}</p>}
          </div>
        );
      })}
    </section>
  );
}

// asks for the ladder and the chips for one complete team. Before practice the server
// says so (a 400 about practice), then it checks again once a minute
function Results({ team, raceName }) {
  const key = JSON.stringify([raceName, team.drivers, team.constructors, team.budget, team.freeTransfers]);
  const [res, setRes] = useState({ key: null });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [ladder, chips] = await Promise.all([
        postJson(`${API}/transfer-ladder`, { race_name: raceName, drivers: team.drivers, constructors: team.constructors,
                                             budget: team.budget, free_transfers: team.freeTransfers }),
        postJson(`${API}/chip-advisor`, { race_name: raceName, my_drivers: team.drivers, my_constructors: team.constructors }),
      ]);
      if (cancelled) return;
      const err = !ladder.ok ? ladder.error : !chips.ok ? chips.error : null;
      setRes({ key, ladder: ladder.ok ? ladder.data : null, chips: chips.ok ? chips.data : null,
               error: err, waiting: !!err && /practice/i.test(err) });
    })();
    return () => { cancelled = true; };
  // key covers everything about the team and race
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, tick]);

  useEffect(() => {
    if (!res.waiting) return;
    const id = setInterval(() => setTick(t => t + 1), CHECK_EVERY_MS);
    return () => clearInterval(id);
  }, [res.waiting]);

  if (res.key !== key) return <Loading text={`Working out your transfers and chips for ${raceName}. The free server can take up to 30 seconds to wake up.`} rows={4} />;
  if (res.waiting) return <p className="text-sm text-pw-muted bg-pw-panel rounded-lg px-3 py-2.5 my-3">No practice yet for {raceName}. This fills in by itself after FP1.</p>;
  if (res.error && !res.ladder && !res.chips) return <ErrorLine text={res.error} />;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.35fr_1fr] gap-6 mt-4">
      {res.ladder ? <Ladder key={key} data={res.ladder} free={team.freeTransfers} /> : <ErrorLine text={res.error} />}
      {res.chips ? <Chips data={res.chips} /> : <ErrorLine text={res.error} />}
    </div>
  );
}

function TeamCard({ team, prices, teamMap }) {
  return (
    <div className="bg-pw-panel rounded-xl px-3.5 py-3 flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap gap-1.5">
        {team.drivers.map(c => (
          <span key={c} className="flex items-center gap-1.5 bg-pw-raised rounded-md pl-1.5 pr-2 py-1 cond font-bold text-[14px]">
            <i className="w-1 h-4 rounded-sm" style={{ background: teamMap[c] ? teamAccent(teamMap[c]) : "#5A6170" }} />{surname(c)}
            {!(c in (prices?.drivers || {})) && prices && <small className="font-normal text-pw-low">not in the price list</small>}
          </span>
        ))}
        {team.constructors.map(n => (
          <span key={n} className="flex items-center gap-1.5 bg-pw-raised rounded-md pl-1.5 pr-2 py-1 cond font-bold text-[14px]">
            <i className="w-1 h-4 rounded-sm" style={{ background: teamAccent(n) }} />{n}
            {!(n in (prices?.constructors || {})) && prices && <small className="font-normal text-pw-low">not in the price list</small>}
          </span>
        ))}
      </div>
      <div className="flex gap-5 text-right num">
        <div><p className="text-xs text-pw-muted">Budget</p><p className="cond-x font-extrabold text-xl">{money(team.budget)}</p></div>
        <div><p className="text-xs text-pw-muted">Free transfers this week</p><p className="cond-x font-extrabold text-xl">{team.freeTransfers}</p></div>
      </div>
    </div>
  );
}

export default function Garage({ upcomingRaces, finishes }) {
  const [teams, setTeams] = useState(loadTeams);
  const [active, setActive] = useState(() => Math.max(0, loadTeams().findIndex(isComplete)));
  const [editing, setEditing] = useState(false);
  const [prices, setPrices] = useState(null);
  const [pricesError, setPricesError] = useState(null);
  const [race, setRace] = useState("");
  const raceName = race || upcomingRaces?.[0]?.race_name || "";

  useEffect(() => {
    let cancelled = false;
    fetchJson(`${API}/prices`).then(r => {
      if (cancelled) return;
      if (r.ok) setPrices(r.data); else setPricesError(r.error);
    });
    return () => { cancelled = true; };
  }, []);

  const team = teams[active];
  const allEmpty = teams.every(isEmpty);

  const save = (next) => {
    const all = teams.map((t, i) => (i === active ? next : t));
    setTeams(all);
    saveTeams(all);
    setEditing(false);
  };

  if (editing) {
    if (!prices) return pricesError ? <ErrorLine text={pricesError} /> : <Loading text="Loading the price list..." rows={3} />;
    return <GarageEditor key={active} team={team} prices={prices} teamMap={driverTeamMap(finishes)} onSave={save} onCancel={() => setEditing(false)} />;
  }

  return (
    <div>
      {allEmpty && (
        <div className="mb-4">
          <h2 className="cond-x font-extrabold text-3xl">Add your F1 Fantasy teams</h2>
          <p className="text-sm text-pw-muted max-w-[60ch] mt-1">
            Put in the teams you really have in the game, once. Then every week this page tells you which transfers
            are worth it and which chip to play. Saved on this device only.
          </p>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 mb-3">
        {teams.map((t, i) => (
          <button
            key={i}
            onClick={() => { setActive(i); if (isEmpty(t)) setEditing(true); }}
            className={`rounded-lg px-3 py-2 text-left min-w-0 ${i === active && !allEmpty ? "bg-pw-red text-pw-bg" : isEmpty(t) ? "border-[1.5px] border-dashed border-pw-edge text-pw-muted" : "bg-pw-raised text-pw-muted hover:text-pw-text"}`}
          >
            <span className="block font-bold text-sm truncate">{t.name}</span>
            <span className="block text-xs truncate">{isEmpty(t) ? "Add team" : isComplete(t) ? `${t.freeTransfers} free transfer${t.freeTransfers === 1 ? "" : "s"}` : "not finished"}</span>
          </button>
        ))}
      </div>

      {!isEmpty(team) && (
        <>
          <div className="flex flex-wrap items-end gap-2.5 mb-3">
            <label className="flex-1 min-w-[180px] text-xs text-pw-muted">Race
              <select value={raceName} onChange={e => setRace(e.target.value)} className={`${INPUT_CLS} mt-1`}>
                {(upcomingRaces || []).map(r => <option key={r.race_name} value={r.race_name}>{r.race_name}{r.is_sprint ? " (sprint)" : ""}</option>)}
              </select>
            </label>
            <button onClick={() => setEditing(true)} className="px-3 py-2 text-sm rounded-lg border border-pw-edge hover:border-pw-muted">Edit this team</button>
          </div>
          <TeamCard team={team} prices={prices} teamMap={driverTeamMap(finishes)} />
          {isComplete(team) && raceName
            ? <Results team={team} raceName={raceName} />
            : <p className="text-sm text-pw-muted my-3">This team isn't finished yet. Tap "Edit this team" to pick all 5 drivers and 2 constructors.</p>}
        </>
      )}
    </div>
  );
}
