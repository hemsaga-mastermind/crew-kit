"""Strict readers for the record layer (SPEC-0.3.md section 2).

Nothing here infers a value from prose. A file that is not in the specified
shape comes back with errors, and the caller turns that into `unknown`.
"""
import json
import re
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEY_RE = re.compile(r"^[a-z_]+$")
ID_RE = re.compile(r"^[a-z0-9-]+$")
CHECKBOX_RE = re.compile(r"^- \[( |x)\] (.*)$")

CONTROLS = ("branch_protection", "ci_gates", "monitoring", "rollback", "kill_switch", "budgets")
GATES = ("G0", "G1", "G2", "G3")
GATE_STATUS = ("open", "passed", "killed")
AUTONOMY = ("A", "B", "C")
ACTION_GATES = ("none", "automated", "founder")
STATUS_COLOURS = ("green", "amber", "red")
STATUS_LINES = ("Done:", "Next:", "Blocked:", "Risks:", "Decisions needed:")

MANIFEST_KEYS = {"crew_kit", "crew", "journal", "gates", "handoffs", "agents"}
MANIFEST_REQUIRED = ("crew_kit", "crew", "agents")
AGENT_KEYS = {"id", "folder", "autonomy", "lane", "wakes", "controls", "actions"}
AGENT_REQUIRED = ("id", "folder", "autonomy")
ACTION_KEYS = {"name", "irreversible", "gate"}
STATE_KEYS = {"agent", "status", "updated", "lane", "autonomy", "waiting_on"}
STATE_REQUIRED = ("agent", "status", "updated")
HANDOFF_KEYS = {"from", "to", "sent", "ask", "acceptance_test", "answered", "cc", "founder_needed"}
HANDOFF_REQUIRED = ("from", "to", "sent", "ask", "acceptance_test")
GATE_KEYS = {"product", "gate", "kill_line", "kill_line_written", "test_started", "status", "decided"}
GATE_REQUIRED = ("product", "gate", "kill_line", "kill_line_written", "status")


class ManifestError(Exception):
    """A manifest the engine cannot trust. Fatal: every verdict below it would be noise."""


def read_text(path):
    """(text, error). Never raises."""
    try:
        return Path(path).read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return None, "not found"
    except OSError as exc:
        return None, "unreadable (%s)" % exc.strerror
    except UnicodeDecodeError:
        return None, "not UTF-8"


