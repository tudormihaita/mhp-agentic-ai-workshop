"""Exercise 3 - our own MCP server.

The tools from Exercise 2, moved into a separate program that speaks MCP. Any MCP client can use
them now: our ADK agent, MCP Inspector, Claude Desktop, VS Code, ...

The agent starts this file itself (see agent.py), so you don't run it by hand. To try it alone:
    npx @modelcontextprotocol/inspector python exercises/ex03_mcp/trip_server.py     (needs Node.js)

TODO 1 is at the bottom of this file's tool list: search_hotels is already exposed, the other two aren't.

Notes:
  - The server is a separate process: it can't see the ADK session, so tools that need
    session state (add_to_trip, get_trip) stay in the agent as local tools.
  - Never print() in a stdio MCP server: stdout is the channel the protocol messages go through.
"""

from __future__ import annotations

import logging
from datetime import date as Date

import httpx
from mcp.server.mcpserver import MCPServer

logging.getLogger("httpx").setLevel(logging.WARNING)  # keep the adk web terminal readable

server = MCPServer("trip-planner")

HTTP_TIMEOUT = 10.0
USER_AGENT = {"User-Agent": "agentic-ai-workshop/1.0"}

HOTELS = {
    "Lisbon": [
        {"id": "LIS-H1", "name": "Alfama Backpackers", "type": "hostel", "price_per_night": 24, "rating": 8.9},
        {"id": "LIS-H2", "name": "Casa do Fado", "type": "guesthouse", "price_per_night": 58, "rating": 9.1},
        {"id": "LIS-H3", "name": "Hotel Tejo Central", "type": "hotel", "price_per_night": 110, "rating": 8.4},
    ],
    "Barcelona": [
        {"id": "BCN-H1", "name": "Gothic Quarter Hostel", "type": "hostel", "price_per_night": 29, "rating": 8.5},
        {"id": "BCN-H2", "name": "Pension Gracia", "type": "guesthouse", "price_per_night": 65, "rating": 8.7},
        {"id": "BCN-H3", "name": "Hotel Diagonal Mar", "type": "hotel", "price_per_night": 135, "rating": 8.8},
    ],
    "Rome": [
        {"id": "FCO-H1", "name": "Termini Youth Hostel", "type": "hostel", "price_per_night": 27, "rating": 8.1},
        {"id": "FCO-H2", "name": "Trastevere Rooms", "type": "guesthouse", "price_per_night": 70, "rating": 9.0},
    ],
    "Milan": [
        {"id": "MIL-H1", "name": "Navigli Hostel", "type": "hostel", "price_per_night": 33, "rating": 8.3},
        {"id": "MIL-H2", "name": "Hotel Brera Garden", "type": "hotel", "price_per_night": 118, "rating": 8.7},
    ],
    "Vienna": [
        {"id": "VIE-H1", "name": "Naschmarkt Hostel", "type": "hostel", "price_per_night": 26, "rating": 8.6},
        {"id": "VIE-H2", "name": "Hotel Ringstrasse", "type": "hotel", "price_per_night": 98, "rating": 8.5},
    ],
    "Paris": [
        {"id": "CDG-H1", "name": "Montmartre Hostel", "type": "hostel", "price_per_night": 38, "rating": 8.2},
        {"id": "CDG-H2", "name": "Hotel Canal Saint-Martin", "type": "hotel", "price_per_night": 125, "rating": 8.6},
    ],
    "Athens": [
        {"id": "ATH-H1", "name": "Plaka Hostel", "type": "hostel", "price_per_night": 21, "rating": 8.8},
        {"id": "ATH-H2", "name": "Acropolis View Rooms", "type": "guesthouse", "price_per_night": 55, "rating": 9.2},
    ],
}


