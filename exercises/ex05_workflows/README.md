# Exercise 5: Workflows (classic): sequential, parallel, loop

**Concept:** in Exercises 2-4 an LLM decided what happens next. In a **workflow, your code decides
the order**, and LLM agents fill in the steps. Steps pass data to each other through **session state**:

```
trip_pipeline (SequentialAgent)
├── request_parser            → state["request"]   structured output: TripRequest
├── research (ParallelAgent)
│   ├── flight_scout          → state["flights"]
│   ├── stay_scout            → state["stays"]
│   └── weather_scout         → state["weather"]
├── budget_loop (LoopAgent, max 3 rounds)
│   ├── planner               → state["plan"]      structured output: TripPlan
│   └── budget_checker        → state["review"], or calls exit_loop when the plan fits
└── presenter                 → the answer you see
```

Three classic patterns, one per building block:

| Block | Pattern | When |
|---|---|---|
| `SequentialAgent` | **Prompt chaining**: fixed steps, each with a small, focused prompt | The steps are known in advance |
| `ParallelAgent` | **Parallelization**: independent steps at the same time | Steps don't depend on each other |
| `LoopAgent` | **Evaluator-optimizer**: one agent proposes, another checks, repeat | Output must pass a check |

`SequentialAgent`, `ParallelAgent` and `LoopAgent` contain no LLM: they are just control flow.
(ADK 2 marks them as deprecated in favour of graph workflows, Exercise 6. They are the easiest way to
learn the patterns.)

## Run it
```bash
adk web --reload_agents exercises      # pick ex05_workflows
```
Send one message: *"Weekend in Barcelona from Cluj, 2026-11-20 to 2026-11-22. My budget is 1200 lei."*
A workflow is not a conversation: every message runs the whole pipeline again.

## Steps

1. **Read the run.** Send the message above. In the **Events** tab, find each step and its output.
   In the **State** tab, find `request`, `flights`, `stays`, `weather`, `plan`. Then look at
   `budget_checker`'s answers: what does it say?

2. **TODO 1: structured output.** `request_parser` turns free text into a `TripRequest` object
   (`output_schema`). The budget is missing from it, and the later steps **only** see what is in state:
   each one has `include_contents="none"`, so it doesn't see the chat. Add the two budget fields and
   run again.

3. **TODO 2: parallel.** The three scouts don't depend on each other. Make `research` a
   `ParallelAgent` and compare the timing in the **Trace** tab.

4. **TODO 3: stop the loop.** The checker never has a way to say "done", so the loop always runs 3
   rounds. Give it the `exit_loop` tool. Then try a budget of **3000 lei** (fits at once) and
   **600 lei** (can never fit: what stops the loop?).

5. **Check the checker.** Try **1000 lei**: no plan fits (the cheapest is €192, about 1030 lei).
   Look at the planner's `total_eur` in each round: does it match the prices of the items it
   chose? Did the checker notice? (Exercise 6 replaces this check with plain code.)

## Agent or workflow? Same request, measured (DeepSeek, demo data, 1200 lei)

| | Model calls | Input tokens | Time | Same structure every run? | Budget check |
|---|---|---|---|---|---|
| One agent with tools (Exercise 2) | 2-3 | 4-7k | 12-18 s | no | only if the model thinks of it |
| This workflow | 14-15 | ~14k | 75-95 s | yes | always, as a separate step |

On this small task, **the single agent is faster and cheaper**. The workflow buys something else:
steps that always happen, a structured request you can validate, the same output shape every time,
and steps you can test one at a time.

| Choose a **workflow** when... | Choose an **agent** when... |
|---|---|
| The steps are known in advance | The path depends on what you find along the way |
| Some steps must always happen (validation, checks) | The user drives the conversation |
| Cost and latency must be predictable | Flexibility matters more than predictability |
| You want to test each step on its own | The number of steps isn't known in advance |

Real systems mix both: an agent can call a workflow as a tool, and a workflow step can be an agent.

## Generic example
```python
class Order(BaseModel):
    item: str = Field(description="What the user wants to buy.")

parser = Agent(name="parser", model=get_model(), instruction="Extract the order.",
               output_schema=Order, output_key="order")          # result -> state["order"]
worker = Agent(name="worker", model=get_model(), include_contents="none",
               instruction="Order: {order}\nFind the best price.", tools=[search], output_key="offer")
pipeline = SequentialAgent(name="pipeline", sub_agents=[parser, worker])
```

## Takeaways
- In a workflow, **code** owns the control flow; LLMs only do the steps that need language.
- **Structured output** (`output_schema`) is the contract between steps: later steps rely on its fields.
- With `include_contents="none"`, a step sees only the state you inject: smaller prompts, and no
  hidden dependency on the chat.
- An LLM checking an LLM can be fooled. Arithmetic and rules belong in code (Exercise 6).
