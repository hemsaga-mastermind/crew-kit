<img src="docs/assets/crewless-logo.svg" width="48" height="48" alt="Crewless">

# Crew Kit

**Run a small organisation on AI agents, with a person signing off what matters, and receipts for everything.**

Crew Kit is the operating method Crewless uses to run one founder with a crew of AI agents. It contains:
- the rules every agent follows;
- the files that keep agents on track across days;
- the gates an idea passes before it becomes a product;
- the autonomy levels that say what agents may do alone;
- an honest list of what broke while we learned this.

It is not a framework or a library. It is a set of plain Markdown files, a strictly specified record layer, and a
small read-only engine that checks the records against the rules. It works with any agent tool that can read and
write files: Claude Code, Cursor, scheduled routines, chat bots.

**v0.3 adds the engine.** The rules that fail because someone *forgot* are now checks; the rules that fail because
someone *disagreed* stay in the documents, where they belong. The engine has three verdicts — `pass`, `fail` and
`unknown` — and it never folds `unknown` into either of the others.

## Start here
1. Read [docs/01-why-agents-go-idle.md](docs/01-why-agents-go-idle.md): the failure analysis everything else rests on.
2. Read [docs/02-protocol.md](docs/02-protocol.md): ten rules, one page.
3. Copy `templates/` into a folder per agent: `charter.md`, `state.md`, `backlog.md`.
4. Start a decision log (`templates/decisions.jsonl`) and check it with `python3 -I tools/check_decisions.py`.
5. Read [docs/07-what-broke.md](docs/07-what-broke.md) before you scale past three agents.
6. Read [SPEC-0.3.md](SPEC-0.3.md), copy `examples/crew/crew.json`, and run the engine.
   **The example crew is deliberately amber and red**, so `health` exits 1 and prints
   failing rows on your first run — a green example would teach you that green is the
   normal state, which is the thing this kit exists to argue with:

```
python3 -I bin/crewkit health examples/crew --asof 2026-10-21
python3 -I bin/crewkit lint   examples/crew
python3 -I bin/crewkit gates  examples/crew
python3 -I bin/crewkit verify examples/crew
```

Python 3.9 or newer, standard library only, read-only, no network call. Nothing is uploaded, so running it tells
us nothing about you.

## Contents
| File | What it gives you |
| --- | --- |
| [01 Why agents go idle](docs/01-why-agents-go-idle.md) | Why agents stall or forget, and the four fixes |
| [02 Protocol](docs/02-protocol.md) | The ten rules every agent rereads |
| [03 Roles and packs](docs/03-roles-and-packs.md) | A chief operator plus small packs of agents |
| [04 Handoffs](docs/04-handoffs.md) | How work moves between agents without getting lost |
| [05 Gates and autonomy](docs/05-gates-and-autonomy.md) | Idea-to-product gates; what agents may do alone |
| [06 Cost hygiene](docs/06-cost-hygiene.md) | Keeping token and agent spend sane |
| [07 What broke](docs/07-what-broke.md) | Real failures and the fix for each |
| [08 Checking agent output](docs/08-checking-agent-output.md) | Catching confident, wrong answers |
| [SPEC-0.3.md](SPEC-0.3.md) | The record layer and the engine: formats, checks, exit codes |
| `templates/` | Charter, state, backlog, handoff, status, decision log, card (v0.2), contract and nodes (v0.3) |
| `examples/crew/` | A worked two-agent crew, deliberately amber and red rather than green |
| `bin/crewkit` | The engine: `health`, `lint`, `gates`, `verify` |
| `tools/check_decisions.py` | Validates the decision log (no dependencies) |

## The engine, in one table
| Command | What it checks | The rule it stops being a wish |
| --- | --- | --- |
| `health` | state freshness, the weekly status, overdue backlog, unanswered handoffs, rule slips | doc 01, fix 4 — the weekly health check nobody remembers |
| `lint` | missing files, ownerless backlog items, handoffs to lanes nothing wakes, level B claimed without its six controls, irreversible actions with no gate, agents nothing wakes, contracts with no oracle, needs no node can satisfy | docs 01, 03, 04, 05 |
| `gates` | a kill line was written before the test started | doc 05 — "a kill line written after the result has been seen does not count" |
| `verify` | the decision log's schema, and its hash chain | rule 12 — append-only in fact, not by convention |

## Status
v0.3 (draft). Used daily to run Crewless. v0.3 adds the record layer, the engine, the mutual contract with its
oracle rule, and capability-based placement for a crew spread over more than one machine. Issues and pull requests
are welcome.

## Licence
- Docs and templates: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Code: MIT (see LICENSE); docs licence in LICENSE-docs.

Made by Crewless.
