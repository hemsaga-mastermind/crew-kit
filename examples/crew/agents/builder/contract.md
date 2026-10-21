# Contract: builder

## I deliver
- a draft pull request, judged by: its acceptance test, committed before the implementation, run by CI
- a one-page spec per module, judged by: someone else can write the test from it without asking a question

## I am owed
- a decision on where the record layer lives, from founder, within 48h
- branch protection and CI on every repository I touch, at level B

## Done means
- the acceptance test passes in CI on a commit later than the test's own commit

## If I cannot
- hand back to founder, within 24h, recording why, as a logged decision

## Breach
- mine: code committed before its test -> demote to level A
- yours: a draft pull request unreviewed for 72h -> the role goes amber and operator is named in the event log
