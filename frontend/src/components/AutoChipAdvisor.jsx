import { DRIVER_NAMES, CHIP_META, REC_STYLE } from "../constants";

// Actionable recommendations sort to the front so the useful chips surface first.
const REC_PRIORITY = { PLAY: 0, CONSIDER: 1, HEDGE: 1, "POST-QUALI": 2, HOLD: 3, SAVE: 3 };
const CHIP_ORDER = ["x3_boost", "wildcard", "limitless", "final_fix", "no_negative", "autopilot"];

function chipContext(key, chip) {
  switch (key) {
    case "x3_boost": {
      const name = chip.target ? (DRIVER_NAMES[chip.target] || chip.target) : null;
      if (!name) return null;
      return chip.gain ? `Boost ${name} · +${chip.gain} pts` : `Boost ${name}`;
    }
    case "wildcard":
    case "limitless":
      return chip.gain ? `+${chip.gain} pts vs this team` : "No gain over this team";
    case "final_fix":
      return chip.riskiest_driver
        ? `Post-qualifying swap · watch ${DRIVER_NAMES[chip.riskiest_driver] || chip.riskiest_driver}`
        : "Use after qualifying";
    case "no_negative":
      return chip.is_high_attrition ? "High-attrition circuit — worth hedging" : "Low attrition risk here";
    case "autopilot":
      return "Save it — PitWall already optimises your captain";
    default:
      return null;
  }
}

// Automatic chip advice for the weekend team currently shown. Shares App's
// /weekend-team data + active-team selection, so switching teams updates it.
// Every chip is graded, best suggestions first.
export default function AutoChipAdvisor({ data, activeTeam }) {
  const teams = data?.teams?.length ? data.teams : (data?.team ? [data.team] : []);
  if (!data || !data.active || teams.length === 0) return null;

  const team = teams[Math.min(activeTeam, teams.length - 1)];
  const chips = team?.chips;
  if (!chips) return null;

  const ordered = [...CHIP_ORDER]
    .filter(key => chips[key])
    .sort((a, b) => (REC_PRIORITY[chips[a].recommendation] ?? 9) - (REC_PRIORITY[chips[b].recommendation] ?? 9));

  const teamLabel = teams.length > 1 ? `Team ${Math.min(activeTeam, teams.length - 1) + 1}` : "your team";

  return (
    <div className="bg-pw-panel border border-white/[0.06] p-3.5">
      <div className="flex items-end justify-between mb-3">
        <p className="text-[10.5px] tracking-[0.05em] text-pw-muted">CHIP ADVISOR · AUTO</p>
        <p className="text-[9.5px] text-pw-muted text-right">{teamLabel} · {data.session_used} pace</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {ordered.map(key => {
          const chip = chips[key];
          const meta = CHIP_META[key] || { label: key, color: "#6b7280", desc: "" };
          const rec = chip.recommendation;
          const ctx = chipContext(key, chip);
          const muted = rec === "HOLD" || rec === "SAVE";
          return (
            <div
              key={key}
              className={`border-l-2 pl-3 pr-2.5 py-2 bg-pw-panel2 ${muted ? "opacity-55" : ""}`}
              style={{ borderColor: meta.color }}
            >
              <div className="flex justify-between items-start gap-2 mb-1">
                <span className="text-[12px] font-bold text-white">{meta.label}</span>
                <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0 ${REC_STYLE[rec] || REC_STYLE.HOLD}`}>
                  {rec}
                </span>
              </div>
              {ctx && <p className="text-[10.5px] text-pw-muted leading-snug">{ctx}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
