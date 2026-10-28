import { useState } from "react";
import { DRIVER_NAMES, teamAccent } from "../../constants";
import { INPUT_CLS } from "../../styles";
import { qualiTag, sessionOptions, raceChange } from "../../lib/racedata";
import Switcher from "../../ui/Switcher";
import TowerRow from "../../ui/TowerRow";
import Loading, { ErrorLine } from "../../ui/Loading";

const name = r => r.FullName || DRIVER_NAMES[r.Abbreviation] || r.Abbreviation;

function Practice({ rows }) {
  return rows.map((r, i) => (
    <TowerRow
      key={r.Abbreviation}
      spot={`P${r.Position}`}
      color={teamAccent(r.TeamName)}
      name={name(r)}
      sub={r.TeamName}
      right={<span className={i === 0 ? "text-pw-caution" : ""}>{r.LapTime}</span>}
      rightSub={i === 0 ? "fastest" : `+${r.GapToPole.toFixed(3)}`}
    />
  ));
}

// one time per driver on a phone, tap a row for all three
function Quali({ rows }) {
  const [open, setOpen] = useState(null);
  return rows.map(r => {
    const { time, tag } = qualiTag(r);
    return (
      <TowerRow
        key={r.Abbreviation}
        spot={`P${r.Position}`}
        color={teamAccent(r.TeamName)}
        name={name(r)}
        sub={r.TeamName}
        right={time}
        rightSub={<span className={`text-[11px] font-bold px-1.5 rounded ${tag === "Q3" ? "bg-[#332D16] text-pw-caution" : "bg-pw-edge text-pw-muted"}`}>{tag}</span>}
        onClick={() => setOpen(open === r.Abbreviation ? null : r.Abbreviation)}
      >
        {open === r.Abbreviation && (
          <p className="text-xs text-pw-muted num mt-0.5">Q1 {r.Q1 || "-"}, Q2 {r.Q2 || "-"}, Q3 {r.Q3 || "-"}</p>
        )}
      </TowerRow>
    );
  });
}

const TONE = { up: "text-pw-safe font-bold", down: "text-pw-low font-bold", same: "text-pw-muted", none: "" };

function Race({ rows }) {
  return rows.map(r => {
    const dnf = r.Status === "DNF";
    const ch = raceChange(r);
    return (
      <TowerRow
        key={r.Abbreviation}
        spot={dnf ? "DNF" : `P${r.Position}`}
        spotClass={dnf ? "text-pw-low" : ""}
        color={teamAccent(r.TeamName)}
        name={name(r)}
        sub={r.TeamName}
        faded={dnf}
        right={ch.text ? <span className={TONE[ch.tone]}>{ch.text}</span> : null}
        rightSub={ch.from}
      />
    );
  });
}

const TITLE = { Quali: "Qualifying", Race: "Race result" };
const HINT = {
  Quali: "Each driver's best time from the last part they reached. Tap a row for all three times.",
  Race: "Grid spot to finish. Green gained places, red lost them.",
};

// Race data: pick a race that's happened, then a session from the strip. The state
// lives in App (useRaceWeekend) so your race is still picked when you come back
export default function RaceDataPage({ races, weekend }) {
  const { race, setRace, session, setSession, answer, loading, available } = weekend;
  const isPractice = session.startsWith("FP");
  const rows = answer?.ok ? (isPractice ? answer.data.results : answer.data) : null;

  return (
    <div>
      <select value={race} onChange={e => setRace(e.target.value)} className={`${INPUT_CLS} mb-3`}>
        <option value="">Pick a race that's happened</option>
        {races.map(r => <option key={r} value={r}>{r}</option>)}
      </select>

      {race && (
        <>
          <Switcher className="mb-4" value={session} onChange={setSession}
            options={sessionOptions(available).map(s => ({ id: s, label: s }))} />
          <h3 className="cond-x font-extrabold text-2xl">{isPractice ? `${session} pace` : TITLE[session]}</h3>
          <p className="text-xs text-pw-muted mb-2">{isPractice ? "Fastest lap and the gap to the top." : HINT[session]}</p>

          {loading && <Loading text="Loading. The free server can take up to 30 seconds to wake up." rows={4} />}
          {!loading && answer && !answer.ok && <ErrorLine text={answer.error} />}
          {!loading && rows && (
            rows.length === 0 ? <p className="text-sm text-pw-muted">Nothing for this session yet.</p>
              : isPractice ? <Practice rows={rows} /> : session === "Quali" ? <Quali rows={rows} /> : <Race rows={rows} />
          )}
        </>
      )}
    </div>
  );
}
