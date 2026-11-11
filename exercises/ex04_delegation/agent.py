"""Exercise 4 - Delegation: a coordinator and specialists.

The same task as Exercise 3, split by job: each specialist sees only its own tools and instructions.
Run it (from the repo root):
    adk web --reload_agents exercises      -> pick `ex04_delegation`
"""

import sys
from datetime import date
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams, StreamableHTTPConnectionParams
from mcp import StdioServerParameters

from common import get_model
from common.travel import add_to_trip, get_trip, trim_flight_results

# How the coordinator uses its specialists:
#   "chat"        -> transfer: the specialist takes over the conversation (ADK's default)
#   "single_turn" -> the specialist does one job and returns the result; the coordinator stays in charge
# TODO 3: after trying the conversation in the README with "chat", switch to "single_turn" and repeat it.
MODE = "chat"

TODAY = date.today().isoformat()
TRIP_SERVER = Path(__file__).resolve().parents[2] / "solutions" / "ex03_mcp" / "trip_server.py"  # finished ex03 server


def trip_server(*tool_names: str) -> McpToolset:
    """Our MCP server from Exercise 3, showing only the given tools to the agent that uses it."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command=sys.executable, args=[str(TRIP_SERVER)]), timeout=30
        ),
        tool_filter=list(tool_names),
    )


flights_agent = Agent(
    name="flights_agent",
    model=get_model(),
    mode=MODE,
    description="Finds real flights with live prices and booking links (Kiwi.com). Use for anything about flights.",
    instruction=(
        f"You find flights with search-flight. Today is {TODAY}. Students fly from Cluj (CLJ) unless they "
        "say otherwise. Prefer one return search over two one-way searches. Follow the tool's date format. "
        "Prices in EUR. Always include the booking link. Never invent flights or prices. Answer briefly."
    ),
    tools=[McpToolset(
        connection_params=StreamableHTTPConnectionParams(url="https://mcp.kiwi.com", timeout=60),
        tool_filter=["search-flight"],
    )],
    after_tool_callback=trim_flight_results,
)

stays_agent = Agent(
    name="stays_agent",
    model=get_model(),
    mode=MODE,
    description="Finds hostels, guesthouses and hotels in a city, cheapest first.",
    instruction="You find places to stay with search_hotels. Never invent stays or prices. Answer briefly.",
    tools=[trip_server("search_hotels")],
)

# TODO 1: Finish the weather specialist.
#   - description: the coordinator reads ONLY this to decide when to delegate to this agent.
#     Say what it does, like the other specialists.
#   - tools: our MCP server, but showing only "get_weather_forecast" (see stays_agent).
weather_agent = Agent(
    name="weather_agent",
    model=get_model(),
    mode=MODE,
    description="TODO",
    instruction=(
        f"You give weather forecasts with get_weather_forecast. Today is {TODAY}. Forecasts exist only "
        "for about 16 days ahead: if a date is further away, say so. Add one line on what to pack."
    ),
    tools=[],
)

destinations_agent = Agent(
    name="destinations_agent",
    model=get_model(),
    mode=MODE,
    description="Suggests the cheapest places to fly to when the user doesn't know where to go.",
    instruction=(
        f"You suggest destinations with sk_destinations_anywhere. Today is {TODAY}. Search from the "
        "user's airport (Cluj, CLJ, by default). Bucharest (OTP) often has cheaper flights: if results are "
        "few or expensive, search OTP too and mention the train to Bucharest (about 8h). Use currency EUR. "
        "Show the 5 cheapest (city, country, approximate price)."
    ),
    tools=[McpToolset(
        connection_params=StreamableHTTPConnectionParams(url="https://mcp.skiplagged.com/mcp", timeout=60),
        tool_filter=["sk_destinations_anywhere"],
    )],
)

root_agent = Agent(
    name="trip_coordinator",
    model=get_model(),
    description="Plans budget weekend trips for students.",
    instruction=(
        f"You coordinate a student's weekend trip plan. Today is {TODAY}.\n"
        "- Delegate to your specialists: flights, stays, weather, and destination ideas.\n"
        "- You handle the budget (convert_currency: prices are in EUR) and the trip list "
        "(add_to_trip, get_trip). Only add items after the user picks them.\n"
        "- Never invent prices, flights, hotels or weather.\n"
        "- Current trip total: {trip_total_eur?} EUR."
    ),
    tools=[trip_server("convert_currency"), add_to_trip, get_trip],
    # TODO 2: Give the coordinator its team: list the four specialists.
    sub_agents=[],
)