@server.tool()
def search_hotels(city: str, nights: int, max_price_per_night: int = 1000) -> dict:
    """Find places to stay in a city, cheapest first (demo data).

    Args:
        city: City name in English, e.g. "Lisbon".
        nights: Number of nights to stay.
        max_price_per_night: Upper price limit per night in EUR (optional).

    Returns:
        A dict with matching stays (id, name, type, price_per_night, total_eur, rating).
    """
    stays = HOTELS.get(city.strip().title())
    if stays is None:
        return {"status": "error", "message": f"No demo data for '{city}'. Available: {', '.join(HOTELS)}."}
    matches = [
        {**s, "total_eur": s["price_per_night"] * nights}
        for s in sorted(stays, key=lambda s: s["price_per_night"])
        if s["price_per_night"] <= max_price_per_night
    ]
    return {"status": "ok", "source": "demo data", "nights": nights, "stays": matches}


# TODO 1: Expose get_weather_forecast and convert_currency as MCP tools, the same way as
#   search_hotels above: one decorator each. That's all it takes: the server reads the name,
#   type hints and docstring, exactly like ADK did in Exercise 2.
#   Check: restart adk web, open ex03_mcp, and ask "What's the weather in Lisbon on <a date this week>?"
def get_weather_forecast(city: str, date: str) -> dict:
    """Get the weather forecast for a city on a specific day (live data from Open-Meteo).

    Forecasts exist only for roughly the next 16 days. For dates further ahead, this returns an
    error: tell the user the forecast isn't available yet instead of guessing.

    Args:
        city: City name, e.g. "Lisbon".
        date: Day in ISO format YYYY-MM-DD.

    Returns:
        A dict with min/max temperature in °C and the chance of rain in percent.
    """
    try:
        Date.fromisoformat(date)
    except ValueError:
        return {"status": "error", "message": f"Invalid date '{date}'. Use YYYY-MM-DD."}
    try:
        geo = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1}, headers=USER_AGENT, timeout=HTTP_TIMEOUT,
        ).json()
        if not geo.get("results"):
            return {"status": "error", "message": f"City '{city}' not found."}
        place = geo["results"][0]
        data = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "start_date": date, "end_date": date,
            },
            headers=USER_AGENT, timeout=HTTP_TIMEOUT,
        ).json()
    except httpx.HTTPError as e:
        return {"status": "error", "message": f"Weather service unreachable: {type(e).__name__}."}
    if data.get("error"):
        return {"status": "error", "message": data.get("reason", "Weather service error.")}
    daily = data["daily"]
    return {
        "status": "ok",
        "city": f"{place['name']}, {place.get('country', '')}",
        "date": date,
        "temp_min_c": daily["temperature_2m_min"][0],
        "temp_max_c": daily["temperature_2m_max"][0],
        "rain_chance_pct": daily["precipitation_probability_max"][0],
    }


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert money between currencies using today's exchange rate (live data from the ECB).

    Args:
        amount: The amount to convert.
        from_currency: 3-letter ISO currency code, e.g. "EUR", "RON", "USD", "GBP".
        to_currency: 3-letter ISO currency code to convert into.

    Returns:
        A dict with the converted amount and the rate used.
    """
    src, dst = from_currency.strip().upper(), to_currency.strip().upper()
    if src == dst:
        return {"status": "ok", "amount": amount, "currency": dst, "rate": 1.0}
    try:
        resp = httpx.get(
            "https://api.frankfurter.dev/v1/latest",
            params={"base": src, "symbols": dst}, headers=USER_AGENT, timeout=HTTP_TIMEOUT,
        )
    except httpx.HTTPError as e:
        return {"status": "error", "message": f"Exchange-rate service unreachable: {type(e).__name__}."}
    if resp.status_code != 200:
        return {
            "status": "error",
            "message": f"Unknown currency '{src}' or '{dst}'. Use 3-letter ISO codes like EUR, RON, USD.",
        }
    data = resp.json()
    rate = data["rates"][dst]
    return {"status": "ok", "amount": round(amount * rate, 2), "currency": dst, "rate": rate, "rate_date": data["date"]}


if __name__ == "__main__":
    server.run()  # stdio transport: the client (our agent) talks to us through stdin/stdout
