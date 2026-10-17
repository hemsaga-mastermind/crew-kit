# Crew Kit

**Run a small organisation on AI agents, with a person signing off what matters, and receipts for everything.**

Crew Kit is the operating method Crewless uses to run one founder with a crew of AI agents. It contains:
- the rules every agent follows;
- the files that keep agents on track across days;
- the gates an idea passes before it becomes a product;
- the autonomy levels that say what agents may do alone;
- an honest list of what broke while we learned this.

It is not a framework or a library. It is a set of plain Markdown files and one small validator. It works with any
agent tool that can read and write files: Claude Code, Cursor, scheduled routines, chat bots.

## Start here
1. Read [docs/01-why-agents-go-idle.md](docs/01-why-agents-go-idle.md): the failure analysis everything else rests on.
2. Read [docs/02-protocol.md](docs/02-protocol.md): ten rules, one page.
3. Copy `templates/` into a folder per agent: `charter.md`, `state.md`, `backlog.md`.
4. Start a decision log (`templates/decisions.jsonl`) and check it with `python3 -I tools/check_decisions.py`.
5. Read [docs/07-what-broke.md](docs/07-what-broke.md) before you scale past three agents.

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
| `templates/` | Charter, state, backlog, handoff, status, decision log, card (v0.2) |
| `tools/check_decisions.py` | Validates the decision log (no dependencies) |

## Status
v0.2 (draft). Used daily to run Crewless. v0.2 adds four failures (13-16), two rules (11-12), enforced autonomy levels, handoff files, untrusted cards, and pre-registration. Issues and pull requests are welcome.

## Licence
- Docs and templates: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Code: MIT (see LICENSE); docs licence in LICENSE-docs.

Made by Crewless.
