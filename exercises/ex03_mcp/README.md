# Exercise 3: MCP: tools from servers

**Concept:** in Exercise 2 the tools were Python functions *inside* the agent. With the
**Model Context Protocol (MCP)** tools live in a separate **server**, and any MCP **client**
(an ADK agent, Claude Desktop, VS Code, Cursor, ...) can discover and call them:

```
                 ┌─ stdio (local process) ──► trip_server.py      (ours: hotels, weather, currency)
ADK agent ──MCP──┼─ HTTP ───────────────────► mcp.kiwi.com        (public: live flight prices)
(client)         └─ HTTP ───────────────────► mcp.skiplagged.com  (public: "where can I go cheaply?")
```

The model can't tell the difference: an MCP tool looks exactly like a local one (name,
parameters, description). What changes is **who writes, runs and maintains the tool**.

## Run it
```bash
adk web --reload_agents exercises      # pick ex03_mcp
```
Kiwi and Skiplagged are live services on the internet: results change, and they may be slow or
rate-limited. That's real-world MCP.

## Steps

1. **Real flights.** Ask: *"Find the cheapest return flight from Cluj to Lisbon, 2026-11-20 to 2026-11-22."*
   Compare with the demo prices from Exercise 2. Then look at the `search-flight` call in the trace:
   - Which **date format** did the model use? Where did it learn it? (Hint: you didn't write that tool.)
   - How big is the **result**? Scroll through it.

2. **TODO 1: expose our own tools.** In `trip_server.py`, `search_hotels` is already an MCP tool.
   Expose `get_weather_forecast` and `convert_currency` too (one decorator each).

3. **TODO 2: connect our server.** In `agent.py`, create the stdio connection to `trip_server.py` and
   add it to the agent's tools. Ask: *"Cheapest stay in Lisbon for 2 nights, and will it rain on Saturday?"*
   Nothing about the tools changed from Exercise 2: same code, same docstrings, now behind a protocol.

4. **TODO 3: too many tools → skills.** Skiplagged exposes 10 tools, and every tool's definition is
   sent to the model on **every** request, even for "hi". Find them in the trace (a model call →
   Request). We need one of them, and only when the user doesn't know where to go.
   - `tool_filter` (like on Kiwi) removes tools **for good**: you decide in code.
   - A **skill** loads tools and instructions **when needed**: the model decides. Until then it sees
     only the skill's name and one-line description.

   Finish `skills/find-destination/SKILL.md` (the description and the tool it unlocks), then wire up
   the skills in `agent.py`. Ask: *"I'm free 2026-11-20 to 2026-11-22 with 200 euros. Where could I
   go?"* In the trace: which tools does the first model call get? What changes after `load_skill`?

   The second skill, `trip-plan-format`, is already finished: it unlocks no tool, it only brings a
   template. Plan a trip, add a flight and a stay, then say *"I'm done, give me the final plan."*

5. **TODO 4: too much data.** One Kiwi search returns ~15 itineraries with every flight segment.
   Implement `trim_flight_results` in `tools.py` and enable `after_tool_callback`. It runs after
   every tool call and can replace the result before the model sees it.

6. **Where should a tool live?** `add_to_trip` and `get_trip` stayed in the agent. Why can't they
   move to `trip_server.py`? (Hint: where is the session state?)

7. **TODO 5 (optional): make the plan yours.** Edit the template or the style rules in
   `skills/trip-plan-format/SKILL.md`, start a new session and ask for the final plan again. Ideas:
   - Write the whole plan in Romanian.
   - If the chance of rain is above 50%, add a "Rainy-day plan" section with 2 indoor ideas.
   - Add a "Day by day" section: one line for each day of the trip.
   - Add a "Cost per day" line.
   - Make it shorter: no table, just 5 bullet points.

   No code changes: a skill is just text. The same file would work in any agent that supports skills
   (Claude Code, Gemini CLI, ...).

## Context check: measured on the solution
| What the model receives | Tokens (approx.) |
|---|---|
| Kiwi `search-flight` tool **definition** (44 parameters), on every request | ~4,500 |
| Skiplagged tool definitions: all 10 / filtered to 1 | ~10,900 / ~1,200 |
| Skills: the fixed cost (skill rules + `load_skill` tools) / each extra skill's name + description | ~700 / ~50 |
| One "Hi" with Skiplagged: not connected / all 10 tools / filtered to 1 / behind skills | 6.6k / 14.7k / 7.5k / 7.4k |
| One of our tool definitions | ~180 |
| One Kiwi search **result**, untrimmed | ~25,000 |
| The same result after `trim_flight_results` | ~300 |

Everything in the conversation is re-sent on every model call. Three untrimmed flight searches
≈ 75,000 tokens on every following call: slower, more expensive, and important details get lost.

## Generic example
```python
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams, StreamableHTTPConnectionParams
from mcp import StdioServerParameters

local = McpToolset(connection_params=StdioConnectionParams(
    server_params=StdioServerParameters(command="python", args=["my_server.py"])))
remote = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="https://example.com/mcp"),
    tool_filter=["only_this_tool"],
)
agent = Agent(name="assistant", model=get_model(), instruction="...", tools=[local, remote])
```
```python
# my_server.py
from mcp.server.mcpserver import MCPServer
server = MCPServer("my-server")

@server.tool()
def lookup(code: str) -> dict:
    """Look up a code. Args: code: 3 uppercase letters."""
    return {"status": "ok", "code": code}

if __name__ == "__main__":
    server.run()
```

```markdown
<!-- skills/my-skill/SKILL.md -->
---
name: my-skill
description: Does X. Use when the user asks for Y or mentions Z.
metadata:
  adk_additional_tools: [some_tool]   # optional: tools unlocked when the skill is loaded
---
Step-by-step instructions, rules, templates, examples...
```
```python
skills = SkillToolset(skills=[load_skill_from_dir(Path("skills/my-skill"))], additional_tools=[toolset])
```

## Takeaways
- MCP separates **who builds a tool** from **who uses it**: write a server once, use it from any client.
- A third-party tool is someone else's API: its description, parameters and output size are theirs.
- Tools cost context twice: their **definitions** on every request, and their **results** for the
  rest of the conversation. You have three levers:

  | Lever | Controls | Who decides |
  |---|---|---|
  | `tool_filter` | which tools exist at all | you, in code, for good |
  | skills | when instructions and tools enter the context | the model, when needed |
  | `after_tool_callback` | how big results are | you, in code, on every call |

- Skills package **know-how**, with or without tools: *how* to use a tool well (`find-destination`)
  or *how* to structure a response (`trip-plan-format`).
