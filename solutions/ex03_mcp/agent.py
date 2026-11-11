"""Exercise 3 - solution: the trip planner with tools from MCP servers."""

import sys
from datetime import date
from pathlib import Path

from google.adk.agents import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams, StreamableHTTPConnectionParams
from google.adk.tools.skill_toolset import SkillDiscoveryMode, SkillToolset
from mcp import StdioServerParameters

from common import get_model

from .tools import add_to_trip, get_trip, trim_flight_results

# 1. Our own MCP server (local process, stdio). ADK starts it and talks to it via stdin/stdout.
trip_server = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,  # the venv's python
            args=[str(Path(__file__).with_name("trip_server.py"))],
        ),
        timeout=30,
    ),
)

# 2. A public remote MCP server (HTTP): real flight search from Kiwi.com, no key needed.
kiwi_flights = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="https://mcp.kiwi.com", timeout=60),
    tool_filter=["search-flight"],  # the server also has "feedback-to-devs": the model doesn't need it
)

# 3. Another public server with 10 tools. We expose only the one we need...
skiplagged = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url="https://mcp.skiplagged.com/mcp", timeout=60),
    tool_filter=["sk_destinations_anywhere"],
)

# 4. ...and only when it's needed: skills. At first the model sees just each skill's name and
#    description. It calls load_skill when a request matches; then the skill's instructions enter the
#    context, and the tools listed in its `adk_additional_tools` (here: Skiplagged's) become available.
SKILLS_DIR = Path(__file__).with_name("skills")
skills = SkillToolset(
    skills=[load_skill_from_dir(SKILLS_DIR / "find-destination"), load_skill_from_dir(SKILLS_DIR / "trip-plan-format")],
    additional_tools=[skiplagged],
    discovery_mode=SkillDiscoveryMode.EAGER,  # skill names + descriptions go in the system instruction
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
        "- Each tool documents its own date format: follow it exactly.\n"
        "- If a tool returns an error, read the message, fix your call and try again, "
        "or explain the problem to the user.\n"
        "- Prices are in EUR. If the user gives a budget in another currency, convert it first.\n"
        "- Only add items to the trip after the user picks them.\n"
        "- Think out loud: before each tool call, write one short line starting with 'Thinking:' "
        "that says what you need to find out and which tool you will use.\n"
        "- Current trip total: {trip_total_eur?} EUR."
    ),
    tools=[trip_server, kiwi_flights, skills, add_to_trip, get_trip],
    after_tool_callback=trim_flight_results,
)
