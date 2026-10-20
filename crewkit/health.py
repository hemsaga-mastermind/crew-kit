"""crewkit health - doc 01 fix 4, the weekly health check, mechanised."""
import datetime
from pathlib import Path

from crewkit import FAIL, PASS, UNKNOWN, VERSION
from crewkit import records as rec
from crewkit.result import Coverage, check, colour

WINDOW_DAYS = 7
HANDOFF_HOURS = 48


def _date(value):
    return datetime.date(int(value[0:4]), int(value[5:7]), int(value[8:10]))


def _state_fresh(folder, asof, cov):
    path = folder / "state.md"
    text, error = rec.read_text(path)
    if text is None:
        cov.unreadable(path, error)
        return check("state_fresh", UNKNOWN, "state.md %s" % error, path)
    cov.read(path)
    fields, errors = rec.parse_state(text)
    if errors:
        return check("state_fresh", UNKNOWN, "state.md is unparseable: " + "; ".join(errors), path)
    updated = _date(fields["updated"])
    age = (asof - updated).days
    if age < 0:
        return check("state_fresh", FAIL, "updated %s is in the future (as of %s)"
                     % (fields["updated"], asof), path)
    if age > WINDOW_DAYS:
        return check("state_fresh", FAIL, "last updated %s, %d days ago" % (fields["updated"], age), path)
    return check("state_fresh", PASS, "updated %s, %d days ago" % (fields["updated"], age), path)


def _status_sent(folder, asof, cov):
    directory = folder / "status"
    try:
        names = sorted(p.name for p in directory.iterdir() if p.is_file())
    except OSError as exc:
        cov.unreadable(directory, exc.strerror or "unreadable")
        return check("status_sent", UNKNOWN, "status folder %s" % (exc.strerror or "unreadable"), directory)
    cov.read(directory)
    inside, unparseable = [], []
    for name in names:
        stem = name[:-3] if name.endswith(".md") else None
        if not stem or not rec.DATE_RE.match(stem):
            continue
        sent = _date(stem)
        if not 0 <= (asof - sent).days <= WINDOW_DAYS:
            continue
        path = directory / name
        text, error = rec.read_text(path)
        if text is None:
            cov.unreadable(path, error)
            continue
        cov.read(path)
        errors = rec.parse_status(text)
        if errors:
            unparseable.append("%s (%s)" % (name, "; ".join(errors)))
        else:
            inside.append(name)
    if inside:
        return check("status_sent", PASS, "status %s" % ", ".join(inside), directory)
    if unparseable:
        return check("status_sent", FAIL, "no complete status in the last %d days; unparseable: %s"
                     % (WINDOW_DAYS, ", ".join(unparseable)), directory)
    return check("status_sent", FAIL, "no status in the %d days to %s" % (WINDOW_DAYS, asof), directory)


def _backlog_overdue(folder, asof, cov):
    path = folder / "backlog.md"
    text, error = rec.read_text(path)
    if text is None:
        cov.unreadable(path, error)
        return check("backlog_overdue", UNKNOWN, "backlog.md %s" % error, path)
    cov.read(path)
    items, errors = rec.parse_backlog(text)
    if errors:
        return check("backlog_overdue", UNKNOWN,
                     "backlog.md has unparseable item lines, so overdue cannot be computed: "
                     + "; ".join(errors), path)
    late = []
    for item in items:
        if item["closed"]:
            continue
        if (asof - _date(item["due"])).days > WINDOW_DAYS:
            late.append("#%d due %s" % (item["id"], item["due"]))
    if late:
        return check("backlog_overdue", FAIL, "overdue by more than %d days: %s"
                     % (WINDOW_DAYS, ", ".join(late)), path)
    open_count = sum(1 for i in items if not i["closed"])
    return check("backlog_overdue", PASS, "%d open item(s), none more than %d days overdue"
                 % (open_count, WINDOW_DAYS), path)


def read_handoffs(directory, cov):
    """Returns (handoffs, unparseable, error). A handoff is (path, fields)."""
    try:
        paths = sorted(p for p in Path(directory).iterdir() if p.is_file() and p.suffix == ".md")
    except OSError as exc:
        cov.unreadable(directory, exc.strerror or "unreadable")
        return [], [], exc.strerror or "unreadable"
    cov.read(directory)
    handoffs, unparseable = [], []
    for path in paths:
        text, error = rec.read_text(path)
        if text is None:
            cov.unreadable(path, error)
            unparseable.append("%s (%s)" % (path.name, error))
            continue
        cov.read(path)
        fields, errors = rec.parse_handoff(text)
        if errors:
            unparseable.append("%s (%s)" % (path.name, "; ".join(errors)))
            continue
        handoffs.append((path, fields))
    return handoffs, unparseable, None


