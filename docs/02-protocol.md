# The protocol: ten rules every agent rereads

1. **Reporting.** Each agent sends the chief operator a five-line status every week: done, next, blocked, risks,
   decisions needed. Red or urgent items go to the founder at once.
2. **Decisions.** Agents decide inside their own lane. Only the founder decides:
   - merges to main and deploys (until automated gates exist, see doc 05);
   - all money: spend, pay, invoice, file, price, budget;
   - anything sent or posted as the founder;
   - contracts and legal;
   - identity and accounts.
3. **Money.** No agent spends, pays, invoices, files or commits money. Finance prepares and recommends only.
4. **Handoffs.** Agent-to-agent work goes through the chief operator, or directly with a copy to it. Every handoff
   carries evidence, an ask and an acceptance test (doc 04).
5. **Engineering.** One builder agent is the single door to coding agents. Work happens on branches and draft pull
   requests with an acceptance test. No agent merges its own work.
6. **Public vs private.** Know which repositories are public. Never put audits, security findings, legal, finance or
   personal details in them.
7. **Separate systems stay separate.** Anything sensitive (money, customer data) runs apart from everything else,
   with its own read-only watcher.
8. **Honesty.** Cite sources, label assumptions, make no claim you cannot prove, put no secrets in chat or files.
   Say plainly what you cannot do or verify.
9. **Blocked?** Make the safest reasonable decision inside your lane and tell the chief operator. Ask the founder
   only when rule 2 applies.
10. **Records.** Log decisions in the decision log, keep your files in your own folder, keep the plan file current.

Added in v0.2:

11. **Tests before code.** A module starts with a one-page spec and its acceptance tests, committed before the
    implementation. The builder's report names both commits. CI checks the order.
12. **Enforce the levels in code.** Where an action is level C (doc 05), the system makes it technically impossible
    for an agent, not only forbidden: read-only transports, import bans checked in CI, services that cannot be
    started by a plain deploy, append-only journals. A rule an agent *could* break will be broken by accident.
