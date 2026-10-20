"""Validate a Crew Kit decision log (one JSON object per line).

Usage: python3 -I tools/check_decisions.py [path]   (default: ./decisions.jsonl)
Exit 0 when every line is valid, 1 otherwise (errors printed one per line).

The schema lives in crewkit/journal.py, which `crewkit verify` also uses; this
command stays as it was in v0.1 so nothing that depends on it breaks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crewkit.journal import check_entry, check_file, main  # noqa: E402,F401

if __name__ == "__main__":
    sys.exit(main(sys.argv))
