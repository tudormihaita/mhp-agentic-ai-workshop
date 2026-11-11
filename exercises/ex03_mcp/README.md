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

4. **TODO 3: too many tools.** Skiplagged exposes 10 tools. Every tool's definition is sent to the
   model on **every** request. Find the tool list in the trace, add a `tool_filter`, and compare.
   You can't edit a third-party tool's description: you choose *which* tools to expose, and you
   steer with your instruction.

5. **TODO 4: too much data.** One Kiwi search returns ~15 itineraries with every flight segment.
   Implement `trim_flight_results` in `tools.py` and enable `after_tool_callback`. It runs after
   every tool call and can replace the result before the model sees it.

6. **Where should a tool live?** `add_to_trip` and `get_trip` stayed in the agent. Why can't they
   move to `trip_server.py`? (Hint: where is the session state?)

7. **Bonus: flexible destination.** Ask: *"I'm flying from Bucharest on 2026-11-20, back on the 22nd.
   Where can I go cheaply?"* Then plan the cheapest one: flight, stay, weather.

## Context check: measured on the solution
| What the model receives | Tokens (approx.) |
|---|---|
| Kiwi `search-flight` tool **definition** (44 parameters), on every request | ~4,500 |
| Skiplagged tool definitions: all 10 / filtered to 1 | ~10,900 / ~1,200 |
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

## Takeaways
- MCP separates **who builds a tool** from **who uses it**: write a server once, use it from any client.
- A third-party tool is someone else's API: its description, parameters and output size are theirs.
  You control which tools you expose (`tool_filter`), your instruction, and what reaches the model
  (`after_tool_callback`).
- Tools cost context twice: their **definitions** on every request, and their **results** for the
  rest of the conversation.
