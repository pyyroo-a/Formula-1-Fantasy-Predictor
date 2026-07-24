import { useState, useEffect } from "react";
import { API } from "./api";
import CountdownWidget from "./components/CountdownWidget";
import WeekendTeamWidget from "./components/WeekendTeamWidget";
import WeatherWidget from "./components/WeatherWidget";
import RaceResultsTable from "./components/RaceResultsTable";
import QualifyingTable from "./components/QualifyingTable";
import { BudgetBar, BudgetDriverCard, ConstructorCard, BoostPickCard } from "./components/BudgetTeam";
import ManualTeamBuilder from "./components/ManualTeamBuilder";
import ChipAdvisor from "./components/ChipAdvisor";
import PredictedFinishes from "./components/PredictedFinishes";
import Backtest from "./components/Backtest";
import { DriverPricesCard, ConstructorPricesCard } from "./components/PricesSidebar";

// import.meta.env.DEV is true under `npm run dev` and false in a production
// build — so the Backtest tab never ships to the deployed site.
const IS_DEV = import.meta.env.DEV;

const TAB_GROUPS = [
  {
    label: "My Team",
    tabs: [
      { id: "budget", label: "Budget Team" },
      { id: "manual", label: "Manual Team" },
      { id: "chips",  label: "Chip Advisor" },
    ],
  },
  {
    label: "Race Data",
    tabs: [
      { id: "results",    label: "Race Results" },
      { id: "qualifying", label: "Qualifying" },
      { id: "finishes",   label: "Predicted Finishes" },
      ...(IS_DEV ? [{ id: "backtest", label: "Backtest" }] : []),
    ],
  },
];

