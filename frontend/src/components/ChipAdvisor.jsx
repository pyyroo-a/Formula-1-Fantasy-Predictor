import { useState } from "react";
import { API } from "../api";
import { DRIVER_NAMES, CHIP_META, REC_STYLE, teamAccent } from "../constants";
import DriverAvatar from "./DriverAvatar";

const ALL_DRIVERS = [
  "VER","NOR","PIA","LEC","HAM","RUS","SAI","ALO","STR","GAS",
  "ALB","OCO","LAW","HUL","BEA","ANT","BOR","LIN","HAD","COL",
  "PER","BOT",
];
const ALL_CONSTRUCTORS = [
  "Red Bull Racing","McLaren","Ferrari","Mercedes","Aston Martin",
  "Alpine","Williams","RB F1 Team","Audi","Haas","Cadillac",
];

function ChipCard({ chipKey, data }) {
  const meta = CHIP_META[chipKey];
  const recStyle = REC_STYLE[data.recommendation] || REC_STYLE.HOLD;
  return (
    <div className="bg-gray-800 rounded-xl p-4 border-l-4" style={{ borderLeftColor: meta.color }}>
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-white font-bold text-base">{meta.label}</h3>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${recStyle}`}>
          {data.recommendation}
        </span>
      </div>
      <p className="text-gray-500 text-xs mb-3 leading-relaxed">{meta.desc}</p>
      <p className="text-gray-300 text-sm leading-relaxed">{data.reason}</p>
      {data.gain !== null && data.gain !== undefined && (
        <div className="mt-3 pt-3 border-t border-gray-700 flex items-center gap-2">
          <span className="text-gray-500 text-xs">Expected xP gain:</span>
          <span className={`font-bold text-sm ${data.gain >= 0 ? "text-green-400" : "text-red-400"}`}>
            {data.gain >= 0 ? "+" : ""}{data.gain?.toFixed(1)}
          </span>
        </div>
      )}
    </div>
  );
}

function ChipAdvisorResults({ result, myTeamScore }) {
  const chips = Object.entries(result.chips);
  const playChips = chips.filter(([, d]) => d.recommendation === "PLAY");
  const considerChips = chips.filter(([, d]) => d.recommendation === "CONSIDER");
  const topPick = playChips[0] || considerChips[0];

  return (
    <div className="space-y-4">
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Your Squad</h3>
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-xs text-gray-500 mb-1">Session</p>
            <p className="text-white font-semibold text-sm">{result.session_used}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Your Score</p>
            <p className="text-white font-bold text-lg">{myTeamScore?.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 mb-1">Best Chip</p>
            {topPick
              ? <p className="font-bold text-sm" style={{ color: CHIP_META[topPick[0]]?.color }}>{CHIP_META[topPick[0]]?.label}</p>
              : <p className="text-gray-500 text-sm">Hold all</p>
            }
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {chips.map(([key, data]) => <ChipCard key={key} chipKey={key} data={data} />)}
      </div>
    </div>
  );
}

export default function ChipAdvisor({ upcomingRaces }) {
  const [raceName, setRaceName] = useState("");
  const [myDrivers, setMyDrivers] = useState([]);
  const [myConstructors, setMyConstructors] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const toggleDriver = (abbr) => {
    setResult(null);
    setMyDrivers(prev =>
      prev.includes(abbr) ? prev.filter(a => a !== abbr)
      : prev.length < 5 ? [...prev, abbr] : prev
    );
  };

  const toggleConstructor = (name) => {
    setResult(null);
    setMyConstructors(prev =>
      prev.includes(name) ? prev.filter(n => n !== name)
      : prev.length < 2 ? [...prev, name] : prev
    );
  };

  const canSubmit = raceName && myDrivers.length === 5 && myConstructors.length === 2;

  const submit = async () => {
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await fetch(`${API}/chip-advisor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: raceName, my_drivers: myDrivers, my_constructors: myConstructors }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setResult(data);
    } catch (e) {
      setError(e.message || "Something went wrong.");
    }
    setLoading(false);
  };

  const myTeamScore = result?.my_team_score;

  return (
    <div>
      <p className="text-gray-400 text-sm text-center mb-6">Enter your current F1 Fantasy squad and we'll tell you which chip to play this round.</p>

      <select
        value={raceName}
        onChange={e => { setRaceName(e.target.value); setResult(null); }}
        className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-5"
      >
        <option value="">Select race</option>
        {(upcomingRaces || []).map(r => (
          <option key={r.race_name} value={r.race_name}>{r.race_name}</option>
        ))}
      </select>

      <div className="mb-5">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Your Drivers</h3>
          <span className="text-gray-600 text-xs">{myDrivers.length}/5</span>
        </div>
        <div className="grid grid-cols-8 gap-1.5">
          {ALL_DRIVERS.map(abbr => {
            const isSelected = myDrivers.includes(abbr);
            const canAdd = !isSelected && myDrivers.length < 5;
            return (
              <button
                key={abbr}
                onClick={() => toggleDriver(abbr)}
                disabled={!isSelected && !canAdd}
                className={`flex flex-col items-center gap-1 rounded-lg py-2 px-1 transition border ${
                  isSelected ? "bg-gray-700 border-white/20 text-white"
                  : canAdd ? "bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-750 hover:border-gray-500"
                  : "bg-gray-800/40 border-gray-800 text-gray-600 cursor-not-allowed opacity-40"
                }`}
              >
                <DriverAvatar abbreviation={abbr} size="md" />
                <span className="text-[10px] font-semibold leading-none">{abbr}</span>
                {isSelected && <span className="text-green-400 text-[10px] leading-none">✓</span>}
              </button>
            );
          })}
        </div>
        {myDrivers.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {myDrivers.map(abbr => (
              <span key={abbr} className="bg-gray-700 text-white text-xs px-2 py-0.5 rounded-full">
                {DRIVER_NAMES[abbr] || abbr}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Your Constructors</h3>
          <span className="text-gray-600 text-xs">{myConstructors.length}/2</span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {ALL_CONSTRUCTORS.map(name => {
            const isSelected = myConstructors.includes(name);
            const canAdd = !isSelected && myConstructors.length < 2;
            const accent = teamAccent(name);
            return (
              <button
                key={name}
                onClick={() => toggleConstructor(name)}
                disabled={!isSelected && !canAdd}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition border-l-4 ${
                  isSelected ? "bg-gray-600 text-white"
                  : canAdd ? "bg-gray-800 text-gray-300 hover:bg-gray-700"
                  : "bg-gray-800/40 text-gray-600 cursor-not-allowed opacity-40"
                }`}
                style={{ borderLeftColor: accent }}
              >
                {name} {isSelected && "✓"}
              </button>
            );
          })}
        </div>
      </div>

      <button
        onClick={submit}
        disabled={!canSubmit || loading}
        className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed transition font-medium mb-4"
      >
        {loading ? "Analysing..." : "Get Chip Advice"}
      </button>

      {error && <p className="text-red-400 text-sm text-center mb-4">{error}</p>}
      {result && <ChipAdvisorResults result={result} myTeamScore={myTeamScore} />}
    </div>
  );
}
