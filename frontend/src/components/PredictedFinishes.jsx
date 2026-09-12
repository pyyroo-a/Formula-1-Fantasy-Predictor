import { DRIVER_NAMES, teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";

function DeltaBadge({ delta }) {
  if (delta === 0) {
    return <span className="text-gray-500 text-xs">—</span>;
  }
  const up = delta > 0; // model expects a better finish than practice order
  return (
    <span className={`text-xs font-semibold ${up ? "text-green-400" : "text-red-400"}`}>
      {up ? "▲" : "▼"} {Math.abs(delta)}
    </span>
  );
}

// what actually happened in the race. green means the model was within a place,
// so you can quickly scan how it did
function ActualCell({ p }) {
  if (p.actual_pos != null) {
    const off = Math.abs(p.model_pos - p.actual_pos);
    return <span className={off <= 1 ? "text-green-400 font-semibold" : "text-white"}>P{p.actual_pos}</span>;
  }
  if (p.actual_status) return <span className="text-red-400 text-xs">DNF</span>;
  return <span className="text-gray-600">?</span>;
}

// Controlled: App owns the /weekend-finishes fetch and shares it with the
// Overview live-card, so this component just renders whatever it's handed.
export default function PredictedFinishes({ data, loading, error }) {
  if (loading) {
    return (
      <div className="text-center py-10">
        <p className="text-gray-400 text-sm">Loading predicted finishes…</p>
        <p className="text-gray-600 text-xs mt-1">May take 15–30 seconds while FastF1 loads practice data</p>
      </div>
    );
  }

  if (error) {
    return <p className="text-red-400 text-sm text-center py-10">{error}</p>;
  }

  // No active weekend, or too far out
  if (!data?.active) {
    return (
      <div className="text-center py-10">
        <p className="text-gray-300 text-sm">{data?.message || "No active race weekend."}</p>
        {data?.race_name && <p className="text-gray-600 text-xs mt-1">Next up: {data.race_name}</p>}
      </div>
    );
  }

  // Active weekend but practice data not out yet
  if (!data.predictions) {
    return (
      <div className="text-center py-10">
        <p className="text-gray-300 text-sm">{data.message}</p>
        <p className="text-gray-600 text-xs mt-1">{data.race_name}</p>
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

  return (
    <div>
      <p className="text-gray-400 text-sm text-center mb-1">
        {held && <span className="bg-pw-risk text-black text-[9px] font-black px-1.5 py-0.5 rounded-sm tracking-wider mr-2">HELD</span>}
        {held ? "What we predicted for " : "Predicted finishing order for "}
        <span className="text-white font-semibold">{data.race_name}</span>
      </p>
      <p className="text-gray-600 text-xs text-center mb-5">
        For F1 Predict · based on {data.session_used} pace · not used for fantasy picks
      </p>

      {/* predicted vs actual summary, only once the race has happened */}
      {held && (hasActual && acc ? (
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-1 text-xs mb-5 border border-gray-800 py-3 px-2">
          <span className="text-gray-400">
            Model off by <span className={modelWon ? "text-green-400 font-semibold" : "text-white font-semibold"}>{acc.model_mae}</span> places on avg
          </span>
          <span className="text-gray-400">
            Practice order off by <span className={baselineWon ? "text-green-400 font-semibold" : "text-white font-semibold"}>{acc.baseline_mae}</span>
          </span>
          <span className="text-gray-600">{acc.finishers} finishers compared, DNFs left out</span>
        </div>
      ) : (
        <p className="text-gray-500 text-xs text-center mb-5">
          Actual results show up here once they are published, usually the day after the race.
        </p>
      ))}

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 text-xs text-gray-500 mb-4">
        <span><span className="text-white">Model</span> = our forecast</span>
        <span><span className="text-white">Practice</span> = pace-order baseline</span>
        <span>Δ = model vs practice</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs uppercase tracking-wider border-b border-gray-700">
              <th className="text-left py-2 pl-2 w-14">Model</th>
              <th className="text-left py-2">Driver</th>
              {hasActual && <th className="text-center py-2 w-16">Actual</th>}
              <th className="text-center py-2 w-20">Practice</th>
              <th className="text-center py-2 w-16">Δ</th>
            </tr>
          </thead>
          <tbody>
            {data.predictions.map((p) => (
              <tr key={p.abbreviation} className="border-b border-gray-800 hover:bg-gray-800/40">
                <td className="py-2 pl-2">
                  <span className="text-white font-bold">P{p.model_pos}</span>
                </td>
                <td className="py-2">
                  <div className="flex items-center gap-2">
                    <DriverAvatar abbreviation={p.abbreviation} size="sm" />
                    <div className="min-w-0">
                      <span className="text-white font-medium">{p.abbreviation}</span>
                      <span
                        className="ml-2 text-gray-500 text-xs border-l-2 pl-2"
                        style={{ borderColor: teamAccent(p.team) }}
                      >
                        {DRIVER_NAMES[p.abbreviation] || p.team}
                      </span>
                    </div>
                  </div>
                </td>
                {hasActual && <td className="text-center py-2"><ActualCell p={p} /></td>}
                <td className="text-center py-2 text-gray-400">P{p.baseline_pos}</td>
                <td className="text-center py-2"><DeltaBadge delta={p.delta} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-gray-600 text-xs mt-4 leading-relaxed">
        Heads up: in backtesting, the plain practice-pace order beat the model. Both are shown so
        you can judge which is closer each weekend — treat the model column as an experiment.
      </p>
    </div>
  );
}