function App() {
  const [mode, setMode] = useState("budget");
  const [races, setRaces] = useState([]);
  const [upcomingRaces, setUpcomingRaces] = useState([]);
  const [nextRace, setNextRace] = useState(null);
  const [priceChanges, setPriceChanges] = useState(null);

  // Race Results tab
  const [resultsRace, setResultsRace] = useState("");
  const [raceResults, setRaceResults] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState(null);

  // Qualifying tab
  const [qualRace, setQualRace] = useState("");
  const [qualResults, setQualResults] = useState(null);
  const [qualLoading, setQualLoading] = useState(false);
  const [qualError, setQualError] = useState(null);

  // Budget Team tab
  const [budgetRace, setBudgetRace] = useState("");
  const [budgetTeams, setBudgetTeams] = useState(null);
  const [activeTeam, setActiveTeam] = useState(0);
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [budgetError, setBudgetError] = useState(null);

  useEffect(() => {
    fetch(`${API}/races`).then(r => r.json()).then(setRaces).catch(() => {});
    fetch(`${API}/upcoming-races`).then(r => r.json()).then(setUpcomingRaces).catch(() => {});
    fetch(`${API}/next-race`).then(r => r.json()).then(setNextRace).catch(() => {});
    fetch(`${API}/price-changes`).then(r => r.json()).then(setPriceChanges).catch(() => {});
  }, []);

  const fetchRaceResults = async (raceName) => {
    if (!raceName) return;
    setResultsLoading(true); setResultsError(null); setRaceResults(null);
    try {
      const res = await fetch(`${API}/race-results`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: raceName }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setRaceResults(data);
    } catch (e) { setResultsError(e.message || "Failed to load race results."); }
    setResultsLoading(false);
  };

  const fetchQualifying = async () => {
    if (!qualRace) return;
    setQualLoading(true); setQualError(null); setQualResults(null);
    try {
      const res = await fetch(`${API}/qualifying-results`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: qualRace }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setQualResults(data);
    } catch (e) { setQualError(e.message || "Failed to load qualifying data."); }
    setQualLoading(false);
  };

  const fetchBudgetTeam = async () => {
    if (!budgetRace) return;
    setBudgetLoading(true); setBudgetError(null); setBudgetTeams(null); setActiveTeam(0);
    try {
      const res = await fetch(`${API}/predict-budget`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: budgetRace, budget: 100.0 }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setBudgetTeams(data.teams);
    } catch (e) { setBudgetError(e.message || "Failed to build budget team."); }
    setBudgetLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-screen-xl mx-auto px-4 sm:px-6">

        {/* ── Top navbar ── */}
        <div className="flex flex-wrap items-center justify-between gap-y-2 py-5 border-b border-gray-800 mb-5">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black tracking-tight">PitWall</h1>
            <span className="text-gray-500 text-sm">F1 Fantasy · 2026 Season</span>
          </div>
          <CountdownWidget nextRace={nextRace} />
        </div>

        {/* ── Info row: weather | driver prices | constructor prices ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
          <div className="h-44"><WeatherWidget nextRace={nextRace} /></div>
          <div className="h-44"><DriverPricesCard priceChanges={priceChanges} /></div>
          <div className="h-44"><ConstructorPricesCard priceChanges={priceChanges} /></div>
        </div>

        {/* ── Weekend lineup (only shown near race weekend) ── */}
        <WeekendTeamWidget />

        {/* ── Tabs — grouped by purpose ── */}
        <div className="flex flex-col sm:flex-row gap-4 sm:gap-8 mb-5">
          {TAB_GROUPS.map(group => (
            <div key={group.label}>
              <p className="text-[11px] text-gray-500 uppercase tracking-widest mb-2">{group.label}</p>
              <div className="flex rounded-lg overflow-x-auto border border-gray-700 bg-gray-800/40 w-max max-w-full">
                {group.tabs.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setMode(tab.id)}
                    className={`py-2.5 px-4 text-xs font-medium transition whitespace-nowrap ${
                      mode === tab.id ? "bg-red-600 text-white" : "bg-transparent text-gray-400 hover:bg-gray-700"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* ── Tab content ── */}
        <div className="pb-12">

          {mode === "results" && (
            <>
              <select
                value={resultsRace}
                onChange={e => { setResultsRace(e.target.value); fetchRaceResults(e.target.value); }}
                className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-4"
              >
                <option value="">Select a completed race</option>
                {races.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
              {resultsLoading && <p className="text-gray-400 text-sm text-center">Loading results...</p>}
              {resultsError && <p className="text-red-400 text-sm text-center">{resultsError}</p>}
              {raceResults && (
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Race Results</h2>
                    <span className="text-xs text-gray-600">{resultsRace}</span>
                  </div>
                  <RaceResultsTable results={raceResults} />
                </div>
              )}
            </>
          )}

          {mode === "qualifying" && (
            <>
              <select
                value={qualRace}
                onChange={e => { setQualRace(e.target.value); setQualResults(null); setQualError(null); }}
                className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-3"
              >
                <option value="">Select a completed race</option>
                {races.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
              {qualRace && !qualResults && !qualLoading && (
                <button onClick={fetchQualifying} className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 transition font-medium mb-4">
                  Load Qualifying Results
                </button>
              )}
              {qualLoading && (
                <div className="text-center mb-4">
                  <p className="text-gray-400 text-sm">Fetching qualifying data from FastF1...</p>
                  <p className="text-gray-600 text-xs mt-1">May take 15–30 seconds on first load</p>
                </div>
              )}
              {qualError && <p className="text-red-400 text-sm text-center mb-4">{qualError}</p>}
              {qualResults && (
                <div>
                  <div className="flex justify-between items-center mb-3">
                    <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Qualifying</h2>
                    <span className="text-xs text-gray-600">{qualRace}</span>
                  </div>
                  <QualifyingTable results={qualResults} />
                </div>
              )}
            </>
          )}

          {mode === "budget" && (
            <>
              <p className="text-gray-400 text-sm text-center mb-4">
                Generates 3 high-scoring lineups within $100M — pick whichever suits your strategy.
              </p>
              <select
                value={budgetRace}
                onChange={e => { setBudgetRace(e.target.value); setBudgetTeams(null); setActiveTeam(0); }}
                className="w-full p-3 rounded-lg bg-gray-800 text-white border border-gray-700 mb-4"
              >
                <option value="">Select a race</option>
                {races.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
              <button
                onClick={fetchBudgetTeam}
                disabled={!budgetRace || budgetLoading}
                className="w-full p-3 rounded-lg bg-red-600 hover:bg-red-700 disabled:bg-gray-600 transition font-medium"
              >
                {budgetLoading ? "Solving..." : "Build Optimal Teams"}
              </button>
              {budgetError && <p className="mt-4 text-red-400 text-sm text-center">{budgetError}</p>}
              {budgetTeams && budgetTeams.length > 0 && (() => {
                const team = budgetTeams[activeTeam];
                return (
                  <div className="mt-6">
                    {/* Team switcher */}
                    <div className="flex rounded-lg overflow-hidden border border-gray-700 mb-5">
                      {budgetTeams.map((t, i) => (
                        <button
                          key={i}
                          onClick={() => setActiveTeam(i)}
                          className={`flex-1 py-2.5 text-sm font-medium transition ${
                            activeTeam === i
                              ? "bg-red-600 text-white"
                              : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                          }`}
                        >
                          Team {i + 1}
                          <span className={`block text-xs mt-0.5 ${activeTeam === i ? "text-red-200" : "text-gray-600"}`}>
                            {t.total_score?.toFixed(1)} pts · ${t.total_cost}M
                          </span>
                        </button>
                      ))}
                    </div>

                    <BudgetBar used={team.total_cost} />
                    <BoostPickCard pick={team.boost_pick} />
                    <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Drivers</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                      {team.drivers.map((driver, i) => (
                        <BudgetDriverCard
                          key={i}
                          driver={driver}
                          isCaptain={driver.Abbreviation === team.boost_pick?.Abbreviation}
                        />
                      ))}
                    </div>
                    <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Constructors</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {team.constructors.map((c, i) => <ConstructorCard key={i} constructor={c} />)}
                    </div>
                  </div>
                );
              })()}
            </>
          )}

          {mode === "manual" && <ManualTeamBuilder upcomingRaces={upcomingRaces} />}
          {mode === "chips" && <ChipAdvisor upcomingRaces={upcomingRaces} />}
          {mode === "finishes" && <PredictedFinishes />}
          {mode === "backtest" && IS_DEV && <Backtest />}
        </div>

      </div>
    </div>
  );
}

export default App;
