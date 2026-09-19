"""
Saves the F1 Fantasy prices the tests use, so the tests don't depend on the live feed.

You only run this once (or if you deliberately want to refresh the test data):
    python tests/record_fixtures.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from src.fetch_prices import fetch_prices, fetch_price_changes  # noqa: E402

out = ROOT / "tests" / "fixtures"
out.mkdir(parents=True, exist_ok=True)

# round 14 = Madring, the weekend the tests pretend to be in
(out / "prices_r14.json").write_text(json.dumps(fetch_prices(14), indent=1, sort_keys=True))
(out / "price_changes_r14.json").write_text(json.dumps(fetch_price_changes(14), indent=1, sort_keys=True))
print("saved", sorted(p.name for p in out.iterdir()))
