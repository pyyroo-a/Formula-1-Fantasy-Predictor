import { useState, useEffect } from "react";
import { API } from "./api";
import CountdownWidget from "./components/CountdownWidget";
import Overview from "./components/Overview";
import ManualTeamBuilder from "./components/ManualTeamBuilder";
import Garage from "./components/myteam/Garage";
import PredictedFinishes from "./components/PredictedFinishes";
import TrackRecord from "./components/TrackRecord";
import ChipHistory from "./components/ChipHistory";
import Backtest from "./components/Backtest";
import { cacheTeam, readCachedTeam, pickNewer } from "./teamCache";
import { useRaceWeekend } from "./hooks/useRaceData";
import RaceDataPage from "./components/racedata/RaceDataPage";
import ErrorBoundary from "./ui/ErrorBoundary";

// import.meta.env.DEV is true under `npm run dev` and false in a production
// build, so the Backtest tab never ships to the deployed site.
const IS_DEV = import.meta.env.DEV;

const NAV = [
  { id: "overview", label: "Overview" },
  { id: "myteam",   label: "My team" },
  { id: "racedata", label: "Race data" },
  { id: "insights", label: "Insights" },
];

// the Team Optimizer got dropped in the redesign: old races at today's prices wasn't
// this weekend's answer or what you could have scored. /predict-budget is still there
// the Garage took over the planner and the chip advisor (your saved teams, both
// answers at once)
const MYTEAM_TABS = [
  { id: "manual", label: "Manual team" },
  { id: "garage", label: "Garage" },
];

// project 5: the track record sits next to the predicted finishes
const INSIGHTS_TABS = [
  { id: "finishes", label: "Predicted finishes" },
  { id: "trackrecord", label: "Track record" },
  { id: "chips", label: "Chips" },
];

// race data is one page now, the session strip replaced the three tabs. Backtest is
// still there when running locally
const RACEDATA_TABS = IS_DEV ? [
  { id: "weekend",  label: "Race weekend" },
  { id: "backtest", label: "Backtest" },
] : null;

function App() {
  const [section, setSection] = useState("overview");
  const [myTeamTab, setMyTeamTab] = useState("manual");
  const [raceDataTab, setRaceDataTab] = useState("weekend");
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

  // Race data. The state stays up here in App (see hooks/useRaceData.js) so
  // switching pages doesn't forget the race you picked.
  const raceWeekend = useRaceWeekend();

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

  const navButton = (item, phone) => (
    <button
      key={item.id}
      onClick={() => setSection(item.id)}
      aria-current={section === item.id ? "page" : undefined}
      className={phone
        ? `flex-1 h-14 text-[13px] font-semibold ${section === item.id ? "text-pw-red" : "text-pw-muted"}`
        : `py-1 text-sm font-semibold whitespace-nowrap transition-colors ${section === item.id ? "text-pw-text shadow-[inset_0_-2px_0_#FF4D4D]" : "text-pw-muted hover:text-pw-text"}`}
    >
      {item.label}
    </button>
  );

  return (
    <div className="min-h-screen bg-pw-bg text-pw-text">
      <div className="max-w-6xl mx-auto min-h-screen pw-page-pad">

        {/* header: logo, the four sections (desktop), the countdown */}
        <header className="flex items-center justify-between gap-4 px-4 sm:px-5 pb-3 pt-[max(env(safe-area-inset-top),12px)] border-b border-pw-edge">
          <div className="flex items-center gap-6 min-w-0">
            {/* the fast P from the favicon, then the name */}
            <span className="flex items-center gap-2 flex-shrink-0">
              <img src="/favicon.svg" alt="" className="w-7 h-7" />
              <span className="cond-x font-extrabold text-2xl text-pw-red">PITWALL</span>
            </span>
            <nav className="hidden sm:flex gap-5">{NAV.map(item => navButton(item, false))}</nav>
          </div>
          <CountdownWidget nextRace={nextRace} />
        </header>

        {/* on a phone the sections sit at the bottom, where your thumb is */}
        <nav className="sm:hidden fixed bottom-0 inset-x-0 z-30 flex bg-pw-bg/95 backdrop-blur border-t border-pw-edge pw-bottom-nav">
          {NAV.map(item => navButton(item, true))}
        </nav>

        {/* sub tabs (My team, Race data, Insights) */}
        {subTabs && (
          <div className="flex gap-5 px-4 sm:px-5 pt-3 border-b border-pw-line overflow-x-auto no-scrollbar">
            {subTabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setSubTab(tab.id)}
                className={`pb-2 text-sm font-semibold whitespace-nowrap transition-colors ${
                  activeSubTab === tab.id ? "text-pw-text shadow-[inset_0_-2px_0_#E9ECF1]" : "text-pw-muted hover:text-pw-text"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}

        <main className="px-4 sm:px-5 pt-4 pb-16">
          <ErrorBoundary resetKey={`${section}/${activeSubTab}`}>

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
            {section === "insights" && insightsTab === "chips" && <ChipHistory />}

            {mode === "weekend" && section === "racedata" && <RaceDataPage races={races} weekend={raceWeekend} />}

            {mode === "manual" && section === "myteam" && <ManualTeamBuilder upcomingRaces={upcomingRaces} weekendTeam={overviewWeekend} />}
            {mode === "garage" && section === "myteam" && <Garage upcomingRaces={upcomingRaces} finishes={finishes} />}
            {mode === "backtest" && section === "racedata" && IS_DEV && <Backtest />}
          </ErrorBoundary>
        </main>

      </div>
    </div>
  );
}

export default App;
