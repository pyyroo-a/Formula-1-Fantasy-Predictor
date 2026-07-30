import { useState, useEffect } from "react";
import { API } from "./api";
import CountdownWidget from "./components/CountdownWidget";
import Overview from "./components/Overview";
import RaceResultsTable from "./components/RaceResultsTable";
import QualifyingTable from "./components/QualifyingTable";
import PracticeTable from "./components/PracticeTable";
import { TeamStatGrid, BudgetDriverCard, ConstructorCard, BoostPickCard } from "./components/BudgetTeam";
import ManualTeamBuilder from "./components/ManualTeamBuilder";
import ChipAdvisor from "./components/ChipAdvisor";
import PredictedFinishes from "./components/PredictedFinishes";
import Backtest from "./components/Backtest";

// import.meta.env.DEV is true under `npm run dev` and false in a production
// build — so the Backtest tab never ships to the deployed site.
const IS_DEV = import.meta.env.DEV;

const NAV = [
  { id: "overview", label: "OVERVIEW" },
  { id: "myteam",   label: "MY TEAM" },
  { id: "racedata", label: "RACE DATA" },
  { id: "insights", label: "INSIGHTS" },
];

const MYTEAM_TABS = [
  { id: "budget", label: "TEAM OPTIMIZER" },
  { id: "manual", label: "MANUAL TEAM" },
  { id: "chips",  label: "CHIP ADVISOR" },
];

const RACEDATA_TABS = [
  { id: "practice",   label: "PRACTICE" },
  { id: "qualifying", label: "QUALIFYING" },
  { id: "results",    label: "RACE RESULTS" },
  ...(IS_DEV ? [{ id: "backtest", label: "BACKTEST" }] : []),
];

