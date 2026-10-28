import { teamAccent } from "../constants";
import { money, fmt1, surname } from "../lib/format";
import { groupByTeam, sortDrivers, sortConstructors } from "../lib/picker";
import Switcher from "./Switcher";

const SORTS = [
  { id: "team", label: "By team" },
  { id: "points", label: "By points" },
  { id: "price", label: "By price" },
];

function Card({ color, title, line, price, picked, disabled, onClick, unknown }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-pressed={picked}
      className={`text-left min-w-0 rounded-md border border-l-[3px] px-2 py-1.5 transition-colors ${
        picked ? "bg-[#22161A] border-pw-red" : disabled ? "bg-pw-raised/50 border-pw-line opacity-40 cursor-not-allowed" : "bg-pw-raised border-pw-line hover:border-pw-edge"
      }`}
      style={{ borderLeftColor: color }}
    >
      <div className="cond font-bold text-[15px] leading-tight truncate">{title}</div>
      <div className="flex justify-between gap-2 text-[11px] text-pw-muted num">
        <span className="truncate">{unknown ? "not in the price list" : line}</span>
        <span className="flex-shrink-0">{price}</span>
      </div>
    </button>
  );
}

// The picker Manual team and the Garage share: drivers grouped by team (teams A to Z,
// teammates side by side) or sorted by points or price, then constructors A to Z.
// Everything wears its team colour so you can spot people fast.
//   drivers:      [{ Abbreviation, TeamName, Price, FantasyValue?, Predicted?, unknown? }]
//   constructors: [{ name, price, score?, unknown? }]
//   picked:       { drivers: [codes], constructors: [names] }
export default function TeamPicker({ drivers, constructors, picked, onToggleDriver, onToggleConstructor, sort = "team", onSort, showPoints = true }) {
  const driverFull = picked.drivers.length >= 5;
  const consFull = picked.constructors.length >= 2;

  const driverCard = d => {
    const on = picked.drivers.includes(d.Abbreviation);
    const line = showPoints && d.FantasyValue != null
      ? `${d.Predicted != null ? `P${Math.round(d.Predicted)}, ` : ""}${fmt1(d.FantasyValue)} pts`
      : d.TeamName || "";
    return (
      <Card
        key={d.Abbreviation}
        color={teamAccent(d.TeamName)}
        title={surname(d.Abbreviation)}
        line={line}
        price={d.Price != null ? money(d.Price) : ""}
        picked={on}
        unknown={d.unknown}
        disabled={!on && driverFull}
        onClick={() => onToggleDriver(d.Abbreviation)}
      />
    );
  };

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <h3 className="cond font-bold text-[17px]">Drivers <span className="text-xs text-pw-muted font-normal">pick 5</span></h3>
        {onSort && <Switcher className="w-full sm:w-[280px]" options={SORTS} value={sort} onChange={onSort} />}
      </div>

      {sort === "team" ? (
        groupByTeam(drivers).map(g => (
          <div key={g.team} className="grid grid-cols-2 sm:grid-cols-[120px_1fr_1fr] gap-1.5 items-center py-1 border-b border-pw-line">
            <div className="col-span-2 sm:col-span-1 flex items-center gap-2 text-xs sm:text-[13px] font-semibold text-pw-muted sm:text-pw-text">
              <span className="w-2.5 h-[3px] sm:w-1 sm:h-6 rounded-sm" style={{ background: g.team === "Other" ? "#5A6170" : teamAccent(g.team) }} />
              <span className="truncate">{g.team}</span>
            </div>
            {g.drivers.map(driverCard)}
          </div>
        ))
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">{sortDrivers(drivers, sort).map(driverCard)}</div>
      )}

      <h3 className="cond font-bold text-[17px] mt-4 mb-2">Constructors <span className="text-xs text-pw-muted font-normal">pick 2, A to Z</span></h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
        {sortConstructors(constructors).map(c => {
          const on = picked.constructors.includes(c.name);
          return (
            <Card
              key={c.name}
              color={teamAccent(c.name)}
              title={c.name}
              line={showPoints && c.score != null ? `${fmt1(c.score)} pts` : ""}
              price={c.price != null ? money(c.price) : ""}
              picked={on}
              unknown={c.unknown}
              disabled={!on && consFull}
              onClick={() => onToggleConstructor(c.name)}
            />
          );
        })}
      </div>
    </div>
  );
}
