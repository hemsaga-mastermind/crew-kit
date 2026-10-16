# What broke

Real failures from running one company on agents, and what we changed. Kept honest on purpose: this is the part
other teams can use.

| # | What broke | Why | What we changed |
| --- | --- | --- | --- |
| 1 | Agents sat idle with full backlogs | Nothing woke them | Routines plus event wake-ups plus a weekly health check (doc 01) |
| 2 | Decisions were "forgotten" | Chat history was summarised | Decision log in a file, validated on every change |
| 3 | Work handed over was never done | The receiver was never woken | Handoff written into the receiver's backlog as well as messaged |
| 4 | An agent committed its state file to git every few minutes | Status churn treated as history | State lives in plain files; commit on meaningful change only |
| 5 | Unrelated jobs ran on the same server as a sensitive system | Convenience | One system per host; sensitive systems run alone |
| 6 | Agents reported results a person could not reproduce | Claims without links | Every claim carries evidence; status "reported" until a person confirms it |
| 7 | A banned phrase reached a public demo | Wording rules lived in a document, not a check | Wording rules enforced by an automated check |
| 8 | A scoring bug silently changed results | One scorer, no cross-check | A second, independent scorer on anything that decides an outcome |
| 9 | A health check kept failing on a part switched off on purpose | Monitoring did not know intent | Intentionally-off parts are declared; checks skip them and say so |
| 10 | Login details and data exports landed in shared folders | Agents saved what they used | Rule 8 plus a scanner; secrets only in a secret store |
| 11 | Plans multiplied | Every agent wrote its own plan | One plan; old ones marked "superseded" with a pointer |
| 12 | Tools ran on accounts the company did not own | Quick start | Company-owned accounts from day one; accounts are level C |

If you hit a failure that is not here, open an issue. Failures are the most valuable contribution.
