# Handoffs

Work between agents moves in one format, every time:

```
HANDOFF  from: <agent>  to: <agent>  cc: chief operator  date: <date>
Evidence: what I found, with links or files (no evidence, no handoff).
Ask: exactly what I need, and by when.
Acceptance test: how we both know it is done (file exists, check passes, table has columns X/Y/Z).
Founder needed? yes/no (if yes, which rule-2 item).
```

- The sender writes the handoff into the receiver's `backlog.md` **and** messages it. A missed message is still
  caught on the receiver's next turn.
- The receiver replies within one working day: accepted, need more evidence, or not my lane.
- **Coding work:** goes to the builder. The builder turns it into a plan task (goal, files, acceptance test) and
  assigns a coding agent on a branch. The tester checks the pull request against the acceptance test. The guardian
  reviews anything touching security, secrets, money or a public repository.
