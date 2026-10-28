"""
Checks for the confidence levels (src/confidence.py), on small made up grids so every
answer can be worked out by hand. The first two are the real Austin 2026 FP3 shapes:
Leclerc P1 with Hamilton right behind him, Max P4 with Hadjar way back in P10.
"""
import pandas as pd
import pytest

import src.confidence as confidence
from src.confidence import (attach_confidence, attach_to_teams, load_weekend_sessions,
                            sessions_for, weekend_confidence)


def _grid(rows):
    """rows are (abbreviation, team, gap to pole) in finishing order."""
    return pd.DataFrame([{"Abbreviation": a, "TeamName": t, "GridPosition": i + 1, "GapToPole": g}
                         for i, (a, t, g) in enumerate(rows)])


AUSTIN_FP3 = _grid([("LEC", "Ferrari", 0.0), ("HAM", "Ferrari", 0.083), ("ANT", "Mercedes", 0.166),
                    ("VER", "Red Bull", 0.212), ("NOR", "McLaren", 0.258), ("RUS", "Mercedes", 0.4),
                    ("PIA", "McLaren", 0.5), ("HUL", "Audi", 0.6), ("GAS", "Alpine", 0.7),
                    ("HAD", "Red Bull", 0.8)])
AUSTIN = {
    "FP1": _grid([("LEC", "Ferrari", 0.0), ("VER", "Red Bull", 0.1), ("HAM", "Ferrari", 0.2),
                  ("ANT", "Mercedes", 0.3), ("NOR", "McLaren", 0.4)]),
    "FP2": _grid([("HAM", "Ferrari", 0.0), ("LEC", "Ferrari", 0.1), ("ANT", "Mercedes", 0.2),
                  ("NOR", "McLaren", 0.3), ("VER", "Red Bull", 0.4)]),
    "FP3": AUSTIN_FP3,
}


def test_clean_driver_is_high():
    conf = weekend_confidence(AUSTIN, "FP3")
    assert conf["LEC"]["level"] == "high" and conf["LEC"]["flags"] == 0
    assert conf["LEC"]["reason"] == ("P1 in FP3. Teammate HAM P2 backs it up, "
                                     "steady all weekend and 0.083s clear of the next car.")


def test_three_flags_is_low():
    conf = weekend_confidence(AUSTIN, "FP3")
    assert conf["VER"]["level"] == "low" and conf["VER"]["flags"] == 3
    assert conf["VER"]["reason"] == ("P4 in FP3. But teammate HAD was P10, moved around between "
                                     "sessions (P2 to P5) and only 0.046s from the next car.")


def test_one_flag_is_medium():
    # Russell: Antonelli 3 places ahead is the only flag, he wasn't in FP1 or FP2 here
    conf = weekend_confidence(AUSTIN, "FP3")
    assert conf["RUS"]["level"] == "medium" and conf["RUS"]["flags"] == 1
    assert conf["RUS"]["reason"] == ("P6 in FP3. 0.100s clear of the next car. But teammate ANT "
                                     "was P3. Couldn't check: only one session so far.")


def test_teammate_exactly_2_places_passes():
    # Norris P5, Piastri P7
    conf = weekend_confidence(AUSTIN, "FP3")
    assert "teammate pia p7 backs it up" in conf["NOR"]["reason"].lower()
    assert "teammate PIA was" not in conf["NOR"]["reason"]


def _two_sessions(first, second):
    """Driver X is P{first} in FP1 and P{second} in sprint quali, everyone else fills in."""
    def grid(pos):
        names = ["A", "B", "C"]
        names.insert(pos - 1, "X")
        return _grid([(n, f"Team {n}", i * 0.2) for i, n in enumerate(names)])
    return {"FP1": grid(first), "SQ": grid(second)}


def test_spread_uses_sample_std():
    # ranks 1 and 3: sample std 1.414, passes. ranks 1 and 4: 2.121, flagged
    assert "steady all weekend" in weekend_confidence(_two_sessions(1, 3), "SQ")["X"]["reason"].lower()
    assert "moved around between sessions (P1 to P4)" in weekend_confidence(_two_sessions(1, 4), "SQ")["X"]["reason"]