def parse_header(text, allowed, required):
    """Parse a header block. Returns (fields, errors)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ["line 1: no header block (expected a line containing only ---)"]
    fields, errors = {}, []
    closed = False
    for n, line in enumerate(lines[1:], 2):
        if line.strip() == "---":
            closed = True
            break
        if not line.strip():
            errors.append("line %d: blank line inside the header block" % n)
            continue
        if ": " not in line:
            errors.append("line %d: not a 'key: value' line" % n)
            continue
        key, value = line.split(": ", 1)
        if not KEY_RE.match(key):
            errors.append("line %d: bad key %r" % (n, key))
            continue
        if key in fields:
            errors.append("line %d: duplicate key %r" % (n, key))
            continue
        if key not in allowed:
            errors.append("line %d: key %r is not one of %s" % (n, key, ", ".join(sorted(allowed))))
            continue
        fields[key] = value.strip()
    if not closed:
        errors.append("header block is not closed")
    for key in required:
        if key not in fields:
            errors.append("missing required key %r" % key)
    return fields, errors


def parse_state(text):
    fields, errors = parse_header(text, STATE_KEYS, STATE_REQUIRED)
    if "updated" in fields and not DATE_RE.match(fields["updated"]):
        errors.append("updated %r is not YYYY-MM-DD" % fields["updated"])
    if "status" in fields and fields["status"] not in STATUS_COLOURS:
        errors.append("status %r is not one of %s" % (fields["status"], ", ".join(STATUS_COLOURS)))
    return fields, errors


def parse_handoff(text):
    fields, errors = parse_header(text, HANDOFF_KEYS, HANDOFF_REQUIRED)
    for key in ("sent", "answered"):
        if key in fields and not DATE_RE.match(fields[key]):
            errors.append("%s %r is not YYYY-MM-DD" % (key, fields[key]))
    return fields, errors


def parse_backlog(text):
    """Returns (items, errors). Only checkbox lines are read; others are prose."""
    items, errors = [], []
    for n, line in enumerate(text.splitlines(), 1):
        match = CHECKBOX_RE.match(line.rstrip())
        if not match:
            continue
        done = match.group(1) == "x"
        parts = [p.strip() for p in match.group(2).split("|")]
        if len(parts) < 3:
            errors.append("line %d: too few fields (want id | owner: | due: | text)" % n)
            continue
        item = {"closed": done, "line": n}
        if not parts[0].isdigit():
            errors.append("line %d: %r is not an integer id" % (n, parts[0]))
            continue
        item["id"] = int(parts[0])
        for part in parts[1:-1]:
            if ": " not in part:
                errors.append("line %d: field %r is not 'key: value'" % (n, part))
                break
            key, value = part.split(": ", 1)
            if key not in ("owner", "due", "done"):
                errors.append("line %d: unknown field %r" % (n, key))
                break
            item[key] = value.strip()
        else:
            item["text"] = parts[-1]
            missing = [k for k in ("owner", "due") if k not in item]
            if missing:
                item["missing"] = missing
            for key in ("due", "done"):
                if key in item and not DATE_RE.match(item[key]):
                    errors.append("line %d: %s %r is not YYYY-MM-DD" % (n, key, item[key]))
                    item["bad_date"] = True
            if done and "done" not in item:
                errors.append("line %d: a done item needs 'done: <date>'" % n)
                item["bad_date"] = True
            items.append(item)
    return items, errors


def parse_status(text):
    """A status file is parseable only with all five lines present exactly once."""
    errors = []
    for label in STATUS_LINES:
        count = sum(1 for line in text.splitlines() if line.startswith(label))
        if count != 1:
            errors.append("expected one %r line, found %d" % (label, count))
    return errors


def read_jsonl(path):
    """Returns (records, errors). Each record gains '_line'."""
    text, error = read_text(path)
    if text is None:
        return None, ["%s: %s" % (path, error)]
    records, errors = [], []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append("line %d: invalid JSON (%s)" % (n, exc.msg))
            continue
        if not isinstance(obj, dict):
            errors.append("line %d: not an object" % n)
            continue
        obj["_line"] = n
        records.append(obj)
    return records, errors


def _reject_unknown(obj, allowed, where):
    extra = sorted(set(obj) - allowed)
    if extra:
        raise ManifestError("%s: unknown key(s) %s" % (where, ", ".join(repr(k) for k in extra)))


def load_manifest(root):
    """Read and validate crew.json. Raises ManifestError."""
    root = Path(root)
    text, error = read_text(root / "crew.json")
    if text is None:
        raise ManifestError("%s: %s" % (root / "crew.json", error))
    try:
        man = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError("crew.json: invalid JSON (%s)" % exc.msg)
    if not isinstance(man, dict):
        raise ManifestError("crew.json: not an object")
    _reject_unknown(man, MANIFEST_KEYS, "crew.json")
    for key in MANIFEST_REQUIRED:
        if key not in man:
            raise ManifestError("crew.json: missing required key %r" % key)
    from crewkit import VERSION
    if man["crew_kit"] != VERSION:
        raise ManifestError("crew.json: crew_kit is %r, this engine reads %r" % (man["crew_kit"], VERSION))
    if not isinstance(man["agents"], list) or not man["agents"]:
        raise ManifestError("crew.json: 'agents' must be a non-empty list")

    agents, seen = [], set()
    for raw in man["agents"]:
        if not isinstance(raw, dict):
            raise ManifestError("crew.json: an agent is not an object")
        where = "crew.json: agent %r" % raw.get("id", "?")
        _reject_unknown(raw, AGENT_KEYS, where)
        for key in AGENT_REQUIRED:
            if key not in raw:
                raise ManifestError("%s: missing required key %r" % (where, key))
        if not isinstance(raw["id"], str) or not ID_RE.match(raw["id"]):
            raise ManifestError("%s: id must be lowercase letters, digits and hyphens" % where)
        if raw["id"] in seen:
            raise ManifestError("crew.json: duplicate agent id %r" % raw["id"])
        seen.add(raw["id"])
        if raw["autonomy"] not in AUTONOMY:
            raise ManifestError("%s: autonomy %r is not A, B or C" % (where, raw["autonomy"]))
        folder = _inside(root, raw["folder"], where + ": folder")
        controls = raw.get("controls", [])
        if not isinstance(controls, list) or any(c not in CONTROLS for c in controls):
            raise ManifestError("%s: controls must be a subset of %s" % (where, ", ".join(CONTROLS)))
        wakes = raw.get("wakes", [])
        if not isinstance(wakes, list) or any(not isinstance(w, str) for w in wakes):
            raise ManifestError("%s: wakes must be a list of strings" % where)
        actions = raw.get("actions", [])
        if not isinstance(actions, list):
            raise ManifestError("%s: actions must be a list" % where)
        for action in actions:
            if not isinstance(action, dict):
                raise ManifestError("%s: an action is not an object" % where)
            _reject_unknown(action, ACTION_KEYS, where + ": action")
            for key in ("name", "irreversible", "gate"):
                if key not in action:
                    raise ManifestError("%s: action is missing %r" % (where, key))
            if not isinstance(action["irreversible"], bool):
                raise ManifestError("%s: action %r: irreversible must be true or false"
                                    % (where, action["name"]))
            if action["gate"] not in ACTION_GATES:
                raise ManifestError("%s: action %r: gate %r is not one of %s"
                                    % (where, action["name"], action["gate"], ", ".join(ACTION_GATES)))
        agents.append({
            "id": raw["id"],
            "folder": folder,
            "lane": raw.get("lane", ""),
            "autonomy": raw["autonomy"],
            "wakes": list(wakes),
            "controls": list(controls),
            "actions": list(actions),
        })

    return {
        "root": root,
        "crew": man["crew"],
        "journal": _inside(root, man.get("journal", "decisions.jsonl"), "crew.json: journal"),
        "gates": _inside(root, man.get("gates", "gates.jsonl"), "crew.json: gates"),
        "handoffs": _inside(root, man.get("handoffs", "handoffs"), "crew.json: handoffs"),
        "agents": sorted(agents, key=lambda a: a["id"]),
    }


def _inside(root, relative, where):
    """Resolve a manifest path and refuse to leave the workspace."""
    if not isinstance(relative, str) or not relative:
        raise ManifestError("%s: must be a non-empty relative path" % where)
    if Path(relative).is_absolute():
        raise ManifestError("%s: must be relative, not %r" % (where, relative))
    base = Path(root).resolve()
    resolved = (base / relative).resolve()
    if base != resolved and base not in resolved.parents:
        raise ManifestError("%s: %r is outside the workspace" % (where, relative))
    return Path(root) / relative
