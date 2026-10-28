"""
GET /track-record: what PitWall's locked teams really scored vs the simple picks.

Just reads data/track_record_2026.json. The maths (most expensive and hindsight try
every possible team) is too slow to do on every visit on the free Render instance, so
scripts/track_record.py works it out and the Monday GitHub Action commits the file.
"""
import json
import os

from fastapi import APIRouter

router = APIRouter()

DEFAULT_PATH = "data/track_record_2026.json"
EMPTY = {"updated": None, "rows": [], "summary": {}}


@router.get("/track-record")
def get_track_record():
    path = os.getenv("TRACK_RECORD_PATH", DEFAULT_PATH)
    if not os.path.exists(path):
        # nothing graded yet, that's an empty record, not an error
        return EMPTY
    with open(path, encoding="utf-8") as f:
        return json.load(f)
