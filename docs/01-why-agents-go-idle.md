# Why agents lose context or go idle, and the fixes

This is the most useful page in the kit, because it is a failure analysis. Every other file exists to fix
something described here.

## What actually happens
- **An agent only works when something wakes it.** It does not think in the background. If nobody messages it, no
  routine fires and no event arrives, it does nothing, even with a full to-do list.
- **Chat history gets summarised.** Long chats are squashed into short summaries. Dates, ticket numbers, who owes what
  and "we decided X" get lost or blurred. An agent that relies on chat memory slowly drifts.
- **Each turn starts close to fresh.** The agent sees its instructions, the summarised chat and whatever it chooses
  to read. If the truth is not in a file, it is effectively not there.
- **Handoffs fall between chairs.** Agent A "sends" work to agent B, but B is never woken, so the work sits.

## The fixes (all four, not one)
1. **Per-agent `state.md` and `backlog.md`, reread every turn.**
   - `state.md`: who I am, my lane, status (green/amber/red), what is in flight, what I am waiting for and from
     whom, last updated. Under about 40 lines.
   - `backlog.md`: numbered items, each with an owner and a due date. Done items move to a dated "done" line; they
     are not deleted.
   - The first action of every turn is to read both; the last is to update both. Chat can be summarised away;
     files cannot.
2. **Scheduled routines.** Every agent gets at least one routine, daily or weekly, whose saved instruction is:
   reread the files, do the next item, update the files, send the chief operator a five-line status. This is what
   stops "idle with a full backlog".
3. **Event-driven wake-ups.** Some things should not wait for the schedule: a message in the agent's inbox, a pull
   request or failing check, a deadline at T-24h, a handoff addressed to it. Use event triggers where the platform
   has them; otherwise the chief operator's daily sweep catches them.
4. **Weekly health check.** Once a week the chief operator checks each agent:
   - Was `state.md` updated in the last 7 days?
   - Did it send a status this week?
   - Is any backlog item more than 7 days overdue?
   - Is any handoff unanswered after 48 hours?
   - Did any rule slip (money, public repository, something sent or posted)?

   The result is one table, green/amber/red per agent. Two reds in a row lead to a proposal: fix, pause or retire.
