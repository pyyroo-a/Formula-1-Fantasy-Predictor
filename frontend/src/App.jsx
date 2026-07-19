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
import { DriverPricesCard, ConstructorPricesCard } from "./components/PricesSidebar";

const TABS = [
  { id: "results",    label: "Race Results" },
  { id: "qualifying", label: "Qualifying" },
  { id: "budget",     label: "Budget Team" },
  { id: "manual",     label: "Manual Team" },
  { id: "chips",      label: "Chip Advisor" },
];

function App() {
  const [mode, setMode] = useState("results");
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
  const [budgetTeam, setBudgetTeam] = useState(null);
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
    setBudgetLoading(true); setBudgetError(null); setBudgetTeam(null);
    try {
      const res = await fetch(`${API}/predict-budget`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: budgetRace, budget: 100.0 }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setBudgetTeam(data);
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

        {/* ── Tabs ── */}
        <div className="overflow-x-auto mb-5">
          <div className="flex rounded-lg overflow-hidden border border-gray-700 min-w-max sm:min-w-0">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setMode(tab.id)}
                className={`flex-1 py-2.5 text-xs font-medium transition px-3 min-w-[90px] sm:min-w-0 whitespace-nowrap ${
                  mode === tab.id ? "bg-red-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
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
                Finds the highest-scoring 5 drivers + 2 constructors within the $100M budget.
              </p>
              <select
                value={budgetRace}
                onChange={e => { setBudgetRace(e.target.value); setBudgetTeam(null); }}
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
                {budgetLoading ? "Solving..." : "Build Optimal Team"}
              </button>
              {budgetError && <p className="mt-4 text-red-400 text-sm text-center">{budgetError}</p>}
              {budgetTeam && (
                <div className="mt-6">
                  <BudgetBar used={budgetTeam.total_cost} />
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-semibold text-gray-200">Optimal Team</h2>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">Total score</p>
                      <p className="text-white font-bold">{budgetTeam.total_score?.toFixed(2)}</p>
                    </div>
                  </div>
                  <BoostPickCard pick={budgetTeam.boost_pick} />
                  <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Drivers</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    {budgetTeam.drivers.map((driver, i) => (
                      <BudgetDriverCard
                        key={i}
                        driver={driver}
                        isCaptain={driver.Abbreviation === budgetTeam.boost_pick?.Abbreviation}
                      />
                    ))}
                  </div>
                  <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Constructors</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {budgetTeam.constructors.map((c, i) => <ConstructorCard key={i} constructor={c} />)}
                  </div>
                </div>
              )}
            </>
          )}

          {mode === "manual" && <ManualTeamBuilder upcomingRaces={upcomingRaces} />}
          {mode === "chips" && <ChipAdvisor upcomingRaces={upcomingRaces} />}
        </div>

      </div>
    </div>
  );
}

export default App;
