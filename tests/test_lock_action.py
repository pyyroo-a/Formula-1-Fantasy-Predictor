"""
Checks on the lock Action's schedule (.github/workflows/lock-snapshot.yml).

GitHub runs scheduled Actions late or drops them, especially on the hour (on Mexico
weekend about 5 of 48 starts actually ran). So the lock can't hang on one start: there's
a start every hour on race days, at an odd minute, and the concurrency group lines them
up so one is always running or waiting to take over.
"""
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "lock-snapshot.yml"


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _crons():
    # yaml reads the "on" key as True
    return [s["cron"] for s in _workflow()[True]["schedule"]]


def test_starts_every_hour_on_friday_and_saturday_off_the_hour():
    assert "17 * * * 5,6" in _crons()


def test_sunday_catch_up_every_hour_until_midday():
    assert "17 0-12 * * 0" in _crons()


def test_one_run_at_a_time_and_new_starts_wait_instead_of_cancelling():
    assert _workflow()["concurrency"] == {"group": "lock-snapshot", "cancel-in-progress": False}
