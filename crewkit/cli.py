"""crewkit - the Crew Kit engine. Read-only, deterministic, no dependencies.

Usage:
  crewkit <health|lint|gates|verify> [workspace] [--asof YYYY-MM-DD] [--json] [--strict]

Exit codes: 0 no fail, 1 at least one fail (or any unknown with --strict),
2 the engine could not run.
"""
import datetime
import json
import sys

from crewkit import FAIL, UNKNOWN, VERSION
from crewkit import gates as gates_cmd
from crewkit import health as health_cmd
from crewkit import journal as verify_cmd
from crewkit import lint as lint_cmd
from crewkit.records import ManifestError, load_manifest

COMMANDS = {
    "health": health_cmd,
    "lint": lint_cmd,
    "gates": gates_cmd,
    "verify": verify_cmd,
}


def _verdicts(result):
    out = []
    for agent in result.get("agents", []):
        out += [c["verdict"] for c in agent["checks"]]
    for row in result.get("gates", []):
        out += [c["verdict"] for c in row["checks"].values()]
    for c in result.get("checks", {}).values():
        out.append(c["verdict"])
    if result.get("findings"):
        out.append(FAIL)
    if result.get("errors"):
        out.append(FAIL)
    return out


def _parse(argv):
    command, workspace, asof, as_json, strict = None, ".", None, False, False
    rest = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--json":
            as_json = True
        elif arg == "--strict":
            strict = True
        elif arg == "--asof":
            i += 1
            if i >= len(argv):
                raise ValueError("--asof needs a date")
            asof = argv[i]
        elif arg in ("-h", "--help"):
            raise ValueError("help")
        elif arg.startswith("-"):
            raise ValueError("unknown option %r" % arg)
        else:
            rest.append(arg)
        i += 1
    if not rest:
        raise ValueError("no command")
    command = rest[0]
    if command not in COMMANDS:
        raise ValueError("unknown command %r (want %s)" % (command, ", ".join(sorted(COMMANDS))))
    if len(rest) > 2:
        raise ValueError("too many arguments")
    if len(rest) == 2:
        workspace = rest[1]
    if asof is None:
        asof = datetime.date.today().isoformat()
    try:
        asof_date = datetime.date(int(asof[0:4]), int(asof[5:7]), int(asof[8:10]))
        if not len(asof) == 10 or asof_date.isoformat() != asof:
            raise ValueError
    except (ValueError, IndexError):
        raise ValueError("--asof %r is not a real YYYY-MM-DD date" % asof)
    return command, workspace, asof_date, as_json, strict


def main(argv):
    try:
        command, workspace, asof, as_json, strict = _parse(argv)
    except ValueError as exc:
        if str(exc) == "help":
            print(__doc__.strip())
            return 2
        print("crewkit: %s" % exc, file=sys.stderr)
        print(__doc__.strip(), file=sys.stderr)
        return 2
    try:
        manifest = load_manifest(workspace)
    except ManifestError as exc:
        payload = {"crew_kit": VERSION, "command": command, "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True) if as_json
              else "crewkit: %s" % exc)
        return 2
    result = COMMANDS[command].run(manifest, asof)
    print(json.dumps(result, indent=2, sort_keys=True) if as_json
          else COMMANDS[command].text(result))
    verdicts = _verdicts(result)
    if FAIL in verdicts:
        return 1
    if strict and UNKNOWN in verdicts:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
