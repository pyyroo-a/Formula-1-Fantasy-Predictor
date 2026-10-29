import { useState } from "react";
import { teamAccent } from "../constants";
import { finishRows, rightSpot } from "../lib/finishes";
import Switcher from "../ui/Switcher";
import Loading, { ErrorLine } from "../ui/Loading";

const STATE_TAG = {
  held: ["Held", "bg-[#1E1A10] text-pw-caution"],
  locked: ["Locked", "bg-[#163222] text-pw-safe"],
  provisional: ["Provisional", "bg-[#141B2C] text-pw-info"],
};

const PILL = {
  exact: "bg-[#163222] text-pw-safe ring-1 ring-pw-safe/60",
  close: "bg-[#163222] text-pw-safe",
  off: "bg-pw-edge text-pw-muted",
  dnf: "bg-[#3A1D22] text-pw-low",
};

// the slim list: predicted spot, driver, practice spot, and the real finish once it's in
function List({ rows, hasActual }) {
  const cols = hasActual ? "grid-cols-[36px_1fr_56px_72px]" : "grid-cols-[36px_1fr_56px]";
  return (
    <div className="bg-pw-panel rounded-xl px-3 py-1.5">
      <div className={`grid ${cols} gap-2 text-[11px] text-pw-muted py-1 border-b border-pw-edge`}>
        <span>Pred</span><span>Driver</span><span className="text-center">Practice</span>
        {hasActual && <span className="text-right">Finished</span>}
      </div>
      {rows.map(r => (
        <div key={r.code} className={`grid ${cols} gap-2 items-center py-1.5 border-b border-pw-line last:border-0 text-[13px] num`}>
          <span className="cond font-bold text-[16px] text-pw-muted">P{r.spot}</span>
          <span className="flex items-center gap-2 min-w-0">
            <i className="w-1 h-5 rounded-sm flex-shrink-0" style={{ background: teamAccent(r.team) }} />
            <b className="cond text-[15px] truncate">{r.name}</b>
            {/* the arrow: the model vs the plain practice order */}
            {r.delta !== 0 && <span className={`text-[11px] ${r.delta > 0 ? "text-pw-safe" : "text-pw-low"}`}>{r.delta > 0 ? "▲" : "▼"}{Math.abs(r.delta)}</span>}
          </span>
          <span className="text-center text-pw-muted">P{r.practice}</span>
          {hasActual && (
            <span className={`justify-self-end text-xs font-bold px-2 py-0.5 rounded-full ${PILL[r.status] || PILL.off}`}>
              {r.status === "dnf" ? "DNF" : r.finished != null ? `P${r.finished}` : "-"}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

const LINE = {
  exact: { stroke: "#5BE38A", width: 3.5 },
  close: { stroke: "#5BE38A", width: 1.8, opacity: 0.85 },
  off: { stroke: "#5A6170", width: 1.6 },
  dnf: { stroke: "#FF7A7A", width: 1.6, dash: "3 3" },
};

// before and after: each driver is a line from where we predicted them (left) to where
// they finished (right). Same height both ends = a flat line = we nailed it
function Lines({ rows }) {
  const total = rows.length;
  const rowH = 24, top = 26, W = 340, xl = 92, xr = W - 72;
  const y = spot => top + (spot - 1) * rowH;
  const H = y(total + 1) + 18;
  return (
    <div className="bg-pw-panel rounded-xl px-2 py-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[520px] mx-auto block" role="img"
           aria-label="Each driver's predicted spot joined to their real finish">
        <text x={xl} y={12} textAnchor="middle" fontSize="10" fill="#8B93A3">predicted</text>
        <text x={xr} y={12} textAnchor="middle" fontSize="10" fill="#8B93A3">finished</text>
        {Array.from({ length: total }, (_, i) => (
          <text key={i} x={xr + 12} y={y(i + 1) + 4} fontSize="10" fill="#5A6170">P{i + 1}</text>
        ))}
        <text x={xr + 12} y={y(total + 1) + 4} fontSize="10" fill="#FF7A7A">DNF</text>
        {/* far off lines first, so the green ones are drawn on top */}
        {[...rows].sort((a, b) => ["off", "dnf", "close", "exact"].indexOf(a.status) - ["off", "dnf", "close", "exact"].indexOf(b.status)).map(r => {
          const s = LINE[r.status] || LINE.off;
          const y1 = y(r.spot), y2 = y(rightSpot(r, total));
          return (
            <g key={r.code}>
              <title>{`${r.name}: predicted P${r.spot}, ${r.status === "dnf" ? "didn't finish" : `finished P${r.finished}`}`}</title>
              <line x1={xl + 6} y1={y1} x2={xr - 6} y2={y2} stroke={s.stroke} strokeWidth={s.width}
                    strokeOpacity={s.opacity ?? 1} strokeDasharray={s.dash} strokeLinecap="round" />
              <circle cx={xl + 6} cy={y1} r="3.5" fill={teamAccent(r.team)} />
              <circle cx={xr - 6} cy={y2} r="3.5" fill={r.status === "dnf" ? "#FF7A7A" : teamAccent(r.team)} />
              {r.status === "exact" && <text x={xr + 34} y={y2 + 4} fontSize="11" fontWeight="800" fill="#5BE38A">✓</text>}
            </g>
          );
        })}
        {rows.map(r => (
          <text key={r.code} x={xl - 4} y={y(r.spot) + 4} textAnchor="end" fontSize="11" fontWeight="700" fill="#E9ECF1">
            P{r.spot} {r.code}
          </text>
        ))}
      </svg>
      <p className="flex flex-wrap gap-x-3 gap-y-1 justify-center text-[11px] text-pw-muted mt-1">
        <span><b className="text-pw-safe">thick green ✓</b> spot on</span>
        <span><b className="text-pw-safe">thin green</b> within 1</span>
        <span><b className="text-pw-text">grey</b> further off</span>
        <span><b className="text-pw-low">red dashes</b> didn't finish</span>
      </p>
    </div>
  );
}

// Controlled: App owns the /weekend-finishes fetch and shares it with the
// Overview, so this component just renders whatever it's handed.
export default function PredictedFinishes({ data, loading, error }) {
  const [view, setView] = useState("list");

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
  const rows = finishRows(data.predictions, hasActual);
  // the lines need both ends, so they only show once the real results are in
  const showLines = hasActual && view === "lines";

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

      {hasActual && (
        <Switcher className="mb-3 sm:max-w-[260px]" value={view} onChange={setView}
          options={[{ id: "list", label: "List" }, { id: "lines", label: "Lines" }]} />
      )}

      {showLines ? <Lines rows={rows} /> : (
        <>
          <p className="text-xs text-pw-muted mb-1">
            Predicted spot on the left, practice order next to it{hasActual ? ", real finish on the right, green means within 1 place" : ""}.
          </p>
          <List rows={rows} hasActual={hasActual} />
        </>
      )}

      <p className="text-xs text-pw-muted mt-3 leading-relaxed max-w-[70ch]">
        Heads up: in backtesting, the plain practice order beat the model. Both are shown so you can judge which
        is closer each weekend, treat the model as an experiment. The arrow is the model vs the practice order.
      </p>
    </div>
  );
}
