"""
Fills data/official_points_2026.json with the game's own points for finished rounds.

Normally the Monday job adds each new round by itself. This is for filling in the
past, or a round it missed.

Usage:
    python scripts/backfill_official_points.py              # rounds 1 to 24
    python scripts/backfill_official_points.py --rounds 1-18
    python scripts/backfill_official_points.py --rounds 18
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.official_points import fetch_official_points, is_raced, save_official_round


def _rounds(text: str) -> list[int]:
    if "-" in text:
        first, last = text.split("-")
        return list(range(int(first), int(last) + 1))
    return [int(text)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", default="1-24", help="e.g. 1-18 or 18")
    args = ap.parse_args()

    saved, skipped = [], []
    for rnd in _rounds(args.rounds):
        try:
            pts = fetch_official_points(rnd)
        except Exception as e:
            skipped.append(f"{rnd} (feed error: {e})")
            continue
        if not is_raced(pts):
            # every driver on 0 means the round hasn't happened, don't store that as a result
            skipped.append(f"{rnd} (not raced yet)")
            continue
        save_official_round(rnd, pts)
        saved.append(rnd)

    print(f"saved rounds: {saved}")
    for s in skipped:
        print(f"skipped round {s}")


if __name__ == "__main__":
    main()