def _handoff_answered(agent_id, directory, asof, cov, cache):
    if "handoffs" not in cache:
        cache["handoffs"] = read_handoffs(directory, cov)
    handoffs, unparseable, error = cache["handoffs"]
    if error:
        return check("handoff_answered", UNKNOWN, "handoffs folder %s" % error, directory)
    if unparseable:
        return check("handoff_answered", UNKNOWN,
                     "unparseable handoff(s), so this cannot be answered: " + ", ".join(unparseable),
                     directory)
    late = []
    for path, fields in handoffs:
        if fields["to"] != agent_id or fields.get("answered"):
            continue
        if (asof - _date(fields["sent"])).days * 24 >= HANDOFF_HOURS:
            late.append("%s (sent %s)" % (path.name, fields["sent"]))
    if late:
        return check("handoff_answered", FAIL, "unanswered after %dh: %s"
                     % (HANDOFF_HOURS, ", ".join(late)), directory)
    mine = sum(1 for _, f in handoffs if f["to"] == agent_id)
    return check("handoff_answered", PASS, "%d handoff(s) addressed here, none late" % mine, directory)


def _rule_slips(folder, asof, cov):
    path = folder / "slips.jsonl"
    if not path.exists():
        return check("rule_slips", UNKNOWN,
                     "no slips.jsonl: the engine cannot see money, sends or public posts, "
                     "so this is unknown, not green", path)
    rows, errors = rec.read_jsonl(path)
    if rows is None or errors:
        cov.unreadable(path, "; ".join(errors) if errors else "unreadable")
        return check("rule_slips", UNKNOWN, "slips.jsonl is unparseable: "
                     + "; ".join(errors or ["unreadable"]), path)
    cov.read(path)
    window = [r for r in rows
              if isinstance(r.get("date"), str) and rec.DATE_RE.match(r["date"])
              and 0 <= (asof - _date(r["date"])).days <= WINDOW_DAYS]
    if window:
        return check("rule_slips", FAIL, "%d slip(s) in the last %d days: %s"
                     % (len(window), WINDOW_DAYS,
                        ", ".join(sorted("%s rule %s" % (r["date"], r.get("rule", "?")) for r in window))),
                     path)
    return check("rule_slips", PASS, "slips.jsonl present, none in the last %d days" % WINDOW_DAYS, path)


def run(manifest, asof):
    cov = Coverage()
    cov.read(manifest["root"] / "crew.json")
    cache = {}
    agents = []
    for agent in manifest["agents"]:
        folder = Path(agent["folder"])
        checks = [
            _state_fresh(folder, asof, cov),
            _status_sent(folder, asof, cov),
            _backlog_overdue(folder, asof, cov),
            _handoff_answered(agent["id"], manifest["handoffs"], asof, cov, cache),
            _rule_slips(folder, asof, cov),
        ]
        agents.append({
            "id": agent["id"],
            "autonomy": agent["autonomy"],
            "colour": colour(checks),
            "checks": checks,
        })
    counts = {"green": 0, "amber": 0, "red": 0}
    for a in agents:
        counts[a["colour"]] += 1
    return {
        "crew_kit": VERSION,
        "command": "health",
        "crew": manifest["crew"],
        "asof": asof.isoformat(),
        "window_days": WINDOW_DAYS,
        "agents": agents,
        "summary": dict(counts, unknown_checks=sum(
            1 for a in agents for c in a["checks"] if c["verdict"] == UNKNOWN)),
        "coverage": cov.as_dict(),
        "not_implemented": ["two reds in a row (doc 01) needs history the engine does not keep"],
    }


def text(result):
    lines = ["health: %s, as of %s (window %d days)"
             % (result["crew"], result["asof"], result["window_days"])]
    for agent in result["agents"]:
        lines.append("")
        lines.append("%-14s %s" % (agent["id"], agent["colour"].upper()))
        for c in agent["checks"]:
            lines.append("  %-8s %-18s %s" % (c["verdict"], c["id"], c["detail"]))
    s = result["summary"]
    lines.append("")
    lines.append("green %d  amber %d  red %d  unknown checks %d"
                 % (s["green"], s["amber"], s["red"], s["unknown_checks"]))
    for path in result["coverage"]["unreadable"]:
        lines.append("could not read %s" % path)
    return "\n".join(lines)
