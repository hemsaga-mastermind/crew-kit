import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check_decisions as cd  # noqa: E402


def write(lines):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    f.write("\n".join(json.dumps(x) for x in lines))
    f.close()
    return f.name


FOUNDER = {"id": "D-2026-10-16-01", "date": "2026-10-16", "kind": "founder", "text": "x",
           "source": {"type": "founder_session"}}
IMPORTED = {"id": "D-2026-10-14-01", "date": "2026-10-14", "kind": "imported", "text": "y",
            "confirm_status": "pending", "source": {"type": "grok_export", "path": "a/b.md"}}


class CheckDecisions(unittest.TestCase):
    def test_valid_file(self):
        self.assertEqual(cd.check_file(write([IMPORTED, FOUNDER])), [])

    def test_founder_needs_founder_source(self):
        bad = dict(FOUNDER, source={"type": "grok_export"})
        self.assertTrue(any("founder entry" in e for e in cd.check_file(write([bad]))))

    def test_imported_needs_confirm_status(self):
        bad = {k: v for k, v in IMPORTED.items() if k != "confirm_status"}
        self.assertTrue(any("confirm_status" in e for e in cd.check_file(write([bad]))))

    def test_duplicate_id(self):
        self.assertTrue(any("duplicate" in e for e in cd.check_file(write([FOUNDER, FOUNDER]))))

    def test_supersedes_must_point_back(self):
        later = dict(FOUNDER, supersedes="D-2026-10-14-01")
        self.assertEqual(cd.check_file(write([IMPORTED, later])), [])
        self.assertTrue(cd.check_file(write([later, IMPORTED])))

    def test_id_date_mismatch(self):
        bad = dict(FOUNDER, id="D-2026-10-15-01")
        self.assertTrue(any("id date" in e for e in cd.check_file(write([bad]))))

    def test_bad_json(self):
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        f.write("{not json")
        f.close()
        self.assertTrue(any("invalid JSON" in e for e in cd.check_file(f.name)))


if __name__ == "__main__":
    unittest.main()
