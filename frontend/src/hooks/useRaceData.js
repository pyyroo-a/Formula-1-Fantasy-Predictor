import { useState } from "react";
import { API } from "../api";
import { postJson } from "../lib/api";

// State and fetching for the Race data page. It gets called in App, not inside the
// page, on purpose: the page unmounts when you switch away from it, and keeping the
// state up in App is what makes your picked race still be there when you come back.
//
// One race, then a session from the strip (FP1 to Race). Every answer is kept, so
// going back to a session you already opened doesn't ask the server again.

const ENDPOINT = { Quali: "qualifying-results", Race: "race-results" };

export function useRaceWeekend() {
  const [race, setRaceName] = useState("");
  const [session, setSessionName] = useState("Race");
  const [answers, setAnswers] = useState({});      // "race|session" -> { ok, data } or { ok: false, error }
  const [pending, setPending] = useState({});      // "race|session" -> true while asking
  const [available, setAvailable] = useState({});  // race -> ["FP1", "FP2", "FP3"], from the practice answer

  const keep = (key, answer) => {
    setAnswers(a => ({ ...a, [key]: answer }));
    setPending(p => { const next = { ...p }; delete next[key]; return next; });
  };

  // practice: "" lets the server pick the last session that ran, which also tells us
  // which practice sessions this weekend had
  const loadPractice = async (raceName, fp) => {
    const r = await postJson(`${API}/practice-results`, { race_name: raceName, session: fp });
    if (r.ok) {
      setAvailable(a => ({ ...a, [raceName]: r.data.available_sessions }));
      keep(`${raceName}|${r.data.session}`, r);
    }
    if (fp) keep(`${raceName}|${fp}`, r);
  };

  const load = async (raceName, s, known) => {
    const key = `${raceName}|${s}`;
    if (!raceName || known[key]) return;
    setPending(p => ({ ...p, [key]: true }));
    if (ENDPOINT[s]) keep(key, await postJson(`${API}/${ENDPOINT[s]}`, { race_name: raceName }));
    else await loadPractice(raceName, s);
  };

  const setRace = (name) => {
    setRaceName(name);
    setSessionName("Race");
    if (!name) return;
    load(name, "Race", answers);
    if (!available[name]) loadPractice(name, "");
  };

  const setSession = (s) => {
    setSessionName(s);
    load(race, s, answers);
  };

  const key = `${race}|${session}`;
  return {
    race, setRace, session, setSession,
    answer: answers[key] || null,
    loading: !!pending[key],
    available: available[race] || null,
  };
}
