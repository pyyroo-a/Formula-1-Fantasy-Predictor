"""
Sprint weekend detection. This used to be a hand typed list with only 2 of the 6
sprints in it, so these checks make sure it can't quietly go wrong like that again.
"""
import src.fetch_practice as fp

SPRINTS_2026 = {
    "Chinese Grand Prix", "Miami Grand Prix", "Canadian Grand Prix",
    "British Grand Prix", "Dutch Grand Prix", "Singapore Grand Prix",
}


def test_all_six_2026_sprints_found():
    for race in SPRINTS_2026:
        assert fp.is_sprint_weekend(race), race


def test_normal_weekends_are_not_sprints():
    for race in ("Italian Grand Prix", "Spanish Grand Prix", "Azerbaijan Grand Prix", "Monaco Grand Prix"):
        assert not fp.is_sprint_weekend(race), race


def test_unknown_race_is_not_a_sprint():
    assert not fp.is_sprint_weekend("Made Up Grand Prix")


def test_matches_the_schedule_exactly():
    # the whole list comes from FastF1, nothing added or missing
    assert fp._sprint_events(2026) == frozenset(SPRINTS_2026)


def test_backup_list_used_if_schedule_cant_load(monkeypatch):
    def broken(year):
        raise ConnectionError("no internet")

    monkeypatch.setattr(fp, "_sprint_events", broken)
    assert fp.is_sprint_weekend("Miami Grand Prix")
    assert not fp.is_sprint_weekend("Italian Grand Prix")
