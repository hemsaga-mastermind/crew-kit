"""crewkit gates - doc 05: a kill line written after the test started does not count."""
from crewkit import FAIL, PASS, UNKNOWN, VERSION
from crewkit import records as rec
from crewkit.result import Coverage, check


def _validate(row):
    errors = []
    extra = sorted(set(row) - rec.GATE_KEYS - {"_line"})
    if extra:
        errors.append("unknown key(s) %s" % ", ".join(repr(k) for k in extra))
    for key in rec.GATE_REQUIRED:
        if key not in row:
            errors.append("missing required key %r" % key)
    if errors:
        return errors
    if row["gate"] not in rec.GATES:
        errors.append("gate %r is not one of %s" % (row["gate"], ", ".join(rec.GATES)))
    if row["status"] not in rec.GATE_STATUS:
        errors.append("status %r is not one of %s" % (row["status"], ", ".join(rec.GATE_STATUS)))
    for key in ("kill_line_written", "test_started", "decided"):
        if key in row and not rec.DATE_RE.match(str(row[key])):
            errors.append("%s %r is not YYYY-MM-DD" % (key, row[key]))
    if not isinstance(row["kill_line"], str):
        errors.append("kill_line must be a string")
    return errors


def run(manifest, asof=None):
    cov = Coverage()
    path = manifest["gates"]
    rows, read_errors = rec.read_jsonl(path)
    errors = []
    gates = []
    if rows is None:
        cov.unreadable(path, read_errors[0].split(": ", 1)[-1])
    else:
        cov.read(path)
        errors += ["%s: %s" % (path, m) for m in read_errors]
        for row in rows:
            problems = _validate(row)
            if problems:
                errors.append("%s line %d: %s" % (path, row["_line"], "; ".join(problems)))
                continue
            if row["kill_line"].strip():
                present = check("kill_line_present", PASS, "kill line recorded", path)
            else:
                present = check("kill_line_present", FAIL,
                                "no kill line: there is nothing to stop this product", path)
            started = row.get("test_started")
            if not started:
                pre = check("pre_registered", UNKNOWN,
                            "no test_started, so the test has not begun and pre-registration "
                            "cannot be checked yet", path)
            elif row["kill_line_written"] <= started:
                # Both dates are self-reported fields in a file the author writes, with no
                # hash and no chain, so writing them in one sitting passes. Doc 05 calls
                # pre-registration the easiest rule to fudge and this check is fudgeable by
                # typing; v0.4 should derive the date from the commit that added the row,
                # which the author does not control. Until then the detail says so.
                pre = check("pre_registered", PASS,
                            "kill line written %s, test started %s - both self-reported in "
                            "this file, so this is the order claimed, not the order proved"
                            % (row["kill_line_written"], started), path)
            else:
                pre = check("pre_registered", FAIL,
                            "kill line written %s, after the test started %s - a kill line "
                            "written after the result has been seen does not count (doc 05)"
                            % (row["kill_line_written"], started), path)
            gates.append({
                "product": row["product"],
                "gate": row["gate"],
                "status": row["status"],
                "line": row["_line"],
                "checks": {"kill_line_present": present, "pre_registered": pre},
            })
    gates.sort(key=lambda g: (g["product"], g["gate"], g["line"]))
    return {
        "crew_kit": VERSION,
        "command": "gates",
        "crew": manifest["crew"],
        "asof": asof.isoformat() if asof else None,
        "gates": gates,
        "errors": sorted(errors),
        "summary": {"gates": len(gates), "errors": len(errors)},
        "coverage": cov.as_dict(),
    }


def text(result):
    lines = ["gates: %s" % result["crew"]]
    for row in result["gates"]:
        lines.append("")
        lines.append("%-16s %s (%s)" % (row["product"], row["gate"], row["status"]))
        for key in ("kill_line_present", "pre_registered"):
            c = row["checks"][key]
            lines.append("  %-8s %-18s %s" % (c["verdict"], c["id"], c["detail"]))
    for message in result["errors"]:
        lines.append("error: %s" % message)
    for message in result["coverage"]["unreadable"]:
        lines.append("could not read %s" % message)
    return "\n".join(lines)
