"""Build throwaway Crew Kit workspaces for the acceptance tests."""
import json
from pathlib import Path

MANIFEST = {
    "crew_kit": "0.3",
    "crew": "testcrew",
    "journal": "records/decisions.jsonl",
    "gates": "records/gates.jsonl",
    "agents": [
        {
            "id": "operator",
            "folder": "agents/operator",
            "autonomy": "A",
            "wakes": ["cron: daily 07:00"],
            "actions": [{"name": "weekly status", "irreversible": False, "gate": "none"}],
        }
    ],
}

STATE = """---
agent: operator
status: green
updated: {updated}
---

Prose below the block is not read.
"""

STATUS = """STATUS operator {date}
Done: one line
Next: one line
Blocked: none
Risks: none
Decisions needed: none
"""

HANDOFF = """---
from: builder
to: operator
sent: {sent}
ask: review the spec
acceptance_test: operator replies with pass or fail
{answered}---

Evidence: SPEC-0.3.md
"""


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def workspace(root, manifest=None, agents=None):
    """A healthy one-agent workspace. `agents` maps agent id -> dict of files."""
    root = Path(root)
    man = json.loads(json.dumps(MANIFEST)) if manifest is None else manifest
    write(root / "crew.json", json.dumps(man, indent=2))
    for agent in man.get("agents", []):
        folder = root / agent["folder"]
        files = (agents or {}).get(agent["id"], {})
        for name, text in files.items():
            if text is None:
                continue
            write(folder / name, text)
    return root


def healthy(root, asof="2026-10-21"):
    """Every health check that can pass, passes."""
    man = json.loads(json.dumps(MANIFEST))
    workspace(
        root,
        man,
        {
            "operator": {
                "charter.md": "# operator charter\n",
                "contract.md": CONTRACT.format(extra=""),
                "state.md": STATE.format(updated=asof),
                "backlog.md": "- [ ] 12 | owner: operator | due: 2026-11-30 | Ship v0.3\n",
                "status/%s.md" % asof: STATUS.format(date=asof),
            }
        },
    )
    write(root / "handoffs/.keep", "")
    write(root / "records/decisions.jsonl", "")
    write(root / "records/gates.jsonl", "")
    return Path(root)


CONTRACT = """# Contract: operator

## I deliver
- the weekly health table, judged by: `crewkit health --strict` exits 0 or the reds are named
{extra}
## I am owed
- a decision on an escalation from founder, within 48h
- read access to every agent folder, at level A

## Done means
- the health table exists for the current week and every red has a named owner

## If I cannot
- hand back to founder, within 24h, recording why

## Breach
- mine: no health table for two weeks -> demote
- yours: an escalation unanswered for 48h -> the role goes amber and founder is named in the event log
"""

NODES = {
    "crew_kit": "0.3",
    "nodes": [
        {
            "name": "vm-1",
            "class": "authoritative",
            "capabilities": {"always_on": True, "ram_mb": 2048, "python": ["3.12"], "os": "linux"},
            "grants": {"may_send_mail": True, "may_schedule": True, "may_hold_secrets": True},
            "products": ["example"],
            "max_concurrent_roles": 3,
        }
    ],
}
