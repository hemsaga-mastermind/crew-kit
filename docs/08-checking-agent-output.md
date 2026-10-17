# Checking agent output

The most expensive agent failure is not a crash. It is a confident, wrong answer that nothing flags. This page is
about catching that.

## Why it happens
Agents rarely fail loudly. A tool call returns the wrong record, a search misses the key page, a summary drops a
condition, and the final answer still reads well.

Long chains make it worse: errors compound. If each step is right 90% of the time, a 20-step task is right end to end
only about 12% of the time (0.9^20 ≈ 0.12). Fewer steps, or a check between steps, matter more than a better prompt.

## What to do
1. **Keep a known-answer set.** Collect a fixed set of inputs whose right answers are decided in advance, before
   anyone sees the agent's output. Rerun it on every change to prompts, tools or models. A change that lowers the
   score does not ship.
2. **Use pass/fail checks, not scores.** "Did it cite the source page: yes/no" is more consistent across runs than
   "rate the answer 1–10". Write each check so two people would mark it the same way.
3. **Reward "I don't know".** If an agent is punished for abstaining, it learns to guess. Make "cannot check" a
   valid, counted outcome, and track how often it is used.
4. **Check the path, not only the answer.** Record which tools were called with which inputs. A right answer reached
   through the wrong record is luck; it will fail next time.
5. **Two checkers on anything that decides an outcome.** A second, independent check (another scorer, another model,
   or a person) on results that trigger money, publishing or a verdict. See doc 07, row 8.
6. **"Reported" is not "confirmed".** An agent's claim stays "reported" until its evidence has been opened and a
   person, or a second check, confirms it. See doc 07, row 6.
7. **Cap the steps.** Break long tasks into short ones, each with its own acceptance test (doc 04), so an error is
   caught where it happens instead of twenty steps later.

8. **Pre-register before you look (v0.2).** For any study whose result could change a decision, write the question,
   the data, the exact variants and the pass line to a file and commit it *before* running anything. Judge on data
   the rules never saw. Correct for the number of variants you tried. Never edit the registration afterwards; put
   deviations in a separate section of the results. A negative result is a finding, filed with the same care.
9. **Seal forecasts, then score them (v0.2).** Anything that claims to know the future is written to an append-only
   journal with a hash and a timestamp before the outcome, and scored against naive baselines afterwards. Trust,
   and any authority over money, grows only with the scored record.

## What this does not do
These checks find the failures you thought to test for. They do not prove an agent is correct in general. Add every
real failure you find to the known-answer set, so it cannot happen twice unnoticed.
