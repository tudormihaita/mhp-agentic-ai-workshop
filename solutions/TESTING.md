# Instructor dry run: testing every exercise

Run everything from the repo root with the venv active, and check the setup first:
`python scripts/check_setup.py`

## Two ways to run

**The finished versions**, i.e. the behaviour students should end up with:
```bash
adk web --reload_agents solutions
```
Open http://localhost:8000 and pick an exercise. Click **New session** before each scenario.

**The student versions, doing the TODOs yourself.** This is the real dry run. Work on a scratch
branch and throw it away afterwards:
```bash
git switch -c dry-run
adk web --reload_agents exercises
# do the TODOs; after saving, start a NEW session in the UI
git switch -   &&   git branch -D dry-run          # discard (git stash first to keep anything)
```

**Without the browser:** the same messages in the terminal, with every tool call and a token table
per agent:
```bash
python scripts/smoke_test.py solutions/ex04_delegation "message 1" "message 2" ...
python scripts/smoke_test.py --provider gemini solutions/ex02_tools "..."    # another provider
```

> **Dates:** the prompts use **2026-11-20 → 2026-11-22**. Weather forecasts cover only about 16 days
> ahead, and ex06 rejects dates in the past. Update the dates in the READMEs before the workshop.

## What to send, per exercise

### Ex01: chat (no tools)
| Send | Expect |
|---|---|
| Say hello; then the three questions from the README table (recursion, process vs thread, haiku) | Answers change after TODO 1 (the instruction) |
| *"What is today's date?"*, *"What's the weather in Cluj-Napoca right now?"* | It can't know: does it admit it, or make something up? |
| Change `MODEL_PROVIDER` / `*_MODEL` in `.env`, restart, ask the same questions | Same code, different model |

### Ex02: tools and the agent loop
| Step | Send | Expect |
|---|---|---|
| Before TODOs | *"Find me the cheapest flight from Cluj to Lisbon on 2026-11-20 and back on 2026-11-22."* | Two `search_flights` calls (one per direction), demo prices |
| TODO 1 | *"Will it rain in Lisbon this Saturday?"* then *"What's the weather in Lisbon next March?"* | Live forecast, then a real API error ("out of range") that the model explains |
| TODO 2 | Pick a flight and a hostel (*"Add the cheapest flight and the cheapest hostel"*) | `trip` and `trip_total_eur` in the **State** tab |
| TODO 3 | *"My budget is 1500 lei, how much is that in euros?"* | Before the fix: passes "lei" → error → retries with RON. After: one call |
| TODO 4 | *"Flights from Cluj to Lisbon on 20 November"* | Works out CLJ/LIS and the date format from the error message |
| TODO 5 | *"Plan a weekend in Lisbon or Barcelona from Cluj, 2026-11-20 to 2026-11-22, under 1500 lei, and preferably where it won't rain. Compare both."* | "Thinking:" lines before each tool call, and **more** model calls than without it |

### Ex03: MCP and skills
| Step | Send | Expect |
|---|---|---|
| Step 1 | *"Find the cheapest return flight from Cluj to Lisbon, 2026-11-20 to 2026-11-22."* | Live Kiwi prices + booking links; date format `20/11/2026`; a huge result (until TODO 4) |
| TODO 1-2 | *"Cheapest stay in Lisbon for 2 nights, and will it rain on Saturday?"* | `search_hotels` and `get_weather_forecast` now come from our MCP server |
| TODO 3 | *"I'm free 2026-11-20 to 2026-11-22 with 200 euros. Where could I go?"* | `load_skill("find-destination")`, then `sk_destinations_anywhere` appears in the next request's tool list |
| TODO 3 | Pick a place, add a flight and a stay, then *"I'm done, give me the final plan."* | `load_skill("trip-plan-format")` → `get_trip` → the exact template |
| TODO 4 | Repeat the step 1 message | A `search-flight` result of ~300 tokens instead of ~25,000 |
| TODO 5 | Edit `skills/trip-plan-format/SKILL.md`, start a new session, ask for the final plan | The new format, with no code change |

