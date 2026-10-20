# Crew Kit v0.3 — the record layer and the engine

**Status:** specification. Written before the implementation, as rule 11 requires.
**What changes in v0.3:** v0.1 and v0.2 are a rulebook a person reads. v0.3 adds a **record layer** —
a small set of strictly specified files — and an **engine** (`crewkit`) that reads those files and
returns a verdict. The rules that fail because someone *forgot* become checks. The rules that fail
because someone *disagreed* stay in the documents, where they belong.

Scope discipline: four commands, ever. `health`, `lint`, `gates`, `verify`. Each one implements a
rule already published in `docs/`. A fifth command needs a published rule and a failure it prevents.

---

## 1. Non-negotiables

These are properties of the engine, testable, and the reason to trust its output.

1. **Three verdicts only: `pass`, `fail`, `unknown`.** There is no fourth, and `unknown` is never
   folded into either of the others. A check that could not read what it needed returns `unknown`
   and says which path it could not read. *Missing coverage is unknown, not absence.*
2. **Deterministic.** Same input files and same `--asof` date produce byte-identical output. No wall
   clock inside the result, no dictionary ordering, no model in the path. Nothing here is judged by
   an LLM; a verdict is produced by comparing dates, sets and hashes.
3. **Read-only.** No command writes, moves or deletes a file in the workspace it inspects. The only
   output is on stdout.
4. **No dependencies.** Python 3.9 or newer, standard library only. A tool that reads files and
   compares dates does not need a package tree.
5. **No guessing at prose.** Every machine-read field lives in a header block or a line format
   defined in §2. If a field is not in that shape, the engine reports it as unparseable — it never
   infers the value from surrounding text.
6. **Every result carries its coverage.** Each command's output lists the paths it read and the
   paths it could not read.

## 2. The record layer

### 2.1 The header block

Several files start with a header block: a line containing exactly `---`, then one or more
`key: value` lines, then a line containing exactly `---`. It is **not** YAML; it is this and
nothing else.

- a key is lowercase ASCII letters and underscores;
- the separator is a colon followed by one space; the value is the rest of the line, stripped;
- a duplicate key is an error;
- a key outside the closed set for that file type is an error;
- a missing required key is an error;
- a date value is `YYYY-MM-DD` and nothing else.

An error in a header block never becomes a `fail`. It becomes `unknown`, naming the file and line.

### 2.2 `crew.json` — the manifest

One per workspace, at its root. The engine reads nothing it is not pointed at from here.

```json
{
  "crew_kit": "0.3",
  "crew": "crewless",
  "journal": "records/decisions.jsonl",
  "gates": "records/gates.jsonl",
  "handoffs": "handoffs",
  "agents": [
    {
      "id": "operator",
      "folder": "agents/operator",
      "autonomy": "A",
      "wakes": ["cron: daily 07:00 reread-and-report"],
      "controls": [],
      "actions": [{"name": "weekly status", "irreversible": false, "gate": "none"}]
    }
  ]
}
```

Required: `crew_kit`, `crew`, `agents`. Optional: `journal`, `gates`, `handoffs` (default
`handoffs`). Per agent, required: `id`, `folder`, `autonomy`. Optional: `wakes`, `controls`,
`actions`, `lane`.

- `crew_kit` must be `"0.3"`.
- `id` is unique, lowercase ASCII letters, digits and hyphens.
- `autonomy` is `A`, `B` or `C` (doc 05).
- `controls` is a subset of `branch_protection`, `ci_gates`, `monitoring`, `rollback`,
  `kill_switch`, `budgets` — the six doc 05 requires for level B.
- an action has `name`, `irreversible` (boolean) and `gate` (`none`, `automated` or `founder`).
- an unknown key anywhere in the manifest is an error, and a manifest error is fatal: the engine
  exits 2 and reports nothing else. A manifest you cannot trust makes every verdict below it
  meaningless.

### 2.3 `state.md`

Header keys — required: `agent`, `status` (`green`/`amber`/`red`), `updated` (date).
Optional: `lane`, `autonomy`, `waiting_on`. Prose follows the block and is not read.

### 2.4 `backlog.md`

Only lines beginning `- [ ] ` or `- [x] ` are read. Fields are separated by ` | `.

```
- [ ] 12 | owner: builder | due: 2026-10-30 | Ship the gates command
- [x] 11 | owner: builder | due: 2026-10-18 | done: 2026-10-17 | Spec the record layer
```

Required on an open item: an integer id, `owner:`, `due:`. A done item also carries `done:`. The
text is the last field. A checkbox line that does not parse is unparseable — it is not ignored, and
it makes `backlog_overdue` `unknown` for that agent.

### 2.5 `status/YYYY-MM-DD.md`

One file per status, inside the agent's folder, named by its date. Required lines, in any order,
one each: `Done:`, `Next:`, `Blocked:`, `Risks:`, `Decisions needed:`. A file missing a line is
unparseable and does not count as a status sent.

### 2.6 `handoffs/*.md`

