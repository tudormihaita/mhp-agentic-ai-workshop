"""The finished trip-planner MCP server (the one you build in Exercise 3), shared by Exercise 4.

It exposes the travel tools from common/travel.py over MCP (stdio). Agents start it themselves:
    StdioServerParameters(command=sys.executable, args=["-m", "common.trip_server"])

Never print() in a stdio MCP server: stdout is the channel the protocol messages go through.
"""

from __future__ import annotations

import logging

from mcp.server.mcpserver import MCPServer

from common.travel import convert_currency, get_weather_forecast, search_hotels

logging.getLogger("httpx").setLevel(logging.WARNING)  # keep the adk web terminal readable

server = MCPServer("trip-planner")

# The same as decorating each function with @server.tool(): name, type hints and docstring
# become the tool's definition.
for tool in (search_hotels, get_weather_forecast, convert_currency):
    server.tool()(tool)

if __name__ == "__main__":
    server.run()
