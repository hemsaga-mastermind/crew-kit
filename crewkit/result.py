"""The verdict model: three verdicts, every check carrying its evidence and coverage."""
from crewkit import FAIL, PASS, UNKNOWN


class Coverage:
    """What a run read, and what it could not. Sorted, so output stays deterministic."""

    def __init__(self):
        self._read = set()
        self._unreadable = {}

    def read(self, path):
        self._read.add(str(path))
        return path

    def unreadable(self, path, why):
        self._unreadable[str(path)] = why

    def as_dict(self):
        return {
            "read": sorted(self._read),
            "unreadable": ["%s: %s" % (p, self._unreadable[p]) for p in sorted(self._unreadable)],
        }


def check(check_id, verdict, detail, evidence):
    assert verdict in (PASS, FAIL, UNKNOWN), verdict
    return {"id": check_id, "verdict": verdict, "detail": detail, "evidence": str(evidence)}


def colour(checks):
    """red if anything failed; amber if anything is unknown; green only when all pass."""
    verdicts = [c["verdict"] for c in checks]
    if FAIL in verdicts:
        return "red"
    if UNKNOWN in verdicts:
        return "amber"
    return "green"


def exit_code(verdicts, strict):
    if FAIL in verdicts:
        return 1
    if strict and UNKNOWN in verdicts:
        return 1
    return 0
