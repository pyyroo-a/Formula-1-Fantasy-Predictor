import { DRIVER_NAMES, teamAccent } from "../constants";
import WeatherWidget from "./WeatherWidget";
import AutoChipAdvisor from "./AutoChipAdvisor";
import RiskTag from "../ui/RiskTag";
import { displayCategory } from "../confidence";
import { fmt1, money, pts, surname } from "../lib/format";
import { showConfidenceKey, finishLine } from "../lib/overview";
import Switcher from "../ui/Switcher";
import TowerRow from "../ui/TowerRow";
import StatBox from "../ui/StatBox";
import Panel from "../ui/Panel";
import { ConfidencePill, ConfidenceKey, ConfidenceReason } from "../ui/Confidence";

const CAT_TAG = {
  Safe:  "text-pw-safe bg-pw-safe/10",
  Value: "text-pw-info bg-pw-info/10",
  Risk:  "text-pw-caution bg-pw-caution/10",
  Avoid: "text-pw-low bg-pw-low/10",
  // a Safe driver with low confidence, see displayCategory. outlined so it doesn't look like Risk
  Consider: "text-pw-caution bg-pw-caution/10 ring-1 ring-pw-caution/60",
};

function CategoryTag({ category }) {
  if (!category) return null;
  return <span className={`text-[11px] font-semibold px-1.5 rounded ${CAT_TAG[category] || "text-pw-muted bg-white/5"}`}>{category}</span>;
}

// Green up / red down price move vs the previous round. Nothing when unchanged.
function PriceDelta({ change }) {
  if (!change) return null;
  const up = change > 0;
  return <span className={`text-[11px] ${up ? "text-pw-safe" : "text-pw-low"}`}>{up ? "▲" : "▼"}{Math.abs(change).toFixed(1)}</span>;
}

