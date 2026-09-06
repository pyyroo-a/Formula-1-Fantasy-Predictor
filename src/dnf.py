"""
Estimates the probability that each driver fails to finish a race.

WHY THIS EXISTS
---------------
src/fantasy.py applies a -20 point penalty for a DNF, but for UPCOMING races it
hardcodes that penalty to 0. Every driver is assumed to finish. In reality about
3 cars per race do not, so the scoring is systematically optimistic for exactly
the picks most likely to blow up a fantasy week.

This module does NOT try to predict which specific driver will crash. That is not
possible. It estimates how *likely* each driver is to retire, so the expected
points calculation can price that risk instead of ignoring it.

WHAT THE DATA ACTUALLY SUPPORTS
-------------------------------
Measured over 2025 + 2026 (36 races, excluding pre-season testing):

  * Base rate: 15.8% of driver-races end in a retirement.

  * Grid position is the STRONGEST signal, and it is well sampled:
        P1-P5   ->  8.1%
        P6-P10  -> 15.1%
        P11-P15 -> 15.7%
        P16+    -> 21.6%
    Slower cars are both less reliable and more exposed to first-lap incidents.

  * The season matters a lot: 2025 ran at 12.5%, 2026 at 21.6%. Nearly double.
    Recent races are therefore weighted more heavily, mirroring how the main
    model weights 2026 5x.

  * Driver identity and circuit both help, but far less than their raw numbers
    suggest. A driver with 9 retirements in 36 races has not proved he is
    unreliable, because an ordinary driver would produce that fairly often by
    chance. Both are therefore shrunk toward the field average by an amount
    measured from the data rather than chosen by hand (see _shrunk_rates).
    Circuit is shrunk about five times harder than driver, because each circuit
    has only one or two runnings to learn from.

Nothing here is trusted on principle. scripts/measure_dnf.py validates the model
walk-forward against the flat base rate. Measured over 2026:

    Brier 0.1652 vs 0.1750 baseline (-5.6%), log loss -5.6%, better on 11 of 12
    races. Component by component, starting from a flat rate: grid -2.9%,
    adding driver -3.7%, adding circuit -4.3%.

The gains are real but modest. If a future change stops beating that baseline,
the model should not be used.
"""

import numpy as np
import pandas as pd

# Statuses that count as having finished the race. Anything else (DNF, Retired,
# Disqualified, Did not start) is treated as a non-finish. This mirrors the rule
# already used in src/fantasy.py so the two stay consistent.
FINISHED_STATUSES = ["Finished", "Lapped"]

# How much more recent-season races count when estimating rates. Matches the 5x
# weighting the main pipeline applies to 2026 results.
CURRENT_SEASON_WEIGHT = 5.0

# Whether to compute retirement probabilities for upcoming races at all.
#
# True means every driver and constructor in the API payload carries a DNF
# probability. It does NOT mean those probabilities move the picks: that is
# controlled separately by DNF_WEIGHT in src/fantasy.py, which is 0.0 because
# charging the risk as a points deduction measured worse (-26.9 pts/race).
#
# So the shipped behaviour is: show the risk, let the human act on it, and leave
# the optimiser scoring exactly as it did before.
USE_DNF_RISK = True

# Probabilities are clipped to this range. A driver is never certain to finish
# and never doomed, and unclipped extremes make the sampler behave badly.
P_MIN, P_MAX = 0.02, 0.60


