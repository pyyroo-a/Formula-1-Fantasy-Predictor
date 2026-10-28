import { DRIVER_NAMES, teamAccent } from "../constants";
import { finishLine } from "../lib/overview";
import DriverAvatar from "./DriverAvatar";
import Loading, { ErrorLine } from "../ui/Loading";

const STATE_TAG = {
  held: ["Held", "bg-[#1E1A10] text-pw-caution"],
  locked: ["Locked", "bg-[#163222] text-pw-safe"],
  provisional: ["Provisional", "bg-[#141B2C] text-pw-info"],
};

// Controlled: App owns the /weekend-finishes fetch and shares it with the
// Overview, so this component just renders whatever it's handed.
export default function PredictedFinishes({ data, loading, error }) {
  if (loading) return <Loading text="Loading predicted finishes. The free server can take up to 30 seconds to wake up." rows={5} />;
  if (error) return <ErrorLine text={error} />;

  // no live weekend, or too far out
  if (!data?.active || !data.predictions) {
    return (
      <div className="py-8">
        <p className="text-sm">{data?.message || "No race weekend live right now."}</p>
        {data?.race_name && <p className="text-xs text-pw-muted mt-1">{data.active ? data.race_name : `Next up: ${data.race_name}`}</p>}
      </div>
    );
  }

  // held = the race is over (or no live weekend), so we are showing the saved
  // predictions. hasActual = the real results are in, so we can compare
  const held = !!data.held;
  const hasActual = !!data.results_available;
  const acc = data.accuracy;
  const modelWon = acc && acc.model_mae < acc.baseline_mae;
  const baselineWon = acc && acc.baseline_mae < acc.model_mae;
  const tag = held ? STATE_TAG.held : data.locked ? STATE_TAG.locked : data.provisional ? STATE_TAG.provisional : null;

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        {tag && <span className={`text-[11px] font-extrabold px-1.5 py-0.5 rounded ${tag[1]}`}>{tag[0]}</span>}
        <h1 className="cond-x font-extrabold text-[30px] sm:text-[36px] leading-none">
          {held ? "What we predicted for the " : "Predicted finish for the "}{data.race_name}
        </h1>
      </div>
      <p className="text-xs text-pw-muted mt-1.5 mb-3">From {data.session_used} pace. For F1 Predict, not used for the fantasy picks.</p>

      {/* predicted vs actual summary, only once the race has happened */}
      {held && (hasActual && acc ? (
        <div className="grid grid-cols-2 gap-2 mb-3 num">
          <div className={`bg-pw-panel rounded-xl px-3 py-2 ${modelWon ? "ring-1 ring-pw-safe/50" : ""}`}>
            <p className="text-xs text-pw-muted">Model off by, on average</p>
            <p className={`cond-x font-extrabold text-2xl ${modelWon ? "text-pw-safe" : ""}`}>{acc.model_mae} places</p>
          </div>
          <div className={`bg-pw-panel rounded-xl px-3 py-2 ${baselineWon ? "ring-1 ring-pw-safe/50" : ""}`}>
            <p className="text-xs text-pw-muted">Practice order off by</p>
            <p className={`cond-x font-extrabold text-2xl ${baselineWon ? "text-pw-safe" : ""}`}>{acc.baseline_mae} places</p>
          </div>
          <p className="col-span-2 text-xs text-pw-muted">{acc.finishers} finishers compared, DNFs left out.</p>
        </div>
      ) : (
        <p className="text-xs text-pw-muted mb-3">The real results show up here once they're published, usually the day after the race.</p>
      ))}

      <p className="text-xs text-pw-muted mb-1">
        Predicted spot on the left, practice order under the name{hasActual ? ", real finish on the right, green means within 1 place" : ""}.
      </p>
      <div className="bg-pw-panel rounded-xl px-3 py-1">
        {data.predictions.map(p => {
          const line = finishLine(p, hasActual);
          return (
            <div key={p.abbreviation} className="flex items-center gap-2.5 py-1.5 border-b border-pw-line last:border-0">
              <span className="w-9 cond font-bold text-[17px] text-pw-muted num">{line.spot}</span>
              <span className="w-1 h-8 rounded-sm flex-shrink-0" style={{ background: teamAccent(p.team) }} />
              <DriverAvatar abbreviation={p.abbreviation} size="sm" />
              <div className="flex-1 min-w-0">
                <p className="cond font-semibold text-[16px] leading-tight truncate">{DRIVER_NAMES[p.abbreviation] || p.abbreviation}</p>
                <p className="text-xs text-pw-muted num">
                  practice order P{p.baseline_pos}
                  {p.delta !== 0 && <span className={`ml-1.5 ${p.delta > 0 ? "text-pw-safe" : "text-pw-low"}`}>{p.delta > 0 ? "▲" : "▼"}{Math.abs(p.delta)}</span>}
                </p>
              </div>
              {line.finished && (
                <span className={`flex-shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full num ${line.close ? "bg-[#163222] text-pw-safe" : "bg-pw-edge text-pw-muted"}`}>
                  {line.finished}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-pw-muted mt-3 leading-relaxed max-w-[70ch]">
        Heads up: in backtesting, the plain practice order beat the model. Both are shown so you can judge which
        is closer each weekend, treat the model as an experiment. The arrow is the model vs the practice order.
      </p>
    </div>
  );
}