// "Round 18, locked after FP3 on 24 Oct" or "Round 19, preview from FP2"
function lockLine(w) {
  const bits = [];
  if (w?.round) bits.push(`Round ${w.round}`);
  if (w?.locked && w?.session_used) {
    const when = w.locked_at ? new Date(w.locked_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : null;
    bits.push(`locked after ${w.session_used}${when ? ` on ${when}` : ""}`);
  } else if (w?.session_used) {
    bits.push(`preview from ${w.session_used}`);
  }
  return bits.join(", ");
}

function finishLabel(f) {
  const state = f?.held ? "held" : f?.provisional ? "provisional" : f?.locked ? "locked" : "live";
  return f?.race_name ? `${state}, ${f.race_name}` : state;
}

// The 2x pick, which the main page never showed before (only the old Team Optimizer did)
function BoostBox({ pick }) {
  if (!pick) return null;
  return (
    <div className="flex items-center gap-3 border border-pw-red rounded-xl px-3 py-2.5 my-3">
      <span className="cond-x font-extrabold text-3xl text-pw-red leading-none">2x</span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2">
          <span className="cond font-bold text-lg leading-tight">{DRIVER_NAMES[pick.Abbreviation] || pick.Abbreviation}</span>
          <ConfidencePill level={pick.Confidence} />
        </div>
        <p className="text-xs text-pw-muted leading-relaxed">
          {pick.reason || `Starting P${pick.GridPosition}, predicted P${Math.round(pick.Predicted)}`}
        </p>
        {pick.alternatives?.length > 0 && (
          <p className="text-xs text-pw-muted">Next best: {pick.alternatives.map(surname).join(", ")}</p>
        )}
      </div>
    </div>
  );
}

function TeamRows({ team }) {
  return (
    <div>
      {team.drivers.map(d => (
        <TowerRow
          key={d.Abbreviation}
          spot={`P${Math.round(d.Predicted)}`}
          color={teamAccent(d.TeamName)}
          name={DRIVER_NAMES[d.Abbreviation] || d.Abbreviation}
          right={money(d.Price)}
          rightSub={pts(d.FantasyValue)}
        >
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-pw-muted">
            <span>{d.TeamName}</span>
            <CategoryTag category={displayCategory(d)} />
            <ConfidencePill level={d.Confidence} />
            {/* chance this driver retires. just for info, it doesn't change the picks */}
            {d.DNFProb != null && <RiskTag p={d.DNFProb} />}
          </div>
          <ConfidenceReason text={d.ConfidenceReason} />
        </TowerRow>
      ))}
      {(team.constructors || []).map(c => (
        <TowerRow key={c.name} spot="" color={teamAccent(c.name)} name={c.name} right={money(c.price)} rightSub={pts(c.score)}>
          <div className="flex flex-wrap gap-x-2 text-xs text-pw-muted">
            <span>Constructor</span>
            {c.dnf_risk != null && <><RiskTag p={c.dnf_risk} label="1+ out" /><RiskTag p={c.double_dnf_risk} label="both out" /></>}
          </div>
        </TowerRow>
      ))}
    </div>
  );
}

// The landing page: weather, this weekend's 3 teams with the 2x and chips, prices,
// and the predicted finish (with the real result next to it once the race is in).
export default function Overview({ nextRace, weekendData, held = false, weekendActiveTeam, setWeekendActiveTeam, priceChanges, finishes }) {
  const teams = weekendData?.teams?.length ? weekendData.teams : (weekendData?.team ? [weekendData.team] : []);
  const activeIdx = Math.min(weekendActiveTeam, teams.length - 1);
  const team = weekendData?.active && teams.length ? teams[activeIdx] : null;
  const raceName = weekendData?.race_name || nextRace?.race_name;

  const allDrivers = priceChanges?.drivers
    ? Object.entries(priceChanges.drivers).sort(([, a], [, b]) => b.price - a.price)
    : [];
  const allConstructors = priceChanges?.constructors
    ? Object.entries(priceChanges.constructors).sort(([, a], [, b]) => b.price - a.price)
    : [];
  const preds = finishes?.active && finishes?.predictions ? finishes.predictions : [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-4">
      <div className="flex flex-col gap-4 min-w-0">
        <WeatherWidget nextRace={nextRace} />

        <section className="bg-pw-panel rounded-xl px-3.5 sm:px-4 py-3.5">
          {team && held && (
            <p className="text-[13px] text-pw-caution bg-[#1E1A10] rounded-lg px-3 py-2 mb-3">
              No race weekend live right now. Showing the last locked team until the next race gets locked.
            </p>
          )}
          {/* provisional = worked out live before the weekend is locked, so it can still change */}
          {team && !held && weekendData?.provisional && (
            <p className="text-[13px] text-pw-info bg-[#141B2C] rounded-lg px-3 py-2 mb-3">
              {weekendData.awaiting_lock
                ? `Built from ${weekendData.session_used}. Locking in shortly, after that it won't change.`
                : `Not final yet, built from ${weekendData.session_used}. Locks once ${weekendData.final_session || "FP3"} is published.`}
            </p>
          )}

          {raceName && <h1 className="cond-x font-extrabold text-[34px] sm:text-[40px] leading-[0.95]">{raceName}</h1>}
          {team && <p className="text-[13px] text-pw-muted mt-1">{lockLine(weekendData)}</p>}

          {team ? (
            <>
              {teams.length > 1 && (
                <Switcher
                  className="mt-3"
                  value={activeIdx}
                  onChange={setWeekendActiveTeam}
                  options={teams.map((t, i) => ({ id: i, label: `Team ${i + 1}`, sub: `${fmt1(t.total_score)} pts` }))}
                />
              )}
              <BoostBox pick={team.boost_pick} />
              {showConfidenceKey(team.drivers) && <ConfidenceKey />}
              <TeamRows team={team} />
              <div className="flex gap-2 mt-3">
                <StatBox label="Expected points" value={fmt1(team.total_score)} />
                <StatBox label="Cost" value={money(team.total_cost)} />
                <StatBox label="Left over" value={money(team.budget_remaining)} />
              </div>
            </>
          ) : (
            <p className="text-pw-muted text-sm py-4">
              {weekendData && !weekendData.active
                ? (weekendData.message || "No race weekend live right now.")
                : "The teams show up once practice is in (within 5 days of a race)."}
            </p>
          )}
        </section>

        {/* chip advice for the team picked above, it follows the switcher */}
        <AutoChipAdvisor data={weekendData} activeTeam={weekendActiveTeam} />
      </div>

      <div className="flex flex-col gap-4 min-w-0">
        <Panel title="Predicted finish" aside={finishes ? finishLabel(finishes) : null}>
          {preds.length ? (
            <div className="max-h-80 overflow-y-auto no-scrollbar">
              {preds.map(p => {
                const line = finishLine(p, !!finishes.results_available);
                return (
                  <div key={p.abbreviation} className="flex items-center gap-2 text-[13px] py-1.5 border-b border-pw-line last:border-0 num">
                    <span className="w-8 text-pw-muted cond font-semibold">{line.spot}</span>
                    <span className="flex-1 min-w-0 truncate">{surname(p.abbreviation)}</span>
                    {/* the small arrow: model vs the plain practice order */}
                    {p.delta !== 0 && (
                      <span className={`text-[11px] ${p.delta > 0 ? "text-pw-safe" : "text-pw-low"}`} title="Model vs practice order">
                        {p.delta > 0 ? "▲" : "▼"}{Math.abs(p.delta)}
                      </span>
                    )}
                    {line.finished && (
                      <span className={`text-xs font-semibold px-2 rounded-full ${line.close ? "bg-[#163222] text-pw-safe" : "bg-pw-edge text-pw-muted"}`}>
                        {line.finished}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-pw-muted text-sm py-2">
              {finishes && !finishes.active ? "No race weekend live right now." : "Waiting for practice pace..."}
            </p>
          )}
        </Panel>

        <Panel title="Driver prices">
          <div className="max-h-48 overflow-y-auto no-scrollbar">
            {allDrivers.length ? allDrivers.map(([abbr, d]) => (
              <div key={abbr} className="flex justify-between items-center text-[13px] py-1 num">
                <span>{surname(abbr)}</span>
                <span className="flex items-center gap-1.5"><PriceDelta change={d.change} />{money(d.price)}</span>
              </div>
            )) : <p className="text-pw-muted text-sm py-2">Loading...</p>}
          </div>
        </Panel>

        <Panel title="Constructor prices">
          <div className="max-h-48 overflow-y-auto no-scrollbar">
            {allConstructors.length ? allConstructors.map(([name, d]) => (
              <div key={name} className="flex justify-between items-center gap-2 text-[13px] py-1 num">
                <span className="truncate border-l-[3px] pl-2" style={{ borderColor: teamAccent(name) }}>{name}</span>
                <span className="flex items-center gap-1.5 flex-shrink-0"><PriceDelta change={d.change} />{money(d.price)}</span>
              </div>
            )) : <p className="text-pw-muted text-sm py-2">Loading...</p>}
          </div>
        </Panel>
      </div>
    </div>
  );
}
