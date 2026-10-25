import RaceResultsTable from "../RaceResultsTable";
import { INPUT_CLS, SECTION_HEAD_CLS } from "../../styles";

// Race Data > Race Results. State comes from useRaceResults in App.
export default function RaceResultsTab({ races, results }) {
  const { resultsRace, setResultsRace, raceResults, resultsLoading, resultsError, fetchRaceResults } = results;
  return (
    <>
      <select
        value={resultsRace}
        onChange={e => { setResultsRace(e.target.value); fetchRaceResults(e.target.value); }}
        className={`${INPUT_CLS} mb-4`}
      >
        <option value="">Select a completed race</option>
        {races.map(r => <option key={r} value={r}>{r}</option>)}
      </select>
      {resultsLoading && <p className="text-pw-muted text-sm text-center">Loading results…</p>}
      {resultsError && <p className="text-pw-red text-sm text-center">{resultsError}</p>}
      {raceResults && (
        <div>
          <p className={SECTION_HEAD_CLS}>{resultsRace?.toUpperCase()} · FINAL CLASSIFICATION</p>
          <RaceResultsTable results={raceResults} />
        </div>
      )}
    </>
  );
}
