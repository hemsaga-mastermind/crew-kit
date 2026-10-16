"""Validate a Crew Kit decision log (one JSON object per line).

Usage: python3 -I tools/check_decisions.py [path]   (default: ./decisions.jsonl)
Exit 0 when every line is valid, 1 otherwise (errors printed one per line).
"""
import json
import re
import sys
from pathlib import Path

KINDS = {"founder", "proxy", "bot", "imported"}
FOUNDER_SOURCES = {"founder_session", "telegram_signed", "commit_signed"}
CONFIRM = {"pending", "confirmed", "rejected"}
ID_RE = re.compile(r"^D-\d{4}-\d{2}-\d{2}-\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED = ("id", "date", "kind", "text", "source")


def check_entry(e, seen):
    errs = []
    for f in REQUIRED:
        if f not in e:
            errs.append(f"missing field '{f}'")
    if errs:
        return errs
    if not ID_RE.match(str(e["id"])):
        errs.append(f"bad id {e['id']!r} (want D-YYYY-MM-DD-NN)")
    elif e["id"] in seen:
        errs.append(f"duplicate id {e['id']}")
    if not DATE_RE.match(str(e["date"])):
        errs.append(f"bad date {e['date']!r}")
    elif not str(e["id"]).startswith(f"D-{e['date']}-"):
        errs.append("id date does not match date")
    kind = e["kind"]
    if kind not in KINDS:
        errs.append(f"unknown kind {kind!r}")
    if not str(e["text"]).strip():
        errs.append("empty text")
    src = e["source"]
    if not isinstance(src, dict) or not src.get("type"):
        errs.append("source must be an object with a 'type'")
        return errs
    if kind == "founder" and src["type"] not in FOUNDER_SOURCES:
        errs.append(f"founder entry needs source.type in {sorted(FOUNDER_SOURCES)}")
    if kind == "proxy" and not src.get("mandate"):
        errs.append("proxy entry needs source.mandate")
    if kind == "bot" and not src.get("bot"):
        errs.append("bot entry needs source.bot")
    if kind == "imported":
        if e.get("confirm_status") not in CONFIRM:
            errs.append(f"imported entry needs confirm_status in {sorted(CONFIRM)}")
        if not src.get("path"):
            errs.append("imported entry needs source.path")
    sup = e.get("supersedes")
    if sup is not None and sup not in seen:
        errs.append(f"supersedes unknown or later id {sup}")
    return errs


def check_file(path):
    errors, seen = [], set()
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {n}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(e, dict):
            errors.append(f"line {n}: not an object")
            continue
        errors += [f"line {n}: {m}" for m in check_entry(e, seen)]
        if "id" in e:
            seen.add(e["id"])
    return errors


def main(argv):
    path = argv[1] if len(argv) > 1 else Path("decisions.jsonl")
    errors = check_file(path)
    for m in errors:
        print(m)
    if not errors:
        print(f"ok: {path}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
