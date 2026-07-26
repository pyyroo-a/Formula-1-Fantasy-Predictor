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

// Automatic chip advice for the weekend team currently shown in the lineup widget.
// Shares App's /weekend-team data + active-team selection, so switching teams
// above updates the chips here. Every chip is graded, best suggestions first.
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
    <div className="mb-6">
      <div className="flex items-end justify-between mb-3">
        <div>
          <p className="text-xs text-red-500 uppercase tracking-widest font-semibold mb-0.5">Chip Advisor · Auto</p>
          <p className="text-white font-bold text-lg">Should you play a chip?</p>
        </div>
        <p className="text-xs text-gray-500 text-right">Graded for {teamLabel}<br />on {data.session_used} pace</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {ordered.map(key => {
          const chip = chips[key];
          const meta = CHIP_META[key] || { label: key, color: "#6b7280", desc: "" };
          const rec = chip.recommendation;
          const ctx = chipContext(key, chip);
          const muted = rec === "HOLD" || rec === "SAVE";
          return (
            <div
              key={key}
              className={`rounded-xl p-4 border-l-4 ${muted ? "bg-gray-800/40 opacity-70" : "bg-gray-800"}`}
              style={{ borderLeftColor: meta.color }}
            >
              <div className="flex justify-between items-start mb-1.5 gap-2">
                <h3 className="text-white font-bold text-sm">{meta.label}</h3>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0 ${REC_STYLE[rec] || REC_STYLE.HOLD}`}>
                  {rec}
                </span>
              </div>
              <p className="text-gray-500 text-[11px] leading-relaxed mb-2">{meta.desc}</p>
              {ctx && <p className="text-gray-300 text-xs font-medium">{ctx}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
