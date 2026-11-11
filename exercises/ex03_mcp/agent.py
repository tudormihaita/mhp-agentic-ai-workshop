"""Exercise 3 - The trip planner gets its tools from MCP servers.

Run it (from the repo root):
    adk web --reload_agents exercises      -> pick `ex03_mcp`
"""

import sys
from datetime import date
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams, StreamableHTTPConnectionParams
from mcp import StdioServerParameters  # noqa: F401  (used in TODO 2)

from common import get_model

from .tools import add_to_trip, get_trip, trim_flight_results  # noqa: F401  (trim_flight_results: TODO 4)

# A public remote MCP server (HTTP): real flight search from Kiwi.com, no API key needed.
# Use it as the example for TODO 2.
kiwi_flights = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="https://mcp.kiwi.com", timeout=60),
    tool_filter=["search-flight"],  # the server also has "feedback-to-devs": the model doesn't need it
)

# TODO 2: Connect to our own MCP server, trip_server.py, which runs as a local process.
#   For a local server the connection is "stdio": ADK starts the program and talks to it through
#   its stdin/stdout. Replace None with:
#       McpToolset(connection_params=StdioConnectionParams(
#           server_params=StdioServerParameters(command=..., args=[...]), timeout=30))
#   - command: the Python that runs this code -> sys.executable
#   - args:    the path to trip_server.py     -> str(Path(__file__).with_name("trip_server.py"))
#   Then add trip_server to the agent's tools list below.
trip_server = None

# Another public server, with 10 tools (flights, hotels, car rental, flexible dates, ...).
# TODO 3: Open the agent in adk web and look at the tools it lists (Info / Events tab). Each tool
#   definition is sent to the model on EVERY request and costs tokens. We only need
#   "sk_destinations_anywhere": add tool_filter=[...] like the Kiwi connection above.
skiplagged = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="https://mcp.skiplagged.com/mcp", timeout=60),
)

root_agent = Agent(
    name="trip_planner",
    model=get_model(),
    description="Plans budget weekend trips for students, with live flight prices.",
    instruction=(
        "You help students plan cheap weekend trips. Today is " + date.today().isoformat() + ".\n"
        "- Never invent prices, flights, hotels or weather: always get them from your tools.\n"
        "- Flights: use search-flight (live prices from Kiwi.com). Prefer a return search over two "
        "one-way searches. Always show the booking link.\n"
        "- If the user doesn't know where to go, use sk_destinations_anywhere (works best from big "
        "airports such as OTP Bucharest). Ask for prices in EUR.\n"
        "- Each tool documents its own date format: follow it exactly.\n"
        "- If a tool returns an error, read the message, fix your call and try again, "
        "or explain the problem to the user.\n"
        "- Prices are in EUR. If the user gives a budget in another currency, convert it first.\n"
        "- Only add items to the trip after the user picks them.\n"
        "- Think out loud: before each tool call, write one short line starting with 'Thinking:' "
        "that says what you need to find out and which tool you will use.\n"
        "- Current trip total: {trip_total_eur?} EUR."
    ),
    # Local tools and MCP toolsets mix freely: the model can't tell where a tool lives.
    tools=[kiwi_flights, skiplagged, add_to_trip, get_trip],
    # TODO 4: after implementing trim_flight_results in tools.py, uncomment:
    # after_tool_callback=trim_flight_results,
)
