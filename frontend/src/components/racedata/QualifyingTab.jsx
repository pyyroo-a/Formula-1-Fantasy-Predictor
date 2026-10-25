import QualifyingTable from "../QualifyingTable";
import { INPUT_CLS, PRIMARY_BTN_CLS, SECTION_HEAD_CLS } from "../../styles";

// Race Data > Qualifying. State comes from useQualifying in App.
export default function QualifyingTab({ races, qualifying }) {
  const {
    qualRace, setQualRace, qualResults, setQualResults,
    qualLoading, qualError, setQualError, fetchQualifying,
  } = qualifying;
  return (
    <>
      <select
        value={qualRace}
        onChange={e => { setQualRace(e.target.value); setQualResults(null); setQualError(null); }}
        className={`${INPUT_CLS} mb-3`}
      >
        <option value="">Select a completed race</option>
        {races.map(r => <option key={r} value={r}>{r}</option>)}
      </select>
      {qualRace && !qualResults && !qualLoading && (
        <button onClick={fetchQualifying} className={`${PRIMARY_BTN_CLS} mb-4`}>
          Load Qualifying Results
        </button>
      )}
      {qualLoading && (
        <div className="text-center mb-4">
          <p className="text-pw-muted text-sm">Fetching qualifying data from FastF1…</p>
          <p className="text-pw-muted/60 text-xs mt-1">May take 15 to 30 seconds on first load</p>
        </div>
      )}
      {qualError && <p className="text-pw-red text-sm text-center mb-4">{qualError}</p>}
      {qualResults && (
        <div>
          <p className={SECTION_HEAD_CLS}>{qualRace?.toUpperCase()} · QUALIFYING</p>
          <QualifyingTable results={qualResults} />
        </div>
      )}
    </>
  );
}
