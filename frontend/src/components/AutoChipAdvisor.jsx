import { DRIVER_NAMES, CHIP_META } from "../constants";
import { fmt1 } from "../lib/format";
import VerdictTag from "../ui/VerdictTag";

// Actionable recommendations sort to the front so the useful chips surface first.
const REC_PRIORITY = { PLAY: 0, CONSIDER: 1, HEDGE: 1, "POST-QUALI": 2, HOLD: 3, SAVE: 3 };
const CHIP_ORDER = ["x3_boost", "wildcard", "limitless", "final_fix", "no_negative", "autopilot"];

function chipContext(key, chip) {
  switch (key) {
    case "x3_boost": {
      const name = chip.target ? (DRIVER_NAMES[chip.target] || chip.target) : null;
      if (!name) return null;
      return chip.gain ? `On ${name}, +${fmt1(chip.gain)} pts` : `On ${name}`;
    }
    case "wildcard":
    case "limitless":
      return chip.gain ? `+${fmt1(chip.gain)} pts vs this team` : "No gain over this team";
    case "final_fix":
      return chip.riskiest_driver
        ? `Decide after qualifying, watch ${DRIVER_NAMES[chip.riskiest_driver] || chip.riskiest_driver}`
        : "Use after qualifying";
    case "no_negative":
      return chip.is_high_attrition ? "High-attrition circuit, worth hedging" : "Low attrition risk here";
    case "autopilot":
      return "Save it, PitWall already picks your 2x";
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
    <section className="bg-pw-panel rounded-xl px-3.5 sm:px-4 py-3.5">
      <div className="flex items-baseline justify-between gap-2 mb-3">
        <h3 className="cond font-bold text-[15px]">Chips for {teamLabel}</h3>
        <p className="text-xs text-pw-muted text-right">from {data.session_used} pace</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {ordered.map(key => {
          const chip = chips[key];
          const meta = CHIP_META[key] || { label: key, color: "#6b7280", desc: "" };
          const rec = chip.recommendation;
          const ctx = chipContext(key, chip);
          const muted = rec === "HOLD" || rec === "SAVE";
          return (
            <div
              key={key}
              className={`bg-pw-raised rounded-lg border-l-[3px] px-3 py-2 ${muted ? "opacity-60" : ""}`}
              style={{ borderColor: meta.color }}
            >
              <div className="flex justify-between items-center gap-2">
                <span className="cond font-bold text-[15px]">{meta.label}</span>
                <VerdictTag rec={rec} />
              </div>
              {ctx && <p className="text-xs text-pw-muted leading-snug mt-0.5">{ctx}</p>}
            </div>
          );
        })}
      </div>
    </section>
  );
}
