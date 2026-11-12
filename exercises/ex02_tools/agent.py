"""Exercise 2 - A trip-planning agent with tools: the think -> act -> observe loop.

Run it (from the repo root):
    adk web --reload_agents exercises -> pick `ex02_tools`
"""

from datetime import date

from google.adk.agents import Agent

from common import get_model

from .tools import add_to_trip, convert_currency, get_trip, get_weather_forecast, search_flights, search_hotels

root_agent = Agent(
    name="trip_planner",
    model=get_model(),
    description="Plans budget weekend trips for students.",
    instruction=(
        "You help students plan cheap weekend trips. Today is " + date.today().isoformat() + ".\n"
        "- Never invent prices, flights, hotels or weather: always get them from your tools.\n"
        # TODO 4: Tell the agent what to do when a tool returns {"status": "error", ...}.
        "- Prices are in EUR. If the user gives a budget in another currency, convert it first.\n"
        "- Only add items to the trip after the user picks them.\n"
        # TODO 5: Make the agent think out loud: before each tool call it should write one short
        #   line starting with "Thinking:" (what it needs to find out, which tool it will use).
        # Session state injected into the prompt ({name?} = optional, empty if not set yet):
        "- Current trip total: {trip_total_eur?} EUR."
    ),
    # The model only sees these tools: their names, parameters and docstrings
    tools=[search_flights, search_hotels, get_weather_forecast, convert_currency, add_to_trip, get_trip],
)
