# Trainer demo script: showing the finished result of each exercise

Prompts to send live, on the **finished** agents, to show students where each exercise ends up.
(For checking every TODO step by step, see [TESTING.md](TESTING.md).)

```bash
adk web --reload_agents solutions      # http://localhost:8000, pick the exercise top-left
```

- Each **scene** is one session: click **New session** before it, and send its messages in order.
- `>` lines are the prompts. Where there are several options, choose one; they show the same thing.
- **Point at** tells you what to open in the UI while the answer is on screen.
- Dates: **2026-11-20 → 2026-11-22** (Fri → Sun). Weather only works up to ~16 days ahead, and
  ex06 rejects past dates: shift all dates together if the workshop is later.
- Optional: open a second tab with `adk web exercises` (port: `--port 8001`) to show the
  "before" next to the "after".

---

## Ex01: chat agent (the model is a replaceable part)

**Scene 1: the instruction shapes the behavior**
> Hi! What can you help me with?

> Explain recursion in two sentences, with a tiny example.

**Point at:** the short answer and the Python example, as the instruction asks. Then Events → a
model call → Request: the system instruction, plus the line ADK adds from `name` and `description`.

**Scene 2: the limits of a model alone**
> What is today's date?

> What's the weather in Cluj-Napoca right now?

> What is the latest version of the `google-adk` Python package?

**Point at:** it says it can't know (the instruction tells it not to guess). Ask the class: *why*
can't it know? No clock, no internet, only training data. This is the hook for Exercise 2.

**Scene 3: swap the model (optional)**
Change `MODEL_PROVIDER` in `.env` (e.g. `gemini` or `ollama`), restart `adk web`, repeat Scene 1.
**Point at:** same code, different model: different style, speed and quality.

---

## Ex02: tools and the agent loop

**Scene 1: the loop, step by step**
> Plan a weekend in Lisbon or Barcelona from Cluj, 2026-11-20 to 2026-11-22, under 1500 lei, and preferably where it won't rain. Compare both.

**Point at:**
- The `Thinking:` lines, each followed by a tool call and its result: think → act → observe.
- `convert_currency` with `RON` (the budget converted first, as the instruction says).
- Live weather for both cities; demo flights and hotels.
- Count the model calls in the Events tab.

**Continue in the same session: state**
> Let's go with Lisbon. Add the cheapest flights there and back and the cheapest hostel to my trip.

> How much of my budget is left?

**Point at:** the **State** tab (`trip` with 3 items, `trip_total_eur`, e.g. 241), and in the next
Request the instruction line `Current trip total: 241 EUR`.

> What's in my trip so far?

**Point at:** `get_trip` reads the state: the trip didn't have to be remembered by the model.

**Scene 2: errors are observations**
> Flights from Cluj to Lisbon on 20 November

> What's the weather in Lisbon next March?

**Point at:** the tool returns `"status": "error"` (bad airport/date format, or forecast out of
range). The model reads the message and fixes its call, or explains the problem. No crash.

---

## Ex03: MCP servers and skills

**Scene 1: the whole thing, in 4 messages** (the main demo)

1. Discover (find-destination skill + Skiplagged + currency):
   > I'm free from 2026-11-20 to 2026-11-22 and I have 1000 lei. I don't know where to go, any cheap ideas from Cluj?

   Alternatives:
   > Where could I fly cheaply from Cluj next weekend? I have about 200 euros.

   > Surprise me: somewhere warm and cheap for 2026-11-20 to 2026-11-22, leaving from Cluj.

   **Point at:** the first request has **no** Skiplagged tools, only the skill names in the
   instruction. Then `load_skill("find-destination")` → `sk_destinations_anywhere` appears in the
   **next** request's tool list. The answer: 5 destinations, "prices are approximate".

2. Plan (Kiwi + trimming + our own MCP server):
   > Let's go to Lisbon. Find me the cheapest return flight, a cheap hostel for the 2 nights, and the weather on Saturday.

   Pick a city with demo hotels: Lisbon, Barcelona, Rome, Milan, Vienna, Paris or Athens.
   **Point at:** `search-flight` with `20/11/2026` (Kiwi's own date format, from its tool
   description); its result is **small** (the `after_tool_callback` trimmed ~25k tokens to ~300).
   `search_hotels` and `get_weather_forecast` come from `trip_server.py` over stdio: same tools as
   ex02, now behind MCP.

3. Choose (session state):
   > Add the cheapest flight and that hostel to my trip. How much of my budget is left?

   **Point at:** State tab.

4. The final result (trip-plan-format skill):
   > I'm done, give me the final plan.

   Alternatives:
   > Looks good. Write up the final plan for me.

   > Summarize my trip so I can send it to my friends.

   **Point at:** `load_skill("trip-plan-format")` (it unlocks no tool, it only brings a template),
   `get_trip`, and the answer in the exact template: title, table with booking link, budget line,
   weather → packing, "Before you go" checklist.

**Scene 2: the cost of tools** (short, optional)
> Hi

**Point at:** Request → the tool list and the token count: only Kiwi, our server, the trip tools
and `load_skill`. Do the same in the `exercises` tab (before TODO 3): Skiplagged's 10 tools are in
every request, ~14.7k tokens vs ~7.4k.

**Scene 3: a skill is just text** (optional, live edit)
Edit `solutions/ex03_mcp/skills/trip-plan-format/SKILL.md`, e.g. add *"Write the whole plan in
Romanian"* or *"If the chance of rain is above 50%, add a 'Rainy-day plan' section"*. New session,
repeat Scene 1 quickly (or just messages 2-4 with a known city), ask for the final plan again.
**Point at:** a different plan, no code changed. Revert the file afterwards.

