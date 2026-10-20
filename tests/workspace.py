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
