import { DRIVER_NAMES, teamAccent } from "../constants";
import WeatherWidget from "./WeatherWidget";
import AutoChipAdvisor from "./AutoChipAdvisor";

const CAT_BADGE = {
  Safe:  "text-pw-safe bg-pw-safe/10",
  Value: "text-pw-rain bg-pw-rain/10",
  Risk:  "text-pw-risk bg-pw-risk/10",
  Avoid: "text-pw-red bg-pw-red/10",
};

function PanelLabel({ children }) {
  return <p className="text-[10.5px] tracking-[0.05em] text-pw-muted mb-2.5">{children}</p>;
}

function shortName(abbr) {
  const full = DRIVER_NAMES[abbr];
  if (!full) return abbr;
  const parts = full.split(" ");
  return `${parts[0][0]}. ${parts.slice(1).join(" ")}`;
}

// The landing dashboard — weather, weekend lineup, prices, live predicted finish.
export default function Overview({ nextRace, weekendData, weekendActiveTeam, setWeekendActiveTeam, priceChanges, finishes }) {
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
    <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-3.5">
      {/* ── Left column ── */}
      <div className="flex flex-col gap-3.5">
        <WeatherWidget nextRace={nextRace} />

        <div className="bg-pw-panel border border-white/[0.06] p-3.5">
          <div className="flex items-start justify-between gap-2 mb-2.5">
            <p className="text-[10.5px] tracking-[0.05em] text-pw-muted">RACE WEEKEND LINEUP{raceName ? ` · ${raceName}` : ""}</p>
            {teams.length > 1 && (
              <div className="flex gap-0.5 flex-shrink-0">
                {teams.map((t, i) => (
                  <button
                    key={i}
                    onClick={() => setWeekendActiveTeam(i)}
                    title={`Team ${i + 1} · ${t.total_score?.toFixed(1)} pts · $${t.total_cost}M`}
                    className={`px-2 py-0.5 text-[10px] font-bold rounded-sm transition ${
                      activeIdx === i ? "bg-pw-red text-white" : "bg-pw-panel2 text-pw-muted hover:text-white"
                    }`}
                  >
                    T{i + 1}
                  </button>
                ))}
              </div>
            )}
          </div>
          {team ? (
            <div className="flex flex-col">
              {team.drivers.map((d, i) => {
                const badge = CAT_BADGE[d.PickCategory] || "text-pw-muted bg-white/5";
                return (
                  <div
                    key={d.Abbreviation}
                    className="flex items-center gap-2.5 py-2 border-b border-white/[0.05]"
                  >
                    <div className="w-5 text-pw-muted text-[11px]">{String(i + 1).padStart(2, "0")}</div>
                    <div
                      className="flex-1 text-[12.5px] text-white truncate border-l-2 pl-2.5"
                      style={{ borderColor: teamAccent(d.TeamName) }}
                    >
                      {shortName(d.Abbreviation)} <span className="text-pw-muted">— {d.TeamName}</span>
                    </div>
                    <span className={`text-[9.5px] px-1.5 py-0.5 rounded-sm ${badge}`}>{(d.PickCategory || "").toUpperCase()}</span>
                    <div className="text-[11.5px] text-white w-16 text-right">${d.Price?.toFixed(1)}M</div>
                  </div>
                );
              })}
              {/* Constructors — horizontal pair, drivers stay vertical above */}
              <div className="grid grid-cols-2 gap-2 mt-2.5">
                {(team.constructors || []).map(c => (
                  <div
                    key={c.name}
                    className="flex items-center justify-between gap-2 bg-pw-panel2 border-l-2 pl-2.5 pr-2 py-2"
                    style={{ borderColor: teamAccent(c.name) }}
                  >
                    <span className="text-[12px] text-white truncate">{c.name}</span>
                    <span className="text-[11.5px] text-white flex-shrink-0">${c.price?.toFixed(1)}M</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-pw-muted text-xs py-4">
              {weekendData && !weekendData.active
                ? (weekendData.message || "No active race weekend right now.")
                : "Lineup appears once practice data is in (within 5 days of a race)."}
            </p>
          )}
        </div>

        {/* Chip advice for the generated team, shown automatically underneath it */}
        <AutoChipAdvisor data={weekendData} activeTeam={weekendActiveTeam} />
      </div>

      {/* ── Right column ── */}
      <div className="flex flex-col gap-3.5">
        <div className="bg-pw-panel border border-white/[0.06] p-3.5">
          <PanelLabel>DRIVER PRICES</PanelLabel>
          <div className="max-h-44 overflow-y-auto no-scrollbar pr-1">
            {allDrivers.length ? allDrivers.map(([abbr, d]) => (
              <div key={abbr} className="flex justify-between text-[11.5px] text-white py-1">
                <span>{DRIVER_NAMES[abbr]?.split(" ").slice(-1)[0] || abbr}</span>
                <span>${d.price.toFixed(1)}M</span>
              </div>
            )) : <p className="text-pw-muted text-xs py-2">Loading…</p>}
          </div>
        </div>

        <div className="bg-pw-panel border border-white/[0.06] p-3.5">
          <PanelLabel>CONSTRUCTOR PRICES</PanelLabel>
          <div className="max-h-36 overflow-y-auto no-scrollbar pr-1">
            {allConstructors.length ? allConstructors.map(([name, d]) => (
              <div key={name} className="flex justify-between text-[11.5px] text-white py-1">
                <span
                  className="truncate border-l-2 pl-2"
                  style={{ borderColor: teamAccent(name) }}
                >{name}</span>
                <span className="flex-shrink-0">${d.price.toFixed(1)}M</span>
              </div>
            )) : <p className="text-pw-muted text-xs py-2">Loading…</p>}
          </div>
        </div>

        <div className="bg-pw-panel border border-white/[0.06] p-3.5 flex-1">
          <PanelLabel>PREDICTED FINISH — LIVE</PanelLabel>
          {preds.length ? (
            <div className="max-h-64 overflow-y-auto no-scrollbar pr-1">
              {preds.map((p, i) => (
                <div
                  key={p.abbreviation}
                  className={`flex justify-between items-center text-[11.5px] text-white py-1.5 ${i === preds.length - 1 ? "" : "border-b border-white/[0.05]"}`}
                >
                  <span>P{p.model_pos} · {DRIVER_NAMES[p.abbreviation]?.split(" ").slice(-1)[0] || p.abbreviation}</span>
                  {p.delta === 0
                    ? <span className="text-pw-muted">—</span>
                    : <span className={p.delta > 0 ? "text-pw-safe" : "text-pw-red"}>{p.delta > 0 ? "▲" : "▼"}{Math.abs(p.delta)}</span>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-pw-muted text-xs py-2">
              {finishes && !finishes.active ? "No active weekend." : "Awaiting practice pace…"}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