---

## Ex04: delegation (coordinator + specialists, `single_turn`)

**Scene 1: the 5-message conversation**
> I have 1000 lei and I'm free from 2026-11-20 to 2026-11-22. Find me the cheapest return flight from Cluj to Lisbon.

> Is there one that leaves later on Friday?

> What will the weather be like in Lisbon that weekend?

> Find me a cheap hostel there for the 2 nights.

> Add the cheapest flight and that hostel to my trip. How much of my budget is left?

**Point at:**
- The specialists appear as **tool calls** of `trip_coordinator` (`flights_agent`,
  `weather_agent`, `stays_agent`). Click one: the **request the coordinator wrote** for it.
- A `weather_agent` model call: its input is tiny (~1.3k tokens), it sees only its own tool.
- Message 2: the coordinator must put the context ("Cluj → Lisbon, 2026-11-20") into the request,
  because the specialist doesn't see the conversation.
- Message 5: `convert_currency`, `add_to_trip` stay with the coordinator, which owns the trip.

**Scene 2: one request, several specialists**
> Plan me a weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22, with 1200 lei: the cheapest flights, a hostel and the weather.

**Point at:** the coordinator calls several specialists for one message, then combines their
answers. That is the orchestrator-workers pattern.

**Scene 3: the destinations specialist**
> I don't know where to go. Any cheap ideas for 2026-11-20 to 2026-11-22?

**Point at:** `destinations_agent` with Skiplagged: a 10-tool server is now the problem of one
specialist only, not of every request.

**Scene 4: transfer vs single_turn** (optional)
Set `MODE = "chat"` in `solutions/ex04_delegation/agent.py`, new session, repeat Scene 1.
**Point at:** `transfer_to_agent`; message 2 is answered by `flights_agent` directly (it now owns
the conversation); message 5 has to be transferred back to the coordinator. Set `MODE` back.

---

## Ex05: classic workflows (sequential, parallel, loop)

One message per session. Same request, four budgets:

| Budget | Prompt | Point at |
|---|---|---|
| 1200 lei | > Weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22. My budget is 1200 lei. | The main demo: see below |
| 3000 lei | > Weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22. My budget is 3000 lei. | Fits at once: the checker calls `exit_loop` after round 1 |
| 600 lei | > Weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22. My budget is 600 lei. | Never fits: stopped by `max_iterations=3`, the presenter says so |
| 1000 lei | > Weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22. My budget is 1000 lei. | The cheapest plan is €192 (~1030 lei). Does the LLM checker notice, or accept a wrong total? |

Phrasing variants for the parser (same result):
> I want to go from Cluj to Barcelona on Nov 20, back Nov 22, max 1200 RON.

> Barcelona trip 20-22 November 2026, flying from Cluj, budget 240 euros.

**Point at (1200 lei):**
- The State tab: `request` (a structured `TripRequest` from free text), then `plan`, `review`.
- The Trace tab: the three scouts run **at the same time** (`ParallelAgent`).
- The loop: the planner picks comfort, the checker says "over budget", the planner re-plans
  cheaper, the checker calls `exit_loop`.
- The fixed order: the user can't steer it mid-way, and nothing is skipped: compare the number
  of model calls with ex02's single agent for the same request.

---

## Ex06: graph workflow (code decides the routes)

**Scene 1: the routes**

| Path | Prompt | Point at |
|---|---|---|
| invalid → stop | > Weekend in Tokyo from Cluj, 2026-11-20 to 2026-11-22. | `validate_request` routes to `explain_problem`: "I can't plan this trip yet: ...". **1 LLM call** in total (only the parser) |
| invalid → stop | > Weekend in Barcelona from Cluj, 2026-10-01 to 2026-10-03, 1200 lei. | A past date, rejected by code |
| fits at once | > Weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22. My budget is 3000 lei. | `check_budget` → `fits` → presenter |
| over → re-plan → fits | > Weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22. My budget is 1200 lei. | The main demo: see below |
| give up | > Weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22. My budget is 600 lei. | After `MAX_ROUNDS` re-plans: "nothing fits" (€192 vs ~€112), said honestly |

**Point at (1200 lei):**
- The events authored by the function nodes: `validate_request` (airport codes and currency
  normalized: "lei" → RON), `check_budget` with its `route` and the `budget_check` state
  (the total **recomputed from real prices**, not taken from the LLM).
- The back-edge `over → planner`, then `fits → presenter`.
- The 1000-lei case from ex05 can't fool this checker: the arithmetic is code.

**Scene 2: same request, ex05 vs ex06** (optional)
Send the 1000-lei Barcelona message to both. ex05's LLM checker may accept a wrong total; ex06's
code checker can't. This is the closing argument: **let the LLM do the fuzzy parts, let code do
the rules.**

---

## If something goes wrong live
| Symptom | Quick fix |
|---|---|
| `429` / "Too Many Requests" | Wait a few seconds and resend (the model client retries 3 times by itself) |
| Kiwi or Skiplagged slow / timing out | Live public servers: retry once, otherwise move on and show a screenshot |
| Weather "out of allowed range" | The dates are more than ~16 days ahead: shift them |
| A change in `SKILL.md` or `agent.py` not visible | Start a **new session** (with `--reload_agents`), or restart `adk web` |
