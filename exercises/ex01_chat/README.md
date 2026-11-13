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
   started `adk web` with `--reload_agents`), or restart `adk web` (Ctrl+C, run it again), and check that the agent's behavior changes.

3. **Find the limits**. Ask:
   - *What is today's date?*
   - *What is the latest version of the `google-adk` Python package?*
   - *What's the weather in Cluj-Napoca right now?*

   Does the model admit it doesn't know, or does it make something up? Why can't it know?

4. **Look under the hood.** In the `adk web` UI, open the **Events** / trace tab and click on a message:
   find the request sent to the model. What is in it besides your message? Find your instruction,
   and the line ADK added from the agent's `name` and `description`.

## Takeaways
- Agent = model + instructions (+ tools + memory + loop, coming next).
- The instruction shapes behavior a lot; the model sets the ceiling of quality.
- The model only knows its training data. It has no clock, no internet and no access to your files.
