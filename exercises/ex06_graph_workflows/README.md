# Exercise 6: Workflows (graph): nodes, edges, routes

**Concept:** the same pipeline as Exercise 5, written as a **graph**: nodes connected by edges. This is
ADK 2's recommended way to build workflows (`Workflow`). Two kinds of nodes:

- **LLM nodes** (`Agent`): only where language is needed: understand, research, choose, present.
- **Function nodes** (plain Python): rules and arithmetic. No LLM: free, fast, always correct.

```
START → parse_request → validate_request ──invalid──→ explain_problem
                              │ ok
                ┌─────────────┼─────────────┐
           flight_scout   stay_scout   weather_scout        (run in parallel)
                └─────────────┼─────────────┘
                           research (JoinNode: waits for all three)
                              ↓
                           planner ←──over──┐
                              ↓             │
                         check_budget ──────┘
                              │ fits / give_up
                           presenter
```

## The syntax in 30 seconds
```python
Workflow(name="trip_graph", edges=[
    (START, a, b),                          # a chain: START → a → b
    (b, {"ok": c, "invalid": d}),           # routing: b returns Event(route="ok") or route="invalid"
    ((c1, c2), JoinNode(name="j"), e),      # fan-out to c1 and c2 in parallel, then wait for both
    (e, {"again": a, "done": f}),           # an edge back to an earlier node = a loop
])
```
A function node gets its parameters **from session state, by name** (`def check_budget(request, plan)`
reads `state["request"]` and `state["plan"]`). It returns an `Event` with a `route`, new `state`, or a
`message` for the user.

## Run it
```bash
adk web --reload_agents exercises      # pick ex06_graph_workflows
```
The UI can draw the workflow as a graph: look for the graph view of the agent's structure and of each
event, and follow which nodes ran.

## Steps

1. **TODO 1: the "invalid" route.** Ask *"Weekend in Tokyo from Cluj, 2026-11-20 to 2026-11-22."*
   Nothing comes back: `validate_request` returned the route `"invalid"`, and no edge handles it.
   Map it to `explain_problem`, then ask again. How many LLM calls did the answer cost?

2. **TODO 2: the budget rule, in code.** Ask *"Weekend in Barcelona from Cluj, 2026-11-20 to
   2026-11-22. My budget is 600 lei."* The plan is presented as fitting, but it doesn't. Write the
   verdict in `check_budget`. Note how the total is computed: from the **real prices** of the chosen ids,
   not from what the planner claims (remember Exercise 5, step 5).

3. **TODO 3: the loop.** Ask again with **1200 lei**. Now `check_budget` can return `"over"`, but no
   edge handles it. Add the edge back to `planner`. Then try **600 lei** (can never fit) and
   **3000 lei** (fits at once). What stops the loop in the 600 lei case?

## Exercise 5 vs Exercise 6
| | Classic (Exercise 5) | Graph (Exercise 6) |
|---|---|---|
| Control flow | Nested containers: Sequential, Parallel, Loop | Explicit edges and routes |
| Rules and arithmetic | An LLM step (can be fooled) | Function nodes (plain code) |
| Invalid request | Runs the whole pipeline anyway | Stops after one LLM call, with a precise message |
| Loop limit | `max_iterations` | Your own counter (`MAX_ROUNDS`): a graph has no built-in limit |
| Measured (DeepSeek, 1200 lei, one re-plan) | 14-15 model calls, ~14k input tokens | 11 model calls, ~11k input tokens |

## Takeaways
- Use an LLM only where language or judgment is needed. Everything that can be a rule should be code.
- Routes make decisions **visible**: every branch is an edge you can read, test and draw.
- A graph gives you loops and branches freely, so limits are your job.
- Structured output (`TripRequest`, `TripPlan`) is what lets plain code work with an LLM's output.
