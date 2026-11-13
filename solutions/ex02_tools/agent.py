"""Exercise 2 - solution: a trip-planning agent with tools."""

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
        "- If a tool returns an error, read the message, fix your call and try again, "
        "or explain the problem to the user.\n"
        "- Prices are in EUR. If the user gives a budget in another currency, convert it first.\n"
        "- Only add items to the trip after the user picks them.\n"
        "- Current trip total: {trip_total_eur?} EUR."
    ),
    tools=[search_flights, search_hotels, get_weather_forecast, convert_currency, add_to_trip, get_trip],
)
