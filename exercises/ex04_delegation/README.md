# Exercise 4: Delegation: a coordinator and specialists

**Concept:** in Exercise 3 one agent did everything: every request carried every tool definition and
every search result so far. Here the **same task** is split by job. A **coordinator** talks to the user
and delegates; each **specialist** sees only its own tools and instructions:

```
                        ┌─ flights_agent       Kiwi (MCP, remote)
trip_coordinator ───────┼─ stays_agent         our trip server (MCP), only search_hotels
  convert_currency      ├─ weather_agent       our trip server (MCP), only get_weather_forecast
  add_to_trip, get_trip └─ destinations_agent  Skiplagged (MCP, remote)
```

The trip planning MCP server is the finished one from Exercise 3 (`common/trip_server.py`), so this exercise works
even if your Exercise 3 isn't complete.

Splitting is **not** automatically better: more agents means more model calls and information lost
between them. The question of this exercise is *when* it pays off.

## Run it
```bash
adk web --reload_agents exercises      # pick ex04_delegation
```

## Two ways to delegate (`mode` on the specialist)

| | `"chat"`: transfer (ADK's default) | `"single_turn"`: call and return |
|---|---|---|
| Analogy | Forwarding a customer's call to another department | Emailing a colleague a question and getting the answer back |
| After the specialist answers | **It** owns the conversation: the user's next message goes to it | The **coordinator** gets the result and stays in charge |
| What the specialist sees | The whole conversation | Only the request the coordinator sends it |
| Good for | Separate conversations per department (support desk: bookings, refunds, visas) | One plan assembled from several parts (our trip) |

(ADK has a third mode, `"task"`: the specialist chats with the user until its task is done, then hands
back control with `finish_task`. We don't use it here.)

## Steps

1. **Before you change anything**, ask *"Find me a flight from Cluj to Lisbon on 2026-11-20."*
   The coordinator has no team yet: what does it do?

2. **TODO 1 + 2: build the team.** Finish `weather_agent` (its description and its tool) and give
   the coordinator its four specialists. Start a **new session** and send these one by one:
   1. *"I have 1000 lei and I'm free from 2026-11-20 to 2026-11-22. Find me the cheapest return
      flight from Cluj to Lisbon."*
   2. *"Is there one that leaves later on Friday?"*
   3. *"What will the weather be like in Lisbon that weekend?"*
   4. *"Find me a cheap hostel there for the 2 nights."*
   5. *"Add the cheapest flight and that hostel to my trip. How much of my budget is left?"*

   In the trace, follow `transfer_to_agent`. **Who** answers message 2? Who passes control to whom at
   messages 3, 4 and 5? Why does message 5 have to go back to the coordinator?

3. **TODO 3: call and return.** Set `MODE = "single_turn"`, start a new session, and send the same
   five messages. Now the specialists appear as **tool calls** of the coordinator. Click one: what
   request did the coordinator write for it? What does the specialist *not* know about the
   conversation? (Hint: message 2.)

4. **Compare.** Click a `weather_agent` model call in each run (Request tab): how long is its input?
   For a full token table per agent, run the conversation from the terminal:
   ```bash
   python scripts/smoke_test.py exercises/ex04_delegation "message 1" "message 2" ...
   ```

5. **Bonus:** *"I don't know where to go. Any cheap ideas for 2026-11-20 to 2026-11-22?"*

## Tips: When to split
| Split into specialists when... | Keep one agent when... |
|---|---|
| One agent has too many tools or instructions, and starts choosing badly | A handful of tools is enough |
| Some steps produce large results that the rest of the conversation doesn't need | Every step needs the full context |
| Parts need different models, permissions or owners | Latency and cost matter more than structure |

**Same idea in a coding agent:** *subagents* work like `single_turn`. The main agent sends
a task ("find where X is used"), the subagent reads 50 files in its own context, and only its short
report comes back. Transfer is rare in coding agents, where one conversation stays with the user: it's
the support-desk pattern.

## Takeaways
- Delegation is a **context-management** tool: a specialist works in its own context and returns
  only what matters.
- `description` is what the coordinator routes on, just like a tool's docstring.
- Transfer hands over the **conversation**; `single_turn` hands over a **task**. Choose by who should
  own the conversation.
- More agents is not free: more calls, more latency, and information possibly lost at every handoff.
