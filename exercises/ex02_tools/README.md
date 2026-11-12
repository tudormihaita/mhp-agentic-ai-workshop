# Exercise 2: Tools and the agent loop (think → act → observe)

**Concept:** an LLM can't check a flight price or a forecast. With **tools** it doesn't need to:
the model *asks* for a function call, ADK runs the function, and the result goes back to the model.
This repeats until the model can answer. That repetition is **the agent loop**:

```
user ──► model ──think──► function_call ──act──► your Python function
            ▲                                          │
            └────────── function_response ◄──observe───┘
         (repeat until the model answers in text)
```

The model never sees your code. It only sees each tool's **name, parameters and docstring**.

## Run it
```bash
adk web --reload_agents exercises      # pick ex02_tools
```

## The tools (`tools.py`)
| Tool | Data | Status |
|---|---|---|
| `search_flights` | demo data (fake) | complete: read it as an example |
| `search_hotels` | demo data (fake) | complete |
| `get_weather_forecast` | **live**, Open-Meteo | TODO 1 |
| `convert_currency` | **live**, ECB rates via Frankfurter | works, but TODO 3 |
| `add_to_trip`, `get_trip` | session state | TODO 2 |

## Steps

1. **Watch the loop.** Before changing anything, ask:
   *"Find me the cheapest flight from Cluj to Lisbon on 2026-11-20 and back on 2026-11-22."*
   In the **Events** tab, click each event and find the `function_call` and `function_response`.
   How many times was the model called? Why twice for `search_flights`?

2. **TODO 1: live weather.** Finish `get_weather_forecast`. Then ask:
   *"Will it rain in Lisbon this Saturday?"* and *"What's the weather in Lisbon next March?"*
   The second question fails on purpose. Find the error in the trace: what did the tool return,
   and what did the model do with it?

3. **TODO 2: remember the trip.** Implement `add_to_trip` and `get_trip` with `tool_context.state`.
   Pick a flight and a hostel, then open the **State** tab. Look at the instruction in `agent.py`:
   `{trip_total_eur?}` puts the state value into the prompt on every turn.

4. **TODO 3: an out-of-date tool description.** Ask *"My budget is 1500 lei, how much is that in euros?"*
   What does the model pass to `convert_currency`, and why? How does it recover? Fix the docstring
   so it matches the code, start a new session and count the calls again.
   The model follows the docstring, not your code: a tool called wrongly is usually a
   **documentation bug**, not a model bug.

5. **TODO 4: errors are observations.** Add an instruction line saying what to do when a tool
   returns `"status": "error"`. Test it: *"Flights from Cluj to Lisbon on 20 November"*
   (the model must work out the airport codes and date format; the error message lists the valid codes).

6. **TODO 5: make the thinking visible.** Ask the big one first, without TODO 5:
   *"Plan a weekend in Lisbon or Barcelona from Cluj, 2026-11-20 to 2026-11-22, under 1500 lei,
   and preferably where it won't rain. Compare both."*
   Count the model calls in the trace. Then add the "Thinking:" instruction, start a new session and
   ask again. Every step is now visible: `Thinking:` (think), a tool call (act), a result (observe).
   **Count the model calls again.** Why are there more now? (Hint: before, the model could ask for
   several tools in one go.) Seeing the reasoning costs time and tokens.

## Generic example
```python
def get_book(isbn: str) -> dict:
    """Look up a book in the library catalogue.

    Args:
        isbn: 13-digit ISBN without dashes, e.g. "9780262033848".

    Returns:
        {"status": "ok", "title": ..., "available": bool} or {"status": "error", "message": ...}.
    """
    book = CATALOGUE.get(isbn)
    if book is None:
        return {"status": "error", "message": "ISBN not found. Use 13 digits, no dashes."}
    return {"status": "ok", **book}

agent = Agent(name="librarian", model=get_model(), instruction="...", tools=[get_book])
```

## Context check
- Everything a tool returns is added to the conversation, and the **whole conversation is
  re-sent to the model on every call**. Find this in a later request in the trace. That's why
  tools should return small results.
- `tool_context.state` keeps facts *outside* the prompt. You choose what goes back in (`{trip_total_eur?}`).

## Takeaways
- Agent = model + instructions + tools + **a loop** that runs until the model is done.
- Docstrings and type hints are the tool's interface to the model: write them for the model.
- Return errors as data. The model can read them and correct itself.
