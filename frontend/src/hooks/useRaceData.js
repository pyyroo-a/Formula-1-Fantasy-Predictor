import { useState } from "react";
import { API } from "../api";

// State and fetching for the Race Data tabs. These get
// called in App, not inside the tabs, on purpose: a tab unmounts when you switch
// away from it, and keeping the state up in App is what makes your picked race
// still be there when you come back.

export function useRaceResults() {
  const [resultsRace, setResultsRace] = useState("");
  const [raceResults, setRaceResults] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState(null);

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

  return { resultsRace, setResultsRace, raceResults, resultsLoading, resultsError, fetchRaceResults };
}

export function usePractice() {
  const [practiceRace, setPracticeRace] = useState("");
  const [practiceData, setPracticeData] = useState(null);   // { session, available_sessions, results }
  const [practiceLoading, setPracticeLoading] = useState(false);
  const [practiceError, setPracticeError] = useState(null);

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

  return {
    practiceRace, setPracticeRace, practiceData, setPracticeData,
    practiceLoading, practiceError, setPracticeError, fetchPractice,
  };
}

export function useQualifying() {
  const [qualRace, setQualRace] = useState("");
  const [qualResults, setQualResults] = useState(null);
  const [qualLoading, setQualLoading] = useState(false);
  const [qualError, setQualError] = useState(null);

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

  return {
    qualRace, setQualRace, qualResults, setQualResults,
    qualLoading, qualError, setQualError, fetchQualifying,
  };
}
