"""crewkit lint - structure only (doc 01 fix 2, doc 03, doc 04, doc 05).

Runs nothing, judges no content, and has no `unknown`: either the structure is
there or it is not.
"""
from pathlib import Path

from crewkit import VERSION
from crewkit import records as rec
from crewkit.health import read_handoffs
from crewkit.result import Coverage

CODES = {
    "L01": "no state.md",
    "L02": "no backlog.md",
    "L03": "no charter.md",
    "L04": "a backlog line that does not parse",
    "L05": "an open backlog item with no owner or no due date",
    "L06": "a handoff addressed to a lane nothing wakes",
    "L07": "autonomy B without all six controls",
    "L08": "an irreversible action with no gate",
    "L09": "an agent with no wakes",
}


def _finding(agent, code, detail, path):
    return {"agent": agent, "code": code, "finding": CODES[code], "detail": detail,
            "evidence": str(path)}


def run(manifest, asof=None):
    cov = Coverage()
    cov.read(manifest["root"] / "crew.json")
    findings = []
    ids = {a["id"] for a in manifest["agents"]}

    for agent in manifest["agents"]:
        aid = agent["id"]
        folder = Path(agent["folder"])
        for name, code in (("state.md", "L01"), ("backlog.md", "L02"), ("charter.md", "L03")):
            path = folder / name
            if path.exists():
                cov.read(path)
            else:
                cov.unreadable(path, "not found")
                findings.append(_finding(aid, code, "%s is missing" % name, path))

        backlog = folder / "backlog.md"
        text, error = rec.read_text(backlog)
        if text is not None:
            items, errors = rec.parse_backlog(text)
            for message in errors:
                findings.append(_finding(aid, "L04", message, backlog))
            for item in items:
                if item.get("missing"):
                    findings.append(_finding(
                        aid, "L05", "line %d: item #%d has no %s"
                        % (item["line"], item["id"], " and no ".join(item["missing"])), backlog))

        if agent["autonomy"] == "B":
            missing = [c for c in rec.CONTROLS if c not in agent["controls"]]
            if missing:
                findings.append(_finding(
                    aid, "L07",
                    "autonomy B is claimed but these controls are not declared: %s. "
                    "Doc 05: level B is earned per system, not declared." % ", ".join(missing),
                    manifest["root"] / "crew.json"))

        for action in agent["actions"]:
            if action["irreversible"] and action["gate"] == "none":
                findings.append(_finding(
                    aid, "L08", "action %r is irreversible and reachable with no gate"
                    % action["name"], manifest["root"] / "crew.json"))

        if not agent["wakes"]:
            findings.append(_finding(
                aid, "L09", "no wakes declared: nothing will start this agent, so it will sit "
                "idle with a full backlog (doc 01)", manifest["root"] / "crew.json"))

    handoffs, unparseable, error = read_handoffs(manifest["handoffs"], cov)
    for path, fields in handoffs:
        if fields["to"] not in ids:
            findings.append(_finding(
                fields["from"] if fields["from"] in ids else "",
                "L06", "handoff is addressed to %r, which is not an agent in crew.json"
                % fields["to"], path))
    for message in unparseable:
        findings.append(_finding("", "L04", "handoff %s" % message, manifest["handoffs"]))

    findings.sort(key=lambda f: (f["agent"], f["code"], f["evidence"], f["detail"]))
    return {
        "crew_kit": VERSION,
        "command": "lint",
        "crew": manifest["crew"],
        "findings": findings,
        "summary": {"findings": len(findings)},
        "coverage": cov.as_dict(),
    }


def text(result):
    if not result["findings"]:
        return "lint: %s - no findings" % result["crew"]
    lines = ["lint: %s - %d finding(s)" % (result["crew"], len(result["findings"]))]
    for f in result["findings"]:
        lines.append("  %s %-14s %s" % (f["code"], f["agent"] or "-", f["detail"]))
        lines.append("  %s %-14s %s" % ("   ", "", f["evidence"]))
    return "\n".join(lines)
