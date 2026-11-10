# Exercise 1: A chat agent (the LLM is a replaceable part)

**Concept:** an LLM on its own is a *stateless text-in, text-out function*. An agent wraps it with
instructions (and later tools, memory and a loop). The model behind the agent can be swapped
without changing the agent's code.

## Steps

1. **Run it.** From the repo root (virtual environment active):
   ```bash
   adk web exercises
   ```
   Open http://localhost:8000, pick **ex01_chat** in the top-left dropdown and say hello.
   The terminal prints which model is in use.

2. **Write the instruction.** Open `agent.py` and complete `TODO 1`. Start a **new session** in the UI (if you
   started `adk web` with `--reload_agents`), or restart `adk web` (Ctrl+C, run it again), and check that the agent's behaviour changes.

3. **Swap the model.** In `.env`, change `BEDROCK_MODEL` (or `MODEL_PROVIDER`), restart, and ask the
   *same* questions again. Fill in the table:

   | Question | Model A | Model B | Model C |
   |---|---|---|---|
   | Explain recursion with a short Python example | | | |
   | What is the difference between a process and a thread? | | | |
   | Write a haiku about debugging | | | |

   Compare: quality, speed, length, style. Did the agent's *code* change at all?

4. **Find the limits** (sets up Exercise 2). Ask:
   - *What is today's date?*
   - *What is the latest version of the `google-adk` Python package?*
   - *What's the weather in Cluj-Napoca right now?*

   Does the model admit it doesn't know, or does it make something up? Why can't it know?

5. **Look under the hood.** In the `adk web` UI, open the **Events** / trace tab and click on a message:
   find the request sent to the model. What is in it besides your message?

## Takeaways
- Agent = model + instructions (+ tools + memory + loop, coming next).
- The instruction shapes behaviour a lot; the model sets the ceiling of quality.
- The model only knows its training data. It has no clock, no internet and no access to your files.