def test_p1_and_last_use_their_only_neighbour():
    s = {"FP3": _grid([("A", "Ta", 0.0), ("B", "Tb", 0.04), ("C", "Tc", 0.2)])}
    conf = weekend_confidence(s, "FP3")
    assert "only 0.040s from the next car" in conf["A"]["reason"]
    assert "only 0.040s from the next car" in conf["B"]["reason"]
    assert "0.160s clear of the next car" in conf["C"]["reason"]


def test_gap_of_exactly_005_passes():
    s = {"FP3": _grid([("A", "Ta", 0.0), ("B", "Tb", 0.05)])}
    assert weekend_confidence(s, "FP3")["A"]["flags"] == 0


def test_identical_times_are_a_tight_pack():
    s = {"FP3": _grid([("A", "Ta", 0.0), ("B", "Tb", 0.0), ("C", "Tc", 0.5)])}
    conf = weekend_confidence(s, "FP3")
    assert conf["A"]["flags"] == 1 and "only 0.000s from the next car" in conf["A"]["reason"]


def test_missing_checks_count_as_passed():
    s = {"FP3": _grid([("Z", "Solo", 0.0), ("W", "Other", 0.3)])}
    conf = weekend_confidence(s, "FP3")
    assert conf["Z"]["level"] == "high"
    assert conf["Z"]["reason"] == ("P1 in FP3. 0.300s clear of the next car. "
                                   "Couldn't check: no teammate time and only one session so far.")
    alone = weekend_confidence({"FP3": _grid([("Z", "Solo", 0.0)])}, "FP3")["Z"]
    assert alone["level"] == "high"
    assert alone["reason"] == ("P1 in FP3. Couldn't check: no teammate time, only one session "
                               "so far and no other car to compare.")


def test_sprint_lock_session_label():
    conf = weekend_confidence(_two_sessions(1, 3), "SQ")
    assert conf["X"]["reason"].startswith("P3 in sprint quali.")


def test_sessions_for():
    assert sessions_for("FP3") == ["FP1", "FP2", "FP3"]
    assert sessions_for("SQ") == ["FP1", "SQ"]


def test_attach_adds_fields_without_touching_the_input():
    drivers = [{"Abbreviation": "LEC", "PickCategory": "Safe"}]
    conf = weekend_confidence(AUSTIN, "FP3")
    out = attach_confidence(drivers, conf)
    assert out[0]["Confidence"] == "high"
    assert out[0]["ConfidenceReason"] == conf["LEC"]["reason"]
    assert out[0]["PickCategory"] == "Safe"
    assert "Confidence" not in drivers[0]


def test_attach_leaves_unknown_drivers_without_a_label():
    conf = weekend_confidence(AUSTIN, "FP3")
    out = attach_confidence([{"Abbreviation": "BOT"}], conf)
    assert out[0]["Confidence"] is None and out[0]["ConfidenceReason"] is None
    out = attach_confidence([{"Abbreviation": "LEC"}], None)
    assert out[0]["Confidence"] is None and out[0]["ConfidenceReason"] is None


def test_attach_to_teams_covers_the_boost_pick():
    conf = weekend_confidence(AUSTIN, "FP3")
    teams = [{"drivers": [{"Abbreviation": "VER"}], "boost_pick": {"Abbreviation": "LEC"}, "total_score": 1}]
    out = attach_to_teams(teams, conf)
    assert out[0]["drivers"][0]["Confidence"] == "low"
    assert out[0]["boost_pick"]["Confidence"] == "high"
    assert out[0]["total_score"] == 1
    assert "Confidence" not in teams[0]["boost_pick"]


def test_load_skips_a_failed_earlier_session():
    def load(s):
        if s == "FP2":
            raise RuntimeError("OpenF1 hiccup")
        return AUSTIN[s]
    assert list(load_weekend_sessions(load, "FP3")) == ["FP1", "FP3"]


def test_load_raises_if_the_lock_session_fails():
    def load(s):
        if s == "FP3":
            raise RuntimeError("no FP3")
        return AUSTIN[s]
    with pytest.raises(RuntimeError):
        load_weekend_sessions(load, "FP3")


def test_the_cutoffs_are_the_measured_ones():
    assert (confidence.MATE_PLACES, confidence.SPREAD_LIMIT, confidence.PACK_GAP_S) == (2, 1.5, 0.05)
    assert confidence.SHOW_ON_SPRINT_WEEKENDS is False
