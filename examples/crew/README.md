# A worked example

A two-agent crew, as the engine reads it. The example is deliberately not all green:

- `operator` is **amber**: everything the engine can check passes, and `rule_slips` is
  `unknown`, because no `slips.jsonl` is kept. Amber is the honest resting state of a crew
  that has not written down its own rule slips.
- `builder` is **red**: its `state.md` is nine days old and it sent no status this week.

Run it:

    python3 -I bin/crewkit health examples/crew --asof 2026-10-21
    python3 -I bin/crewkit lint examples/crew
    python3 -I bin/crewkit gates examples/crew
    python3 -I bin/crewkit verify examples/crew
