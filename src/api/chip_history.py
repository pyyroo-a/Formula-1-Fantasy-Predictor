"""
GET /chip-history: what each chip would really have been worth at each track.

Just reads data/chip_history.json. scripts/chip_history.py works it out (Limitless
tries every possible team, too slow per visit on the free Render instance) and the
Monday GitHub Action commits the file, same as the track record.
"""
import json
import os

from fastapi import APIRouter

router = APIRouter()

DEFAULT_PATH = "data/chip_history.json"
EMPTY = {"updated": None, "seasons": [], "tracks": [], "best": {}, "check": {}}


@router.get("/chip-history")
def get_chip_history():
    path = os.getenv("CHIP_HISTORY_PATH", DEFAULT_PATH)
    if not os.path.exists(path):
        # nothing built yet, that's an empty history, not an error
        return EMPTY
    with open(path, encoding="utf-8") as f:
        return json.load(f)
