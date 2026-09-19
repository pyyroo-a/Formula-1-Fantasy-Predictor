"""
Weekend snapshots: the one saved copy of what PitWall predicted for a race.

Basically the site used to work the team out again every time someone opened it.
The answer then depended on the time (before or after lights out), on whether
Render had just restarted and wiped its lock, and on whether FastF1 downloaded
properly on that request. So the same weekend could show different teams.

Now we work a weekend out ONCE, after final practice, and save it as a file in
data/snapshots/. The site only ever reads those files. Restarts can't lose them
because they get committed to GitHub and ship with the code.

One file per race, e.g. data/snapshots/2026_R14_spanish_grand_prix.json, holding
the 3 teams (with chips and dnf numbers) and the predicted finishing order. Old
ones are kept, so we build up a history of every weekend's predictions.
"""

import base64
import glob
import json
import os
import re

import requests

from src.config import SEASON

# where snapshots live in the repo. this is also the path we commit to on GitHub
REPO_SNAPSHOT_DIR = "data/snapshots"


def _dir() -> str:
    # read each time so tests can point this at a temporary folder
    return os.getenv("SNAPSHOT_DIR", REPO_SNAPSHOT_DIR)


def _slug(race_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", race_name.lower()).strip("_")


def snapshot_filename(year: int, rnd: int, race_name: str) -> str:
    # round is zero padded so the files sort in race order
    return f"{int(year)}_R{int(rnd):02d}_{_slug(race_name)}.json"


def snapshot_path(year: int, rnd: int, race_name: str) -> str:
    return os.path.join(_dir(), snapshot_filename(year, rnd, race_name))


def list_snapshots() -> list[dict]:
    """Every saved snapshot, oldest race first. Broken files are skipped, not fatal."""
    snaps = []
    for path in glob.glob(os.path.join(_dir(), "*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                snap = json.load(f)
            if snap.get("race_name") and snap.get("round") is not None:
                snaps.append(snap)
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(snaps, key=lambda s: (int(s.get("year", SEASON)), int(s["round"])))


def find_snapshot(race_name: str, year: int = SEASON) -> dict | None:
    """The snapshot for one race, or None if that weekend hasn't been locked."""
    for snap in list_snapshots():
        if snap["race_name"] == race_name and int(snap.get("year", SEASON)) == year:
            return snap
    return None


def latest_snapshot(with_key: str | None = None) -> dict | None:
    """
    The newest snapshot. With with_key, the newest one that actually has that part,
    e.g. latest_snapshot("finishes") skips old snapshots saved before we stored finishes.
    """
    for snap in reversed(list_snapshots()):
        if with_key is None or snap.get(with_key):
            return snap
    return None


def save_snapshot(snap: dict, force: bool = False) -> str:
    """
    Writes a snapshot file. Refuses to overwrite an existing one unless force=True,
    because the whole point is that a locked weekend never changes.
    """
    path = snapshot_path(snap.get("year", SEASON), snap["round"], snap["race_name"])
    if os.path.exists(path) and not force:
        raise FileExistsError(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=2)
    return path


def commit_to_github(snap: dict, dry_run: bool = False) -> dict:
    """
    Commits a snapshot into the repo through GitHub's API, so it survives restarts
    and redeploys. Render then redeploys with the file included.

    Needs GITHUB_TOKEN (a fine-grained token that can only write to this repo). If the
    file is already on GitHub we leave it alone, so calling this again is safe.
    """
    repo = os.getenv("GITHUB_REPO", "pyyroo-a/Formula-1-Fantasy-Predictor")
    branch = os.getenv("GITHUB_BRANCH", "main")
    path = f"{REPO_SNAPSHOT_DIR}/{snapshot_filename(snap.get('year', SEASON), snap['round'], snap['race_name'])}"

    if dry_run:
        return {"committed": False, "reason": "dry run, nothing committed", "path": path}

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"committed": False, "reason": "GITHUB_TOKEN is not set, snapshot only saved on this server", "path": path}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    check = requests.get(url, headers=headers, params={"ref": branch}, timeout=20)
    if check.status_code == 200:
        return {"committed": False, "reason": "already on GitHub", "path": path}
    if check.status_code != 404:
        raise RuntimeError(f"GitHub check failed ({check.status_code}): {check.text[:200]}")

    body = {
        "message": f"chore: snapshot for {snap['race_name']} (round {snap['round']})",
        "content": base64.b64encode(json.dumps(snap, indent=2).encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    put = requests.put(url, headers=headers, json=body, timeout=30)
    if put.status_code not in (200, 201):
        raise RuntimeError(f"GitHub commit failed ({put.status_code}): {put.text[:200]}")
    return {"committed": True, "path": path, "commit": put.json().get("commit", {}).get("sha")}
