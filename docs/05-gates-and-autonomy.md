# Gates and autonomy

## Idea-to-product gates
Every idea passes the same gates. Most stop early, on purpose.

| Gate | Question | Typical evidence |
| --- | --- | --- |
| G0: Brief | Is the problem real and worth a test? | One-page brief: problem, what exists, cheapest test, kill line |
| G1: Demand | Will someone use or pay for it? | Conversations with buyers, and a paid pilot or letter of intent |
| G2: Product | Does it work repeatedly at small scale? | Real users, error rate measured, costs known |
| G3: Scale | Does it pay for itself? | Revenue covers cost with margin |

**Kill lines are written before the test starts.** A kill line written after the result has been seen does not
count. Killing a product is a normal outcome and is logged like any other decision.

## Autonomy levels
| Level | Who acts | Examples |
| --- | --- | --- |
| A | Agent alone | Research, drafts, internal files, tests, records |
| B | Agent alone, behind machinery | Merges and deploys, once branch protection, CI gates, monitoring, rollback, a kill switch and budgets exist |
| C | Founder's signature only | Real money; spending and subscriptions; anything sent or signed as the founder; legal and identity; secrets and accounts; public launch of a new product; changes to the autonomy model itself |

Level B is earned per system, not declared. Until the machinery exists, the action stays at level C.
