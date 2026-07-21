import { useState } from "react";
import { API } from "../api";

function Stat({ label, value, tone = "neutral", hint }) {
  const toneClass =
    tone === "good" ? "text-green-400" :
    tone === "bad"  ? "text-red-400"   :
    "text-white";

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className={`text-xl font-bold ${toneClass}`}>{value}</p>
      {hint && <p className="text-xs text-gray-600 mt-0.5">{hint}</p>}
    </div>
  );
}

export default function Backtest() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [openRace, setOpenRace] = useState(null);

  const run = async () => {
    setLoading(true); setError(null); setData(null);
    try {
      const res = await fetch(`${API}/backtest`);
      const json = await res.json();
      if (json.detail) throw new Error(json.detail);
      setData(json);
    } catch (e) {
      setError(e.message || "Backtest failed.");
    }
    setLoading(false);
  };

  const s = data?.summary;
  const beatsBaseline = s && s.avg_delta > 0;

  return (
    <>
      <p className="text-gray-400 text-sm text-center mb-4">
        Replays each completed race with the model trained <em>only</em> on races before it,
        then scores its picks against what actually happened.
      </p>

      <button
        onClick={run}
        disabled={loading}
        className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-gray-600 transition font-medium"
      >
        {loading ? "Replaying season..." : "Run Backtest"}
      </button>

      {loading && (
        <p className="text-gray-600 text-xs text-center mt-2">
          Retrains the model once per race — takes 1–2 minutes.
        </p>
      )}
      {error && <p className="mt-4 text-red-400 text-sm text-center">{error}</p>}

      {s && (
        <div className="mt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            <Stat label="Races tested" value={s.races_tested} />
            <Stat label="Avg model score" value={s.avg_model_score} />
            <Stat
              label="Avg baseline"
              value={s.avg_baseline_score}
              hint="picking by grid order"
            />
            <Stat
              label="Avg delta"
              value={`${s.avg_delta > 0 ? "+" : ""}${s.avg_delta}`}
              tone={beatsBaseline ? "good" : "bad"}
              hint={`beat baseline in ${s.races_beating_baseline}/${s.races_tested}`}
            />
          </div>

          <div
            className={`rounded-lg p-4 mb-5 border ${
              beatsBaseline
                ? "bg-green-950/40 border-green-800"
                : "bg-red-950/40 border-red-800"
            }`}
          >
            <p className={`font-semibold mb-1 ${beatsBaseline ? "text-green-400" : "text-red-400"}`}>
              {beatsBaseline
                ? "Model beats the grid-order baseline"
                : "Model loses to the grid-order baseline"}
            </p>
            <p className="text-gray-300 text-sm">
              {beatsBaseline
                ? `The model averages ${s.avg_delta} more points per race than simply picking the fastest qualifiers.`
                : `Simply picking the best team by qualifying position scores ${Math.abs(s.avg_delta)} more points per race. The model is not yet adding value over the grid.`}
            </p>
            <p className="text-gray-500 text-xs mt-2">
              Best-of-three averages {s.avg_best_of_three} — the ceiling if you always picked
              the strongest of the three generated teams.
            </p>
          </div>

          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
            Race by race
          </h3>

          <div className="space-y-2">
            {data.races.map((r) => {
              if (r.error) {
                return (
                  <div key={r.round} className="bg-gray-800 border border-gray-700 rounded-lg p-3">
                    <span className="text-gray-300 text-sm">{r.race_name}</span>
                    <span className="text-red-400 text-xs ml-2">{r.error}</span>
                  </div>
                );
              }
              const won = r.delta > 0;
              const isOpen = openRace === r.round;

              return (
                <div key={r.round} className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setOpenRace(isOpen ? null : r.round)}
                    className="w-full flex items-center justify-between p-3 hover:bg-gray-750 transition text-left"
                  >
                    <div className="min-w-0">
                      <p className="text-sm text-white truncate">{r.race_name}</p>
                      <p className="text-xs text-gray-500">
                        model {r.model_score} · baseline {r.baseline_score}
                      </p>
                    </div>
                    <span className={`text-sm font-bold shrink-0 ml-3 ${won ? "text-green-400" : "text-red-400"}`}>
                      {won ? "+" : ""}{r.delta}
                    </span>
                  </button>

                  {isOpen && (
                    <div className="border-t border-gray-700 p-3 bg-gray-850">
                      <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                        What the model picked
                      </p>
                      <div className="space-y-1 mb-3">
                        {r.drivers.map((d) => (
                          <div key={d.Abbreviation} className="flex items-center justify-between text-sm">
                            <span className="text-gray-300">
                              {d.Abbreviation}
                              {d.is_boost && (
                                <span className="ml-2 text-xs bg-yellow-600 text-black px-1.5 py-0.5 rounded font-bold">
                                  2x
                                </span>
                              )}
                              <span className="text-gray-600 text-xs ml-2">
                                P{d.GridPosition} → predicted P{d.Predicted}
                              </span>
                            </span>
                            <span className={d.actual_points >= 0 ? "text-green-400" : "text-red-400"}>
                              {d.actual_points > 0 ? "+" : ""}{d.actual_points}
                            </span>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Constructors</p>
                      <div className="space-y-1">
                        {r.constructors.map((c) => (
                          <div key={c.name} className="flex items-center justify-between text-sm">
                            <span className="text-gray-300">{c.name}</span>
                            <span className={c.actual_points >= 0 ? "text-green-400" : "text-red-400"}>
                              {c.actual_points > 0 ? "+" : ""}{c.actual_points}
                            </span>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-gray-600 mt-3">
                        All three teams scored: {r.all_team_scores.join(" · ")}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <p className="text-xs text-gray-600 mt-4 leading-relaxed">
            <strong className="text-gray-500">Caveat:</strong> practice data isn't replayed, so the
            backtest runs without the FP3-pace and teammate-gap signals the live model uses —
            it blends form and circuit history only. Grid positions are taken as known, which
            flatters both the model and the baseline equally.
          </p>
        </div>
      )}
    </>
  );
}