Header keys — required: `from`, `to`, `sent` (date), `ask`, `acceptance_test`.
Optional: `answered` (date), `cc`, `founder_needed`.

### 2.7 `gates.jsonl`

One JSON object per line, one per product and gate (doc 05).

```json
{"product": "example", "gate": "G1", "kill_line": "fewer than 3 people use it within 60 days of publishing", "kill_line_written": "2026-01-05", "test_started": "2026-01-12", "status": "open"}
```

Required: `product`, `gate` (`G0`–`G3`), `kill_line`, `kill_line_written`, `status`
(`open`/`passed`/`killed`). Optional: `test_started`, `decided`.

### 2.8 `decisions.jsonl`

As v0.1 (`tools/check_decisions.py` defines the schema and stays the reference). v0.3 adds optional
hash chaining: a record may carry `prev` (the previous record's `hash`, or `null` for the first) and
`hash` (see §3.4).

## 3. The commands

All four take a workspace path (default `.`) and print a text table, or JSON with `--json`.
`--asof YYYY-MM-DD` sets the date the checks are evaluated against; it defaults to today, which is
the only non-determinism in the engine and is always echoed in the output.

Exit codes: `0` no `fail`; `1` at least one `fail`; `2` the engine could not run (bad manifest,
missing workspace, bad arguments). With `--strict`, `unknown` also exits `1`.

### 3.1 `crewkit health` — doc 01, fix 4

The weekly health check, mechanised, because it is the fix most often skipped. Per agent, window
7 days ending at `--asof`:

| Check | `pass` when | `unknown` when |
| --- | --- | --- |
| `state_fresh` | `state.md` `updated` is within the window and not in the future | file missing or header unparseable |
| `status_sent` | a parseable `status/<date>.md` falls inside the window | the folder is unreadable |
| `backlog_overdue` | no open item is due more than 7 days before `asof` | file missing, or any checkbox line unparseable |
| `handoff_answered` | no handoff addressed to this agent, sent on or before `asof - 2`, lacks `answered` | the handoffs folder is unreadable, or a handoff header is unparseable |
| `rule_slips` | — | always, unless `slips.jsonl` exists in the agent's folder |

`rule_slips` is `unknown` by default on purpose. The engine cannot see whether an agent spent money
or posted as the founder; reporting that as green would be the one lie that discredits the rest.

Agent colour: `red` if any check is `fail`; `amber` if none fails and any is `unknown`; `green`
only when all five pass. Doc 01's "two reds in a row" needs history the engine does not keep in
v0.3; it is not implemented and the output does not pretend otherwise.

### 3.2 `crewkit lint` — doc 01 fix 2, doc 04, doc 05

Structure only. It runs nothing and judges no content.

| Code | Finding |
| --- | --- |
| `L01` | no `state.md` |
| `L02` | no `backlog.md` |
| `L03` | no `charter.md` (doc 03) |
| `L04` | a checkbox line that does not parse |
| `L05` | an open backlog item with no owner or no due date |
| `L06` | a handoff whose `to` is not an agent in the manifest — a lane nothing wakes |
| `L07` | autonomy `B` without all six doc 05 controls, named individually |
| `L08` | an irreversible action whose gate is `none` |
| `L09` | an agent with no `wakes` — doc 01's "idle with a full backlog" |

Every finding is a `fail` with a path. `lint` has no `unknown`: either the structure is there or it
is not. Findings are sorted by agent id, then code.

### 3.3 `crewkit gates` — doc 05

Per line of `gates.jsonl`:

| Check | `pass` when | `fail` when | `unknown` when |
| --- | --- | --- | --- |
| `kill_line_present` | `kill_line` is non-empty | it is empty | — |
| `pre_registered` | `kill_line_written` <= `test_started` | it is later | no `test_started` (the test has not begun) |

`pre_registered` is the point of the command: *"a kill line written after the result has been seen
does not count"* becomes a date comparison, which is the hardest rule in the kit to fudge once a
machine checks it.

### 3.4 `crewkit verify` — doc 05, append-only journals

Runs the v0.1 schema check over `decisions.jsonl`, then the chain:

- `hash` is the SHA-256, hex, of the record's canonical JSON — every key except `hash`, sorted,
  UTF-8, no whitespace between tokens, as `json.dumps(obj, sort_keys=True, separators=(",", ":"),
  ensure_ascii=False)`;
- `prev` equals the previous record's `hash`, and `null` on the first record.

If no record carries `hash`, the chain check is `unknown` ("journal is not chained"), not `pass`.
An unchained journal is append-only by convention only, and the engine says so. If any record
carries `hash`, every record must, and a break is a `fail` naming the first broken line.

## 4. What v0.3 deliberately does not do

- It does not write, fix or scaffold anything.
- It does not read a repository's code, so it cannot tell you an import ban is in place. Doc 05's
  technical controls are declared in the manifest and checked for completeness, not proven.
- It keeps no history, so trends ("two reds in a row") are out.
- It makes no network call, and nothing is uploaded. Running it tells us nothing about you.