### Ex04: delegation
| Step | Send | Expect |
|---|---|---|
| Before TODOs | *"Find me a flight from Cluj to Lisbon on 2026-11-20."* | The coordinator has no team: it can't help |
| TODO 1-2 (`MODE = "chat"`) | The 5 messages below | `transfer_to_agent`; the specialist keeps the conversation (message 2 is answered by `flights_agent`); message 5 goes back to the coordinator |
| TODO 3 (`"single_turn"`) | The same 5 messages, in a new session | Specialists appear as tool calls of the coordinator; each specialist's request is small; the coordinator writes every answer |
| Bonus | *"I don't know where to go. Any cheap ideas for 2026-11-20 to 2026-11-22?"* | `destinations_agent` with Skiplagged |

The 5 messages:
1. *"I have 1000 lei and I'm free from 2026-11-20 to 2026-11-22. Find me the cheapest return flight from Cluj to Lisbon."*
2. *"Is there one that leaves later on Friday?"*
3. *"What will the weather be like in Lisbon that weekend?"*
4. *"Find me a cheap hostel there for the 2 nights."*
5. *"Add the cheapest flight and that hostel to my trip. How much of my budget is left?"*

### Ex05: classic workflows
Send *"Weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22. My budget is 1200 lei."*

| Step | Expect |
|---|---|
| Before TODOs | `budget_checker`: "no budget in the request"; the loop always runs 3 rounds |
| TODO 1 (budget fields) | The checker converts 1200 RON and judges the plan |
| TODO 2 (`ParallelAgent`) | The three scouts overlap in the **Trace** tab |
| TODO 3 (`exit_loop`) | 1200 lei: one re-plan, then stop. **3000 lei**: fits at once. **600 lei**: never fits, stopped by `max_iterations` |
| Step 5: **1000 lei** | Nothing fits (cheapest €192). Watch the planner's `total_eur`: it sometimes doesn't match its items, and the checker may accept it |

### Ex06: graph workflow
| Step | Send | Expect |
|---|---|---|
| TODO 1 | *"Weekend in Tokyo from Cluj, 2026-11-20 to 2026-11-22."* | Before: no answer at all. After: "I can't plan this trip yet: ..." from code, 1 LLM call in total |
| TODO 2 | The Barcelona message with **600 lei** | Before: a €466 plan presented as fitting. After: the verdict is correct |
| TODO 3 | With **1200**, then **600**, then **3000** lei | 1200: one re-plan, fits (~€220). 600: gives up after `MAX_ROUNDS`, says nothing fits (€192 vs ~€112). 3000: fits at once |

## Reference numbers (DeepSeek V4.1 Flash via Deploy, one run each)
| | Model calls | Input tokens | Time |
|---|---|---|---|
| Ex02, the Barcelona request | 2-3 | 4-7k | 12-18 s |
| Ex04, 5 messages: one agent (ex03) / transfer / single_turn | 12 / 14 / 21 | 132k / 87k / 89k | 57 / 51 / 93 s |
| Ex05, 1200 lei | 14-15 | ~14k | 75-95 s |
| Ex06, 1200 lei / 3000 lei | 11 / 10 | ~11k / ~10k | 90 / 38 s |

Workflow runs vary a lot: one ex06 run took 379 s. Kiwi and Skiplagged are live services: results
and prices change, and Skiplagged's results from CLJ changed during development (0 → 39).

## Known open points
- [ ] Update the dates in the exercise READMEs shortly before the workshop.
- [ ] Commit `scripts/smoke_test.py`: the ex04 README tells students to use it.
- [ ] Deploy (Hive) allowed ~5 requests at once in testing; per key or per account is unknown. Ex05/06 send 3 at once per student. Test with 2-3 keys in parallel before the session.
- [ ] Ex01 README still says "change `BEDROCK_MODEL`" (step 3): DeepSeek is now the default.
- [ ] Bedrock with Claude Sonnet 5.5: not tested yet.
- [ ] Ex06 README mentions the UI's graph view: check its exact label in `adk web`.
- [ ] Optional: make `check_setup.py` check access to `mcp.kiwi.com` and `mcp.skiplagged.com`.
