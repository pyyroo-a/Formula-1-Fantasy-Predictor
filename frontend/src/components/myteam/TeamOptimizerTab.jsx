import { TeamStatGrid, BudgetDriverCard, ConstructorCard, BoostPickCard } from "../BudgetTeam";
import { INPUT_CLS, PRIMARY_BTN_CLS, SECTION_HEAD_CLS } from "../../styles";

// My Team > Team Optimizer: 3 lineups for any race. State comes from useBudgetTeams in App.
export default function TeamOptimizerTab({ races, budget }) {
  const {
    budgetRace, setBudgetRace, budgetTeams, setBudgetTeams, activeTeam, setActiveTeam,
    budgetLoading, budgetError, fetchBudgetTeam,
  } = budget;
  return (
    <>
      <p className="text-pw-muted text-sm text-center mb-4">
        Generates 3 high-scoring lineups within $100M, pick whichever suits your strategy.
      </p>
      <select
        value={budgetRace}
        onChange={e => { setBudgetRace(e.target.value); setBudgetTeams(null); setActiveTeam(0); }}
        className={`${INPUT_CLS} mb-3`}
      >
        <option value="">Select a race</option>
        {races.map(r => <option key={r} value={r}>{r}</option>)}
      </select>
      <button
        onClick={fetchBudgetTeam}
        disabled={!budgetRace || budgetLoading}
        className={PRIMARY_BTN_CLS}
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
            <p className={SECTION_HEAD_CLS}>DRIVERS</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-5">
              {team.drivers.map((driver, i) => (
                <BudgetDriverCard
                  key={i}
                  driver={driver}
                  isCaptain={driver.Abbreviation === team.boost_pick?.Abbreviation}
                />
              ))}
            </div>
            <p className={SECTION_HEAD_CLS}>CONSTRUCTORS</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {team.constructors.map((c, i) => <ConstructorCard key={i} constructor={c} />)}
            </div>
          </div>
        );
      })()}
    </>
  );
}