def label_dnf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 0/1 DNF column and drops non-race rows.

    Pre-season testing is stored with RoundNumber 0 and every driver marked as
    finished, which would drag the base rate down if left in.
    """
    out = df[df["RoundNumber"] > 0].copy()
    out["DNF"] = (~out["Status"].isin(FINISHED_STATUSES)).astype(int)
    return out


def _season_weights(years: pd.Series) -> np.ndarray:
    """Latest season gets CURRENT_SEASON_WEIGHT, everything older gets 1."""
    latest = years.max()
    return np.where(years == latest, CURRENT_SEASON_WEIGHT, 1.0)


def _shrunk_rates(df: pd.DataFrame, key: str, p0: float, weights: np.ndarray):
    """
    Empirical-Bayes shrinkage of a per-group rate toward the overall rate p0.

    The intuition: a driver with 4 retirements in 30 races has not proven he is
    unreliable, because that could easily happen to an average driver. So we pull
    his estimate toward the field average, and how hard we pull depends on how
    much real group-to-group variation exists in the data.

        shrunk = (n * observed + k * p0) / (n + k)

    k is the "prior strength", measured rather than guessed:

        k = p0 * (1 - p0) / tau^2

    where tau^2 is the genuine between-group variance, found by taking the
    variance we actually observe and subtracting the variance we would expect
    from random chance alone. If groups barely differ, tau^2 approaches 0, k
    becomes huge, and every group collapses to p0. That is the correct answer
    when there is no real signal, and it is roughly what happens for drivers.

    Returns (rates_by_group, k).
    """
    g = pd.DataFrame({"key": df[key].values, "dnf": df["DNF"].values, "w": weights})
    agg = g.groupby("key").agg(n=("w", "sum"), hits=("dnf", lambda s: 0.0))
    # Weighted counts: sum of weights, and weighted sum of DNFs.
    agg["n"] = g.groupby("key")["w"].sum()
    agg["hits"] = g.assign(x=g["dnf"] * g["w"]).groupby("key")["x"].sum()
    agg["rate"] = agg["hits"] / agg["n"]

    # Effective sample size (Kish). Weighting the current season 5x does NOT
    # give us five times the evidence, it just concentrates the evidence on
    # fewer races. Using the raw weight sum here would pretend each driver has
    # ~90 races when he really has ~37, understate how much of the spread is
    # random chance, and leave the estimates badly under-shrunk.
    sq = g.assign(w2=g["w"] ** 2).groupby("key")["w2"].sum()
    agg["n_eff"] = (agg["n"] ** 2) / sq

    # Only groups with a meaningful sample inform the variance estimate.
    solid = agg[agg["n_eff"] >= 10]
    if len(solid) < 3:
        return {kk: p0 for kk in agg.index}, np.inf

    observed_var = solid["rate"].var(ddof=1)
    noise_var = float((p0 * (1 - p0) / solid["n_eff"]).mean())
    tau2 = max(observed_var - noise_var, 1e-6)   # never negative
    k = p0 * (1 - p0) / tau2

    shrunk = (agg["n_eff"] * agg["rate"] + k * p0) / (agg["n_eff"] + k)
    return shrunk.to_dict(), k


def _grid_curve(df: pd.DataFrame, weights: np.ndarray, p0: float):
    """
    Fits how retirement risk changes with starting position.

    A straight line through the odds is used rather than fixed buckets, so that
    P10 and P11 differ only slightly instead of jumping at an arbitrary edge.
    The fit is done in log-odds space, which keeps predictions inside 0..1.

    Returns a function mapping grid position to a multiplier on the odds.
    """
    d = df.dropna(subset=["GridPosition"])
    w = weights[df.index.isin(d.index)] if len(d) != len(df) else weights
    x = d["GridPosition"].to_numpy(dtype=float)
    y = d["DNF"].to_numpy(dtype=float)

    # Weighted least squares on a smoothed log-odds of the binned rate. Binning
    # first keeps the fit stable with only ~700 rows.
    bins = np.clip(np.round(x).astype(int), 1, 20)
    rate, weight = {}, {}
    for b in range(1, 21):
        m = bins == b
        if m.sum() == 0:
            continue
        ww = w[m].sum()
        rate[b] = float((y[m] * w[m]).sum() / ww)
        weight[b] = ww
    if len(rate) < 4:
        return lambda g: 1.0

    bs = np.array(sorted(rate))
    # Pull each bin toward p0 before taking log-odds, so a bin that happens to
    # have zero retirements does not produce negative infinity.
    n = np.array([weight[b] for b in bs])
    r = np.array([rate[b] for b in bs])
    r = (n * r + 20.0 * p0) / (n + 20.0)
    logit = np.log(r / (1 - r))
    slope, intercept = np.polyfit(bs, logit, 1, w=n)

    base_logit = np.log(p0 / (1 - p0))

    def multiplier(grid):
        g = np.clip(np.asarray(grid, dtype=float), 1, 20)
        return np.exp((intercept + slope * g) - base_logit)

    return multiplier


class DNFModel:
    """
    P(DNF) for a driver, given his grid slot and the circuit.

    Built as a base rate adjusted multiplicatively on the odds scale, so the
    components combine without ever pushing the probability outside 0..1.
    """

    def __init__(self, p0, grid_fn, driver_rates, circuit_rates, k_driver, k_circuit):
        self.p0 = p0
        self._grid_fn = grid_fn
        self._driver = driver_rates
        self._circuit = circuit_rates
        self.k_driver = k_driver
        self.k_circuit = k_circuit

    @classmethod
    def fit(cls, history: pd.DataFrame) -> "DNFModel":
        """`history` is raw race results. Only rows before the target race should
        be passed in, otherwise validation leaks future information."""
        d = label_dnf(history)
        w = _season_weights(d["Year"])
        p0 = float((d["DNF"] * w).sum() / w.sum())

        driver_rates, k_d = _shrunk_rates(d, "Abbreviation", p0, w)
        circuit_rates, k_c = _shrunk_rates(d, "RaceName", p0, w)
        grid_fn = _grid_curve(d, w, p0)
        return cls(p0, grid_fn, driver_rates, circuit_rates, k_d, k_c)

    def predict(self, drivers, grid, race_name=None) -> np.ndarray:
        """
        drivers   : iterable of driver abbreviations
        grid      : their grid positions (practice-estimated is fine)
        race_name : circuit, if known

        Returns P(DNF) per driver, clipped to a sensible range.
        """
        drivers = list(drivers)
        base_odds = self.p0 / (1 - self.p0)

        # Each component contributes a ratio relative to the base rate. A driver
        # the data says is average contributes exactly 1.0 and changes nothing.
        grid_mult = np.asarray(self._grid_fn(grid), dtype=float)

        def ratio(rate):
            return (rate / (1 - rate)) / base_odds

        drv_mult = np.array([
            ratio(self._driver.get(d, self.p0)) for d in drivers
        ])
        circ = self._circuit.get(race_name, self.p0) if race_name else self.p0
        circ_mult = ratio(circ)

        odds = base_odds * grid_mult * drv_mult * circ_mult
        p = odds / (1 + odds)
        return np.clip(p, P_MIN, P_MAX)

    def expected_dnf_penalty(self, drivers, grid, race_name=None, penalty=-20.0):
        """Convenience: the expected points hit, P(DNF) * -20."""
        return self.predict(drivers, grid, race_name) * penalty
