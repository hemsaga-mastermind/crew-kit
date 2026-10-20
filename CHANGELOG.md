# Changelog

## v0.3 (draft, 21 Oct 2026)
The rulebook grows a backbone: a record layer the crew's files actually conform to, and an engine that reads them.
- `SPEC-0.3.md`: the record layer (manifest, header block, backlog, status, handoff, contract, nodes, gates,
  journal) and four commands. Three verdicts only; `unknown` is never folded into `pass` or `fail`.
- `bin/crewkit`: `health` (doc 01 fix 4), `lint` (L01-L14), `gates` (pre-registration as a date comparison),
  `verify` (the v0.1 schema plus a hash chain; an unchained journal is `unknown`, not `pass`).
- `templates/contract.md`: the mutual contract. A contract that names no oracle is invalid and its role may not act
  autonomously under it.
- `templates/nodes.json`: capability profiles. Work declares what it needs, nodes declare what they have, a program
  matches them, and a permission is a grant rather than a self-description. One node stays the default.
- `examples/crew`: a worked crew that is amber and red, because a green example would teach the wrong lesson.
- Read-only, deterministic, standard library only, verified on Python 3.9 and 3.13.

## v0.2 (draft, 17 Oct 2026)
Learned from running a second internal product, one with strict controls on real-world actions, on the method for a week.
- `07-what-broke`: rows 13-16 (automation undid a safety stop; a redeploy that kept the old version; code before tests; old jobs nobody switched off).
- `02-protocol`: rule 11 tests before code; rule 12 enforce levels in code.
- `05-gates-and-autonomy`: a table of technical controls and proofs for level-C actions.
- `04-handoffs`: keep every handoff as a file; take other agents' output through validated, sealed, scored cards.
- `08-checking-agent-output`: pre-register before you look; seal forecasts, then score them.
- `templates/card.json`: the untrusted-input card.

## v0.1 (16 Oct 2026)
First public release.
