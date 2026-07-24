import { useState, useEffect } from "react";
import { API } from "../api";
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

export default function PredictedFinishes() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/weekend-finishes`)
      .then(r => r.json())
      .then(d => {
        if (d.detail) throw new Error(d.detail);
        setData(d);
      })
      .catch(e => setError(e.message || "Failed to load predicted finishes."))
      .finally(() => setLoading(false));
  }, []);

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

  return (
    <div>
      <p className="text-gray-400 text-sm text-center mb-1">
        Predicted finishing order for <span className="text-white font-semibold">{data.race_name}</span>
      </p>
      <p className="text-gray-600 text-xs text-center mb-5">
        For F1 Predict · based on {data.session_used} pace · not used for fantasy picks
      </p>

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
