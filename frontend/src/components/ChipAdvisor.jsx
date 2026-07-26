import { useState } from "react";
import { API } from "../api";
import { DRIVER_NAMES, CHIP_META, REC_STYLE, teamAccent } from "../constants";

const ALL_DRIVERS = [
  "VER","NOR","PIA","LEC","HAM","RUS","SAI","ALO","STR","GAS",
  "ALB","OCO","LAW","HUL","BEA","ANT","BOR","LIN","HAD","COL",
  "PER","BOT",
];
const ALL_CONSTRUCTORS = [
  "Red Bull Racing","McLaren","Ferrari","Mercedes","Aston Martin",
  "Alpine","Williams","RB F1 Team","Audi","Haas","Cadillac",
];

const SELECT_CLS = "w-full p-2.5 bg-pw-panel2 text-white text-sm border border-white/10 outline-none focus:border-pw-red/50";
const HEAD_CLS = "text-xs text-pw-muted tracking-[0.08em]";

function ChipCard({ chipKey, data }) {
  const meta = CHIP_META[chipKey];
  const recStyle = REC_STYLE[data.recommendation] || REC_STYLE.HOLD;
  return (
    <div className="bg-pw-panel2 border-l-2 pl-3 pr-3 py-2.5" style={{ borderColor: meta.color }}>
      <div className="flex justify-between items-start mb-1 gap-2">
        <h3 className="text-white font-bold text-[13px]">{meta.label}</h3>
        <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0 ${recStyle}`}>
          {data.recommendation}
        </span>
      </div>
      <p className="text-pw-muted text-[10.5px] leading-relaxed">{meta.desc}</p>
      {data.reason && <p className="text-gray-300 text-[11.5px] mt-1.5 leading-relaxed">{data.reason}</p>}
      {data.gain !== null && data.gain !== undefined && (
        <div className="mt-2 pt-2 border-t border-white/[0.06] flex items-center gap-2">
          <span className="text-pw-muted text-[10.5px]">Expected xP gain:</span>
          <span className={`font-bold text-[12px] ${data.gain >= 0 ? "text-pw-safe" : "text-pw-red"}`}>
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
    <div className="space-y-3">
      <div className="pw-hairgrid grid grid-cols-3 gap-px border border-white/[0.06]">
        <div className="bg-pw-panel px-3 py-3 text-center">
          <p className="text-[9.5px] text-pw-muted tracking-[0.05em] mb-1">SESSION</p>
          <p className="text-white font-bold text-sm">{result.session_used}</p>
        </div>
        <div className="bg-pw-panel px-3 py-3 text-center">
          <p className="text-[9.5px] text-pw-muted tracking-[0.05em] mb-1">YOUR SCORE</p>
          <p className="text-white font-extrabold text-lg">{myTeamScore?.toFixed(2)}</p>
        </div>
        <div className="bg-pw-panel px-3 py-3 text-center">
          <p className="text-[9.5px] text-pw-muted tracking-[0.05em] mb-1">BEST CHIP</p>
          {topPick
            ? <p className="font-bold text-sm" style={{ color: CHIP_META[topPick[0]]?.color }}>{CHIP_META[topPick[0]]?.label}</p>
            : <p className="text-pw-muted text-sm">Hold all</p>
          }
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
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
      <p className="text-pw-muted text-sm text-center mb-5">Enter your current F1 Fantasy squad and we'll tell you which chip to play this round.</p>

      <select
        value={raceName}
        onChange={e => { setRaceName(e.target.value); setResult(null); }}
        className={`${SELECT_CLS} mb-5`}
      >
        <option value="">Select race</option>
        {(upcomingRaces || []).map(r => (
          <option key={r.race_name} value={r.race_name}>{r.race_name}</option>
        ))}
      </select>

      <div className="mb-5">
        <div className="flex justify-between items-center mb-3">
          <h3 className={HEAD_CLS}>YOUR DRIVERS</h3>
          <span className="text-pw-muted text-xs">{myDrivers.length}/5</span>
        </div>
        <div className="grid grid-cols-6 sm:grid-cols-8 gap-1.5">
          {ALL_DRIVERS.map(abbr => {
            const isSelected = myDrivers.includes(abbr);
            const canAdd = !isSelected && myDrivers.length < 5;
            return (
              <button
                key={abbr}
                onClick={() => toggleDriver(abbr)}
                disabled={!isSelected && !canAdd}
                className={`py-2 text-[11px] font-semibold border transition ${
                  isSelected ? "bg-pw-panel border-white/20 text-white"
                  : canAdd ? "bg-pw-panel2 border-white/10 text-pw-muted hover:text-white hover:border-white/25"
                  : "bg-pw-panel2/40 border-white/5 text-pw-muted/40 cursor-not-allowed"
                }`}
              >
                {abbr}
              </button>
            );
          })}
        </div>
        {myDrivers.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {myDrivers.map(abbr => (
              <span key={abbr} className="bg-pw-panel2 text-white text-[10.5px] px-2 py-0.5 rounded-sm border border-white/10">
                {DRIVER_NAMES[abbr] || abbr}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <h3 className={HEAD_CLS}>YOUR CONSTRUCTORS</h3>
          <span className="text-pw-muted text-xs">{myConstructors.length}/2</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {ALL_CONSTRUCTORS.map(name => {
            const isSelected = myConstructors.includes(name);
            const canAdd = !isSelected && myConstructors.length < 2;
            const accent = teamAccent(name);
            return (
              <button
                key={name}
                onClick={() => toggleConstructor(name)}
                disabled={!isSelected && !canAdd}
                className={`px-3 py-1.5 text-[11px] font-medium transition border-l-2 ${
                  isSelected ? "bg-pw-panel text-white"
                  : canAdd ? "bg-pw-panel2 text-pw-muted hover:text-white"
                  : "bg-pw-panel2/40 text-pw-muted/40 cursor-not-allowed"
                }`}
                style={{ borderColor: accent }}
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
        className="w-full p-2.5 bg-pw-red hover:bg-[#ff7676] text-white text-sm font-semibold transition disabled:bg-white/10 disabled:text-pw-muted disabled:cursor-not-allowed mb-4"
      >
        {loading ? "Analysing…" : "Get Chip Advice"}
      </button>

      {error && <p className="text-pw-red text-sm text-center mb-4">{error}</p>}
      {result && <ChipAdvisorResults result={result} myTeamScore={myTeamScore} />}
    </div>
  );
}
