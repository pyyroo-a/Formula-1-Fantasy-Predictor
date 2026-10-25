"""
No em dashes or en dashes anywhere we write things: code, comments, UI text, docs,
notes, workflows. My rule, and the 2x pick reason was showing up on the site as
garbled text because of one.

Golden files and fixtures are data, so they're skipped here. The golden answers
still can't have one sneak in because they're made from the code this scans.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCAN = ["src", "scripts", "tests", "frontend/src", "docs", "Fantasy Predictor", ".github"]
FILES = ["main.py", "README.md", "Dockerfile", "frontend/index.html", "frontend/README.md",
         ".dockerignore", ".gitignore", ".env.example"]
SUFFIXES = {".py", ".js", ".jsx", ".css", ".md", ".yml", ".yaml", ".html", ".json", ".txt"}
SKIP = {ROOT / "tests" / "golden", ROOT / "tests" / "fixtures"}

DASHES = (chr(0x2014), chr(0x2013))


def _files():
    for name in SCAN:
        base = ROOT / name
        if not base.exists():
            continue  # e.g. the notes folder before it's made
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SUFFIXES:
                continue
            if "__pycache__" in path.parts or any(s in path.parents for s in SKIP):
                continue
            yield path
    for name in FILES:
        if (ROOT / name).exists():
            yield ROOT / name


def test_no_em_or_en_dashes_anywhere():
    bad = []
    for path in _files():
        # strict utf-8 on purpose: a file that got re-encoded on Windows fails here too
        text = path.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            if any(d in line for d in DASHES):
                bad.append(f"{path.relative_to(ROOT)}:{n}")
    assert not bad, f"{len(bad)} lines with dashes:\n" + "\n".join(bad)
