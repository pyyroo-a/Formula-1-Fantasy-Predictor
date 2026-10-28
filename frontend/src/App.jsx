import { useState, useEffect } from "react";
import { API } from "./api";
import CountdownWidget from "./components/CountdownWidget";
import Overview from "./components/Overview";
import RaceResultsTab from "./components/racedata/RaceResultsTab";
import PracticeTab from "./components/racedata/PracticeTab";
import QualifyingTab from "./components/racedata/QualifyingTab";
import TeamOptimizerTab from "./components/myteam/TeamOptimizerTab";
import ManualTeamBuilder from "./components/ManualTeamBuilder";
import ChipAdvisor from "./components/ChipAdvisor";
import TransferPlanner from "./components/myteam/TransferPlanner";
import PredictedFinishes from "./components/PredictedFinishes";
import TrackRecord from "./components/TrackRecord";
import Backtest from "./components/Backtest";
import { cacheTeam, readCachedTeam, pickNewer } from "./teamCache";
import { useRaceResults, usePractice, useQualifying, useBudgetTeams } from "./hooks/useRaceData";

// import.meta.env.DEV is true under `npm run dev` and false in a production
// build, so the Backtest tab never ships to the deployed site.
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
  { id: "planner", label: "PLANNER" },
];

// project 5: the track record sits next to the predicted finishes
const INSIGHTS_TABS = [
  { id: "finishes", label: "PREDICTED FINISHES" },
  { id: "trackrecord", label: "TRACK RECORD" },
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
  const [insightsTab, setInsightsTab] = useState("finishes");

  const [races, setRaces] = useState([]);
  const [upcomingRaces, setUpcomingRaces] = useState([]);
  const [nextRace, setNextRace] = useState(null);
  const [priceChanges, setPriceChanges] = useState(null);

  // Weekend lineup + auto chip advice share one fetch and one team selection.
  const [weekendData, setWeekendData] = useState(null);
  const [weekendActiveTeam, setWeekendActiveTeam] = useState(0);

  // Last active weekend team, cached so the Overview has something to show
  // between races ("hold this team" state) instead of an empty panel.
  //
  // This cache is per-device. That was the bug behind the phone showing the
  // Dutch GP team while the laptop showed Monza: whichever race you happened to
  // last open the site on is the team that device kept, forever. It is now only
  // a starting point, reconciled against the backend below.
  const [lastTeam, setLastTeam] = useState(readCachedTeam);

  // The backend's answer for "what was the last team?". Always fetched between
  // races now, not just when the local cache is empty.
  const [heldFallback, setHeldFallback] = useState(null);

  // Predicted finishes, fetched once, shared by Overview live-card + Insights.
  const [finishes, setFinishes] = useState(null);
  const [finishesLoading, setFinishesLoading] = useState(true);
  const [finishesError, setFinishesError] = useState(null);

  // Race Data tabs and the Team Optimizer. The state stays up here in App (see
  // hooks/useRaceData.js) so switching tabs doesn't forget the race you picked.
  const results = useRaceResults();
  const practice = usePractice();
  const qualifying = useQualifying();
  const budget = useBudgetTeams();

  useEffect(() => {
    fetch(`${API}/races`).then(r => r.json()).then(setRaces).catch(() => {});
    fetch(`${API}/upcoming-races`).then(r => r.json()).then(setUpcomingRaces).catch(() => {});
    fetch(`${API}/next-race`).then(r => r.json()).then(setNextRace).catch(() => {});
    fetch(`${API}/price-changes`).then(r => r.json()).then(setPriceChanges).catch(() => {});
    fetch(`${API}/weekend-team`).then(r => r.json()).then(d => {
      setWeekendData(d);
      if (d?.active && (d?.teams?.length || d?.team)) {
        // Live weekend: this is the truth, so overwrite the device cache.
        cacheTeam(d);
        setLastTeam(d);
      } else if (!d?.active) {
        // Between races. Always ask the backend rather than trusting whatever
        // this particular device happens to be holding, otherwise two devices
        // drift apart and never reconcile.
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

  // Derived mode keeps the existing content blocks working unchanged.
  const mode = section === "myteam" ? myTeamTab : raceDataTab;

  // Between races the live fetch is inactive, so the Overview shows a "held"
  // lineup instead of an empty panel. Two candidates exist and they can
  // disagree, which is what made the phone and the laptop show different teams:
  //
  //   lastTeam     - this device's cache. Can be stale by several races if the
  //                  device was not opened during the most recent weekend.
  //   heldFallback - the backend's answer. Authoritative, but it can lag by one
  //                  race, because after a race finishes the lock file is gone
  //                  (Render wipes it on redeploy) and the rebuild path needs
  //                  that race's results to have been committed first.
  //
  // Neither one is reliably newer, so pick by round number rather than by
  // preferring one source. Every team payload now carries `round`.
  const heldTeam = pickNewer(lastTeam, heldFallback);

  // Self-heal: if the backend knew about a later race than this device did,
  // write it back so the device stops being stale from here on.
  useEffect(() => {
    if (heldTeam && heldTeam !== lastTeam) {
      cacheTeam(heldTeam);
      setLastTeam(heldTeam);
    }
  }, [heldTeam, lastTeam]);
  const held = !!(weekendData && !weekendData.active && heldTeam);
  const overviewWeekend = (weekendData && !weekendData.active) ? (heldTeam || weekendData) : weekendData;

  const subTabs = section === "myteam" ? MYTEAM_TABS : section === "racedata" ? RACEDATA_TABS
    : section === "insights" ? INSIGHTS_TABS : null;
  const activeSubTab = section === "myteam" ? myTeamTab : section === "insights" ? insightsTab : raceDataTab;
  const setSubTab = section === "myteam" ? setMyTeamTab : section === "insights" ? setInsightsTab : setRaceDataTab;

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

            {section === "insights" && insightsTab === "finishes" && (
              <PredictedFinishes data={finishes} loading={finishesLoading} error={finishesError} />
            )}
            {section === "insights" && insightsTab === "trackrecord" && <TrackRecord />}

            {mode === "results" && section === "racedata" && <RaceResultsTab races={races} results={results} />}
            {mode === "practice" && section === "racedata" && <PracticeTab races={races} practice={practice} />}
            {mode === "qualifying" && section === "racedata" && <QualifyingTab races={races} qualifying={qualifying} />}
            {mode === "budget" && section === "myteam" && <TeamOptimizerTab races={races} budget={budget} />}

            {mode === "manual" && section === "myteam" && <ManualTeamBuilder upcomingRaces={upcomingRaces} />}
            {mode === "chips" && section === "myteam" && <ChipAdvisor upcomingRaces={upcomingRaces} />}
            {mode === "planner" && section === "myteam" && <TransferPlanner upcomingRaces={upcomingRaces} />}
            {mode === "backtest" && section === "racedata" && IS_DEV && <Backtest />}
          </div>
        </main>

      </div>
    </div>
  );
}

export default App;
