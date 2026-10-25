import PracticeTable from "../PracticeTable";
import { INPUT_CLS, SECTION_HEAD_CLS } from "../../styles";

// Race Data > Practice. State comes from usePractice in App.
export default function PracticeTab({ races, practice }) {
  const {
    practiceRace, setPracticeRace, practiceData, setPracticeData,
    practiceLoading, practiceError, setPracticeError, fetchPractice,
  } = practice;
  return (
    <>
      <select
        value={practiceRace}
        onChange={e => {
          const r = e.target.value;
          setPracticeRace(r); setPracticeData(null); setPracticeError(null);
          if (r) fetchPractice(r);
        }}
        className={`${INPUT_CLS} mb-3`}
      >
        <option value="">Select a race</option>
        {races.map(r => <option key={r} value={r}>{r}</option>)}
      </select>

      {/* Session switcher: only the sessions that actually ran this weekend */}
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
          <p className="text-pw-muted text-sm">Fetching practice pace…</p>
          <p className="text-pw-muted/60 text-xs mt-1">May take 15 to 30 seconds on first load</p>
        </div>
      )}
      {practiceError && <p className="text-pw-red text-sm text-center mb-4">{practiceError}</p>}
      {practiceData?.results?.length > 0 && !practiceLoading && (
        <div>
          <p className={SECTION_HEAD_CLS}>{practiceRace?.toUpperCase()} · {practiceData.session} PACE</p>
          <PracticeTable results={practiceData.results} />
        </div>
      )}
    </>
  );
}
