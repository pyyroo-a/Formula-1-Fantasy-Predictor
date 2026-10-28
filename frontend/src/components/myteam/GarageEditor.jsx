import { useState } from "react";
import { INPUT_CLS, PRIMARY_BTN_CLS } from "../../styles";
import { money } from "../../lib/format";
import { pickerDrivers, teamFromSaved } from "../../lib/garage";
import Switcher from "../../ui/Switcher";
import TeamPicker from "../../ui/TeamPicker";

// Adding or changing one of your real teams. Same picker as Manual team, but it works
// before practice exists: drivers and prices come from /prices, the teams from the
// predicted finish list. A pick that isn't in today's price list stays, marked.
export default function GarageEditor({ team, prices, teamMap, onSave, onCancel }) {
  const start = teamFromSaved(team, prices);
  const [name, setName] = useState(team.name);
  const [budget, setBudget] = useState(team.budget);
  const [budgetText, setBudgetText] = useState(String(team.budget));
  const [free, setFree] = useState(team.freeTransfers);
  const [drivers, setDrivers] = useState(start.drivers.map(d => d.code));
  const [constructors, setConstructors] = useState(start.constructors.map(c => c.name));
  const [sort, setSort] = useState("team");

  const driverList = [
    ...pickerDrivers(prices, teamMap),
    ...start.drivers.filter(d => !d.known).map(d => ({ Abbreviation: d.code, TeamName: null, Price: null, unknown: true })),
  ];
  const constructorList = [
    ...Object.entries(prices?.constructors || {}).map(([n, price]) => ({ name: n, price })),
    ...start.constructors.filter(c => !c.known).map(c => ({ name: c.name, price: null, unknown: true })),
  ];

  const toggle = (list, setList, max) => (id) =>
    setList(list.includes(id) ? list.filter(x => x !== id) : list.length < max ? [...list, id] : list);

  const cost = drivers.reduce((s, c) => s + (prices?.drivers?.[c] ?? 0), 0)
    + constructors.reduce((s, n) => s + (prices?.constructors?.[n] ?? 0), 0);
  const complete = drivers.length === 5 && constructors.length === 2;
  const over = cost > budget;

  const onBudget = (text) => {
    setBudgetText(text);
    const n = parseFloat(text);
    if (Number.isFinite(n) && n > 0) setBudget(n);
  };

  return (
    <div className="pb-16 sm:pb-0">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mb-2">
        <label className="text-xs text-pw-muted">Team name
          <input value={name} onChange={e => setName(e.target.value)} className={`${INPUT_CLS} mt-1`} />
        </label>
        <label className="text-xs text-pw-muted">Budget in the game ($M)
          <input type="number" step="0.1" min="0" value={budgetText} onChange={e => onBudget(e.target.value)}
            onBlur={() => setBudgetText(String(budget))} className={`${INPUT_CLS} mt-1 num`} />
        </label>
        <div className="text-xs text-pw-muted">Free transfers this week
          <Switcher className="mt-1" value={free} onChange={setFree}
            options={[1, 2, 3].map(n => ({ id: n, label: String(n) }))} />
        </div>
      </div>
      <p className="text-xs text-pw-muted mb-4">
        Budget is your team value plus the bank. You get 2 free transfers a week, pick 3 if you saved one last week.
      </p>

      <TeamPicker
        drivers={driverList}
        constructors={constructorList}
        picked={{ drivers, constructors }}
        onToggleDriver={toggle(drivers, setDrivers, 5)}
        onToggleConstructor={toggle(constructors, setConstructors, 2)}
        sort={sort}
        onSort={setSort}
        showPoints={false}
      />

      <div className="fixed sm:sticky bottom-[45px] sm:bottom-0 inset-x-0 z-20 mt-4 bg-pw-panel border-t border-pw-edge sm:rounded-xl px-4 py-2.5 flex items-center justify-between gap-3">
        <div className="text-xs text-pw-muted num">
          <b className="text-pw-text">{drivers.length}/5</b> drivers, <b className="text-pw-text">{constructors.length}/2</b> constructors
          <span className="block"><b className={over ? "text-pw-low" : "text-pw-text"}>{money(cost)}</b> of {money(budget)}</span>
        </div>
        <div className="flex gap-2">
          <button onClick={onCancel} className="px-3 py-2 text-sm rounded-lg border border-pw-edge">Cancel</button>
          <button
            onClick={() => onSave({ ...team, name: name.trim() || team.name, budget, freeTransfers: free, drivers, constructors })}
            disabled={!complete}
            className={`${PRIMARY_BTN_CLS} w-auto px-4`}
          >
            Save team
          </button>
        </div>
      </div>
    </div>
  );
}