function App() {
  const [section, setSection] = useState("overview");
  const [myTeamTab, setMyTeamTab] = useState("budget");
  const [raceDataTab, setRaceDataTab] = useState("practice");

  const [races, setRaces] = useState([]);
  const [upcomingRaces, setUpcomingRaces] = useState([]);
  const [nextRace, setNextRace] = useState(null);
  const [priceChanges, setPriceChanges] = useState(null);

  // Weekend lineup + auto chip advice share one fetch and one team selection.
  const [weekendData, setWeekendData] = useState(null);
  const [weekendActiveTeam, setWeekendActiveTeam] = useState(0);

  // Last active weekend team, cached so the Overview has something to show
  // between races ("hold this team" state) instead of an empty panel.
  const [lastTeam] = useState(() => {
    try { return JSON.parse(localStorage.getItem("pitwall_last_team") || "null"); }
    catch { return null; }
  });

  // Backend fallback for the very first between-races gap, before any live
  // weekend has been cached to localStorage. Rebuilds the most recent completed
  // race's team so the Overview is never empty.
  const [heldFallback, setHeldFallback] = useState(null);

  // Predicted finishes — fetched once, shared by Overview live-card + Insights.
  const [finishes, setFinishes] = useState(null);
  const [finishesLoading, setFinishesLoading] = useState(true);
  const [finishesError, setFinishesError] = useState(null);

  // Race Results tab
  const [resultsRace, setResultsRace] = useState("");
  const [raceResults, setRaceResults] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState(null);

  // Practice tab
  const [practiceRace, setPracticeRace] = useState("");
  const [practiceData, setPracticeData] = useState(null);   // { session, available_sessions, results }
  const [practiceLoading, setPracticeLoading] = useState(false);
  const [practiceError, setPracticeError] = useState(null);

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
    fetch(`${API}/weekend-team`).then(r => r.json()).then(d => {
      setWeekendData(d);
      // Persist the last live weekend so it can be held between races.
      if (d?.active && (d?.teams?.length || d?.team)) {
        try { localStorage.setItem("pitwall_last_team", JSON.stringify(d)); } catch {}
      } else if (!d?.active && !lastTeam) {
        // No live weekend and nothing cached yet — pull the last team from the
        // backend so the Overview isn't empty until localStorage starts filling.
        fetch(`${API}/last-team`).then(r => r.json())
          .then(h => { if (h?.held) setHeldFallback(h); })
          .catch(() => {});
      }
    }).catch(() => {});
    fetch(`${API}/weekend-finishes`)
      .then(r => r.json())
      .then(d => { if (d.detail) throw new Error(d.detail); setFinishes(d); })
      .catch(e => setFinishesError(e.message || "Failed to load predicted finishes."))
      .finally(() => setFinishesLoading(false));
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

  // session = "" lets the backend auto-pick the final practice session that ran
  // (FP3 normally, FP1 on sprint weekends), and tell us which sessions exist.
  const fetchPractice = async (raceName, session = "") => {
    if (!raceName) return;
    setPracticeLoading(true); setPracticeError(null);
    try {
      const res = await fetch(`${API}/practice-results`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ race_name: raceName, session }),
      });
      const data = await res.json();
      if (data.detail) throw new Error(data.detail);
      setPracticeData(data);
    } catch (e) { setPracticeError(e.message || "Failed to load practice data."); setPracticeData(null); }
    setPracticeLoading(false);
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

  // Derived mode keeps the existing content blocks working unchanged.
  const mode = section === "myteam" ? myTeamTab : raceDataTab;

  // Between races the live fetch is inactive — fall back to the cached team, or
  // the backend's last-team rebuild, so the Overview keeps showing a lineup,
  // flagged as "held". localStorage wins so the label tracks each race by name.
  const heldTeam = lastTeam || heldFallback;
  const held = !!(weekendData && !weekendData.active && heldTeam);
  const overviewWeekend = (weekendData && !weekendData.active) ? (heldTeam || weekendData) : weekendData;

  // Shared pit-wall form styling.
  const inputCls = "w-full p-2.5 bg-pw-panel2 text-white text-sm border border-white/10 outline-none focus:border-pw-red/50";
  const primaryBtn = "w-full p-2.5 bg-pw-red hover:bg-[#ff7676] text-white text-sm font-semibold transition disabled:bg-white/10 disabled:text-pw-muted disabled:cursor-not-allowed";
  const sectionHead = "text-xs text-pw-muted tracking-[0.08em] mb-3";

  const subTabs = section === "myteam" ? MYTEAM_TABS : section === "racedata" ? RACEDATA_TABS : null;
  const activeSubTab = section === "myteam" ? myTeamTab : raceDataTab;
  const setSubTab = section === "myteam" ? setMyTeamTab : setRaceDataTab;

  return (
    <div className="min-h-screen bg-pw-bg text-white font-mono">
      <div className="max-w-6xl mx-auto min-h-screen bg-[#05070c]">

        {/* ── Header: wordmark · nav · T-MINUS ── */}
        <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 sm:px-5 py-3 border-b border-[#ff5c5c]/25 bg-pw-panel2">
          <div className="flex items-center gap-3 sm:gap-6 min-w-0">
            <span className="font-extrabold text-lg sm:text-xl tracking-[0.05em] text-pw-red flex-shrink-0">PITWALL</span>
            <nav className="flex gap-1 sm:gap-2 overflow-x-auto no-scrollbar">
              {NAV.map(item => (
                <button
                  key={item.id}
                  onClick={() => setSection(item.id)}
                  className={`px-2.5 sm:px-3 py-1.5 text-[13px] sm:text-sm tracking-[0.04em] whitespace-nowrap transition ${
                    section === item.id
                      ? "text-white border-b-2 border-pw-red"
                      : "text-pw-muted hover:text-gray-300"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </div>
          <CountdownWidget nextRace={nextRace} />
        </header>

        {/* ── Section sub-tabs (My Team / Race Data) ── */}
        {subTabs && (
          <div className="flex gap-0.5 px-4 sm:px-5 pt-4 overflow-x-auto no-scrollbar">
            {subTabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setSubTab(tab.id)}
                className={`px-4 py-2.5 text-[11px] tracking-[0.04em] whitespace-nowrap transition ${
                  activeSubTab === tab.id
                    ? "bg-pw-panel text-white border border-[#ff5c5c]/30 border-b-0"
                    : "text-pw-muted border-b border-white/[0.08] hover:text-gray-300"
                }`}
              >
                {tab.label}
              </button>
            ))}
            <div className="flex-1 border-b border-white/[0.08]" />
          </div>
        )}

        {/* ── Section content ── */}
        <main className={`px-5 pb-16 ${subTabs ? "pt-0" : "pt-5"}`}>
          <div className={subTabs ? "bg-pw-panel border-x border-b border-[#ff5c5c]/30 p-5" : ""}>

            {section === "overview" && (
              <Overview
                nextRace={nextRace}
                weekendData={overviewWeekend}
                held={held}
                weekendActiveTeam={weekendActiveTeam}
                setWeekendActiveTeam={setWeekendActiveTeam}
                priceChanges={priceChanges}
                finishes={finishes}
              />
            )}

            {section === "insights" && (
              <PredictedFinishes data={finishes} loading={finishesLoading} error={finishesError} />
            )}

            {mode === "results" && section === "racedata" && (
              <>
                <select
                  value={resultsRace}
                  onChange={e => { setResultsRace(e.target.value); fetchRaceResults(e.target.value); }}
                  className={`${inputCls} mb-4`}
                >
                  <option value="">Select a completed race</option>
                  {races.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
                {resultsLoading && <p className="text-pw-muted text-sm text-center">Loading results…</p>}
                {resultsError && <p className="text-pw-red text-sm text-center">{resultsError}</p>}
                {raceResults && (
                  <div>
                    <p className={sectionHead}>{resultsRace?.toUpperCase()} · FINAL CLASSIFICATION</p>
                    <RaceResultsTable results={raceResults} />
                  </div>
                )}
              </>
            )}

            {mode === "practice" && section === "racedata" && (
              <>
                <select
                  value={practiceRace}
                  onChange={e => {
                    const r = e.target.value;
                    setPracticeRace(r); setPracticeData(null); setPracticeError(null);
                    if (r) fetchPractice(r);
                  }}
                  className={`${inputCls} mb-3`}
                >
                  <option value="">Select a race</option>
                  {races.map(r => <option key={r} value={r}>{r}</option>)}
                </select>

                {/* Session switcher — only the sessions that actually ran this weekend */}
                {practiceData?.available_sessions?.length > 0 && (
                  <div className="flex gap-0.5 mb-4">
                    {practiceData.available_sessions.map(s => (
                      <button
                        key={s}
                        onClick={() => fetchPractice(practiceRace, s)}
                        disabled={practiceLoading}
                        className={`px-4 py-2 text-[11px] font-medium transition ${
                          practiceData.session === s
                            ? "bg-pw-red text-white"
                            : "bg-pw-panel2 text-pw-muted hover:text-white"
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}

                {practiceLoading && (
                  <div className="text-center mb-4">
                    <p className="text-pw-muted text-sm">Fetching practice pace from FastF1…</p>
                    <p className="text-pw-muted/60 text-xs mt-1">May take 15–30 seconds on first load</p>
                  </div>
                )}
                {practiceError && <p className="text-pw-red text-sm text-center mb-4">{practiceError}</p>}
                {practiceData?.results?.length > 0 && !practiceLoading && (
                  <div>
                    <p className={sectionHead}>{practiceRace?.toUpperCase()} · {practiceData.session} PACE</p>
                    <PracticeTable results={practiceData.results} />
                  </div>
                )}
              </>
            )}

            {mode === "qualifying" && section === "racedata" && (
              <>
                <select
                  value={qualRace}
                  onChange={e => { setQualRace(e.target.value); setQualResults(null); setQualError(null); }}
                  className={`${inputCls} mb-3`}
                >
                  <option value="">Select a completed race</option>
                  {races.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
                {qualRace && !qualResults && !qualLoading && (
                  <button onClick={fetchQualifying} className={`${primaryBtn} mb-4`}>
                    Load Qualifying Results
                  </button>
                )}
                {qualLoading && (
                  <div className="text-center mb-4">
                    <p className="text-pw-muted text-sm">Fetching qualifying data from FastF1…</p>
                    <p className="text-pw-muted/60 text-xs mt-1">May take 15–30 seconds on first load</p>
                  </div>
                )}
                {qualError && <p className="text-pw-red text-sm text-center mb-4">{qualError}</p>}
                {qualResults && (
                  <div>
                    <p className={sectionHead}>{qualRace?.toUpperCase()} · QUALIFYING</p>
                    <QualifyingTable results={qualResults} />
                  </div>
                )}
              </>
            )}

            {mode === "budget" && section === "myteam" && (
              <>
                <p className="text-pw-muted text-sm text-center mb-4">
                  Generates 3 high-scoring lineups within $100M — pick whichever suits your strategy.
                </p>
                <select
                  value={budgetRace}
                  onChange={e => { setBudgetRace(e.target.value); setBudgetTeams(null); setActiveTeam(0); }}
                  className={`${inputCls} mb-3`}
                >
                  <option value="">Select a race</option>
                  {races.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
                <button
                  onClick={fetchBudgetTeam}
                  disabled={!budgetRace || budgetLoading}
                  className={primaryBtn}
                >
                  {budgetLoading ? "Solving…" : "Build Optimal Teams"}
                </button>
                {budgetError && <p className="mt-4 text-pw-red text-sm text-center">{budgetError}</p>}
                {budgetTeams && budgetTeams.length > 0 && (() => {
                  const team = budgetTeams[activeTeam];
                  return (
                    <div className="mt-6">
                      {/* Team switcher */}
                      <div className="flex gap-0.5 mb-4">
                        {budgetTeams.map((t, i) => (
                          <button
                            key={i}
                            onClick={() => setActiveTeam(i)}
                            className={`flex-1 py-2 text-[11px] font-medium transition ${
                              activeTeam === i
                                ? "bg-pw-red text-white"
                                : "bg-pw-panel2 text-pw-muted hover:text-white"
                            }`}
                          >
                            TEAM {i + 1}
                            <span className={`block text-[10px] mt-0.5 ${activeTeam === i ? "text-white/70" : "text-pw-muted/70"}`}>
                              {t.total_score?.toFixed(1)} pts · ${t.total_cost}M
                            </span>
                          </button>
                        ))}
                      </div>

                      <TeamStatGrid used={team.total_cost} remaining={team.budget_remaining} score={team.total_score} />
                      <BoostPickCard pick={team.boost_pick} />
                      <p className={sectionHead}>DRIVERS</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-5">
                        {team.drivers.map((driver, i) => (
                          <BudgetDriverCard
                            key={i}
                            driver={driver}
                            isCaptain={driver.Abbreviation === team.boost_pick?.Abbreviation}
                          />
                        ))}
                      </div>
                      <p className={sectionHead}>CONSTRUCTORS</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {team.constructors.map((c, i) => <ConstructorCard key={i} constructor={c} />)}
                      </div>
                    </div>
                  );
                })()}
              </>
            )}

            {mode === "manual" && section === "myteam" && <ManualTeamBuilder upcomingRaces={upcomingRaces} />}
            {mode === "chips" && section === "myteam" && <ChipAdvisor upcomingRaces={upcomingRaces} />}
            {mode === "backtest" && section === "racedata" && IS_DEV && <Backtest />}
          </div>
        </main>

      </div>
    </div>
  );
}

export default App;
