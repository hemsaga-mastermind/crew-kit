"""crewkit verify - the decision journal: v0.1 schema, plus the v0.3 hash chain.

This module is the single source of truth for the decision-log schema;
tools/check_decisions.py is a thin wrapper around it, so the v0.1 command keeps working.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from crewkit import FAIL, PASS, UNKNOWN, VERSION
from crewkit import records as rec
from crewkit.result import Coverage, check

KINDS = {"founder", "proxy", "bot", "imported"}
FOUNDER_SOURCES = {"founder_session", "telegram_signed", "commit_signed"}
CONFIRM = {"pending", "confirmed", "rejected"}
ID_RE = re.compile(r"^D-\d{4}-\d{2}-\d{2}-\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED = ("id", "date", "kind", "text", "source")
CHAIN_KEYS = ("prev", "hash")


def check_entry(e, seen):
    """The v0.1 schema check. Returns a list of messages."""
    errs = []
    for f in REQUIRED:
        if f not in e:
            errs.append("missing field '%s'" % f)
    if errs:
        return errs
    if not ID_RE.match(str(e["id"])):
        errs.append("bad id %r (want D-YYYY-MM-DD-NN)" % e["id"])
    elif e["id"] in seen:
        errs.append("duplicate id %s" % e["id"])
    if not DATE_RE.match(str(e["date"])):
        errs.append("bad date %r" % e["date"])
    elif not str(e["id"]).startswith("D-%s-" % e["date"]):
        errs.append("id date does not match date")
    kind = e["kind"]
    if kind not in KINDS:
        errs.append("unknown kind %r" % kind)
    if not str(e["text"]).strip():
        errs.append("empty text")
    src = e["source"]
    if not isinstance(src, dict) or not src.get("type"):
        errs.append("source must be an object with a 'type'")
        return errs
    if kind == "founder" and src["type"] not in FOUNDER_SOURCES:
        errs.append("founder entry needs source.type in %s" % sorted(FOUNDER_SOURCES))
    if kind == "proxy" and not src.get("mandate"):
        errs.append("proxy entry needs source.mandate")
    if kind == "bot" and not src.get("bot"):
        errs.append("bot entry needs source.bot")
    if kind == "imported":
        if e.get("confirm_status") not in CONFIRM:
            errs.append("imported entry needs confirm_status in %s" % sorted(CONFIRM))
        if not src.get("path"):
            errs.append("imported entry needs source.path")
    sup = e.get("supersedes")
    if sup is not None and sup not in seen:
        errs.append("supersedes unknown or later id %s" % sup)
    return errs


def check_file(path):
    """Schema-check a decision log. Returns a list of messages, empty when valid."""
    errors, seen = [], set()
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return ["%s: %s" % (path, exc.strerror or "unreadable")]
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append("line %d: invalid JSON (%s)" % (n, exc.msg))
            continue
        if not isinstance(e, dict):
            errors.append("line %d: not an object" % n)
            continue
        errors += ["line %d: %s" % (n, m) for m in check_entry(e, seen)]
        if "id" in e:
            seen.add(e["id"])
    return errors


def record_hash(record):
    """SHA-256 of the record's canonical JSON, every key except 'hash'."""
    body = {k: v for k, v in record.items() if k not in ("hash", "_line")}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_chain(records):
    """(verdict, detail). Unchained is unknown; half-chained or broken is a fail."""
    chained = [r for r in records if "hash" in r]
    if not records:
        return UNKNOWN, "journal is empty, so the chain is not chained"
    if not chained:
        return UNKNOWN, ("journal is not chained: no record carries a hash, so it is append-only "
                         "by convention only and tampering would leave no trace")
    if len(chained) != len(records):
        plain = [r["_line"] for r in records if "hash" not in r]
        return FAIL, ("journal is partly chained: no hash on line(s) %s"
                      % ", ".join(str(n) for n in plain))
    prev = None
    for record in records:
        expected = record_hash(record)
        if record.get("prev") != prev:
            return FAIL, ("line %d: prev is %r, expected %r"
                          % (record["_line"], record.get("prev"), prev))
        if record["hash"] != expected:
            return FAIL, ("line %d: hash does not match the record's contents "
                          "(stored %s, computed %s) - the record was edited after it was written"
                          % (record["_line"], record["hash"][:12], expected[:12]))
        prev = record["hash"]
    return PASS, "%d record(s), chain intact" % len(records)


def run(manifest, asof=None):
    cov = Coverage()
    path = manifest["journal"]
    records, read_errors = rec.read_jsonl(path)
    if records is None:
        cov.unreadable(path, read_errors[0].split(": ", 1)[-1])
        schema = check("schema", UNKNOWN, "journal %s" % read_errors[0], path)
        chain = check("chain", UNKNOWN, "journal could not be read", path)
    else:
        cov.read(path)
        schema_errors = read_errors + check_file(path)
        if schema_errors:
            schema = check("schema", FAIL, "; ".join(schema_errors), path)
        else:
            schema = check("schema", PASS, "%d record(s), all valid" % len(records), path)
        verdict, detail = check_chain(records)
        chain = check("chain", verdict, detail, path)
    return {
        "crew_kit": VERSION,
        "command": "verify",
        "crew": manifest["crew"],
        "checks": {"schema": schema, "chain": chain},
        "coverage": cov.as_dict(),
    }


def text(result):
    lines = ["verify: %s" % result["checks"]["schema"]["evidence"]]
    for key in ("schema", "chain"):
        c = result["checks"][key]
        lines.append("  %-8s %-8s %s" % (c["verdict"], c["id"], c["detail"]))
    return "\n".join(lines)


def main(argv):
    """The v0.1 command: schema-check one decision log."""
    path = argv[1] if len(argv) > 1 else Path("decisions.jsonl")
    errors = check_file(path)
    for m in errors:
        print(m)
    if not errors:
        print("ok: %s" % path)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
