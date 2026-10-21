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
    "L10": "no contract.md",
    "L11": "a contract missing a required section",
    "L12": "a deliverable with no oracle",
    "L13": "a needs capability no node can satisfy",
    "L14": "a permission capability declared as a self-reported capability",
}


def _finding(agent, code, detail, path):
    return {"agent": agent, "code": code, "finding": CODES[code], "detail": detail,
            "evidence": str(path)}


def _placement(manifest, cov):
    """Work declares requirements, nodes declare capabilities, and a program matches them.

    With no nodes.json there is one node and everything runs there, so there is nothing to
    check. A declared need with nothing to satisfy it is a finding, never a requirement to
    be quietly degraded until it fits whichever machine happens to be up.
    """
    nodes = manifest["nodes"]
    findings = []
    if nodes is not None:
        cov.read(nodes[0]["path"])
        for node in nodes:
            for name in sorted(node["capabilities"]):
                if name in rec.PERMISSION_CAPS:
                    findings.append(_finding(
                        "", "L14", "node %r declares %r among its capabilities; a permission is "
                        "a grant from the founder and belongs in 'grants', because a node cannot "
                        "assert its own right to it" % (node["name"], name), node["path"]))
    for agent in manifest["agents"]:
        for need in agent["needs"]:
            if nodes is None:
                findings.append(_finding(
                    agent["id"], "L13", "needs %r, but there is no nodes.json, so nothing "
                    "declares that capability" % need, manifest["root"] / "crew.json"))
                continue
            if not any(_satisfies(node, need) for node in nodes):
                findings.append(_finding(
                    agent["id"], "L13", "needs %r and no node provides it" % need,
                    nodes[0]["path"]))
    return findings


def _satisfies(node, need):
    """A permission counts only as a grant; capacity may be self-reported."""
    source = node["grants"] if need in rec.PERMISSION_CAPS else node["capabilities"]
    return source.get(need) not in (None, False)


def run(manifest, asof=None):
    cov = Coverage()
    cov.read(manifest["root"] / "crew.json")
    findings = []
    ids = {a["id"] for a in manifest["agents"]}

    for agent in manifest["agents"]:
        aid = agent["id"]
        folder = Path(agent["folder"])
        for name, code in (("state.md", "L01"), ("backlog.md", "L02"), ("charter.md", "L03"),
                           ("contract.md", "L10")):
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

        contract = folder / "contract.md"
        text, error = rec.read_text(contract)
        if text is not None:
            deliverables, errors = rec.parse_contract(text)
            for message in errors:
                findings.append(_finding(aid, "L11", message, contract))
            if not deliverables:
                findings.append(_finding(
                    aid, "L12", "the contract names no deliverable at all, so nothing can be "
                    "judged and the role may not act autonomously under it", contract))
            for line, body, oracle in deliverables:
                if not oracle:
                    findings.append(_finding(
                        aid, "L12", "line %d: deliverable %r names no oracle after %r, so the "
                        "role may not act autonomously under it (an agent may act alone exactly "
                        "when something that did not produce the output can tell it was right)"
                        % (line, body, rec.ORACLE_MARKER), contract))

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

    findings += _placement(manifest, cov)

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
