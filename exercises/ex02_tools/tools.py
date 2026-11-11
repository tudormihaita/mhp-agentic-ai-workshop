"""Exercise 2 - tools for the student trip planner.

Two kinds of tools:
  - LIVE: call free public APIs (no key needed): weather (Open-Meteo), exchange rates (Frankfurter).
  - DEMO: flights and hotels come from the fake data below. There's no free public booking API;
    in the MCP exercise you swap them for a real flight-search MCP server.

search_flights and search_hotels are complete: read them as examples.
Your TODOs are in get_weather_forecast, convert_currency, add_to_trip and get_trip.

How ADK turns a function into a tool:
  - the function name       -> tool name
  - the type hints          -> parameter types
  - the docstring           -> the description the MODEL reads to decide when and how to call it
  - a `tool_context` param  -> injected by ADK, hidden from the model (gives access to session state)

Tools return small dicts. On failure they return {"status": "error", "message": ...} instead of
raising: the model reads the error (the "observe" step) and can correct itself.
"""

from __future__ import annotations

import hashlib
from datetime import date as Date

import httpx
from google.adk.tools import ToolContext

HTTP_TIMEOUT = 10.0
USER_AGENT = {"User-Agent": "agentic-ai-workshop/1.0"}

# --------------------------------------------------------------------------------------------
# Demo data (fake); Prices in EUR.
# --------------------------------------------------------------------------------------------

AIRPORTS = {
    "CLJ": "Cluj-Napoca", "OTP": "Bucharest", "TSR": "Timisoara",
    "LIS": "Lisbon", "BCN": "Barcelona", "FCO": "Rome", "VIE": "Vienna", "CDG": "Paris", "ATH": "Athens",
}
# Route -> (base one-way price, flight duration). Only these routes exist in the demo data.
ROUTES = {
    ("CLJ", "LIS"): (95, "4h 10m"), ("CLJ", "BCN"): (70, "3h 05m"), ("CLJ", "FCO"): (55, "2h 05m"),
    ("CLJ", "VIE"): (60, "1h 25m"), ("CLJ", "CDG"): (85, "3h 00m"), ("CLJ", "ATH"): (65, "2h 00m"),
    ("OTP", "LIS"): (90, "4h 25m"), ("OTP", "BCN"): (75, "3h 20m"), ("OTP", "FCO"): (50, "2h 15m"),
    ("OTP", "VIE"): (55, "1h 40m"), ("OTP", "CDG"): (80, "3h 15m"), ("OTP", "ATH"): (45, "1h 40m"),
    ("TSR", "BCN"): (65, "2h 45m"), ("TSR", "FCO"): (50, "1h 50m"), ("TSR", "VIE"): (40, "1h 05m"),
}
AIRLINES = ["SkyHop", "Carpathia Air", "Danube Jet"]

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


def _parse_date(value: str) -> Date | None:
    try:
        return Date.fromisoformat(value)
    except ValueError:
        return None


def _demo_price(origin: str, destination: str, day: str, slot: int, base: int) -> int:
    """Deterministic 'random' price: same inputs -> same price on every laptop."""
    digest = hashlib.sha256(f"{origin}{destination}{day}{slot}".encode()).digest()
    weekend = Date.fromisoformat(day).weekday() >= 4  # Fri-Sun are pricier
    return int(base * (0.7 + digest[0] / 255 * 0.8) * (1.25 if weekend else 1.0))


# --------------------------------------------------------------------------------------------
# DEMO tools
# --------------------------------------------------------------------------------------------


def search_flights(origin: str, destination: str, date: str) -> dict:
    """Search one-way flights between two airports on a given day.

    Args:
        origin: 3-letter IATA airport code of departure, e.g. "CLJ" for Cluj-Napoca.
        destination: 3-letter IATA airport code of arrival, e.g. "LIS" for Lisbon.
        date: Departure day in ISO format YYYY-MM-DD.

    Returns:
        A dict with a list of flight offers (id, airline, departure time, duration, price_eur),
        cheapest first. For a round trip, call it twice (outbound and return).
    """
    origin, destination = origin.strip().upper(), destination.strip().upper()
    if origin not in AIRPORTS or destination not in AIRPORTS:
        return {
            "status": "error",
            "message": f"Unknown airport code. Use one of: {', '.join(f'{c} ({n})' for c, n in AIRPORTS.items())}.",
        }
    if _parse_date(date) is None:
        return {"status": "error", "message": f"Invalid date '{date}'. Use YYYY-MM-DD."}

    route = ROUTES.get((origin, destination)) or ROUTES.get((destination, origin))
    if route is None:
        return {"status": "ok", "flights": [], "message": f"No direct flights {origin} -> {destination}."}

    base, duration = route
    offers = [
        {
            "id": f"{origin}{destination}-{date}-{slot}",
            "airline": AIRLINES[slot],
            "departure": f"{date} {['06:40', '13:15', '19:50'][slot]}",
            "duration": duration,
            "price_eur": _demo_price(origin, destination, date, slot, base),
        }
        for slot in range(3)
    ]
    offers.sort(key=lambda o: o["price_eur"])
    return {"status": "ok", "source": "demo data", "flights": offers}


def search_hotels(city: str, nights: int, max_price_per_night: int = 1000) -> dict:
    """Find places to stay in a city, cheapest first.

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


# --------------------------------------------------------------------------------------------
# LIVE tools (public APIs, no key)
# --------------------------------------------------------------------------------------------


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
    if _parse_date(date) is None:
        return {"status": "error", "message": f"Invalid date '{date}'. Use YYYY-MM-DD."}
    try:
        geo = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1}, headers=USER_AGENT, timeout=HTTP_TIMEOUT,
        ).json()
        if not geo.get("results"):
            return {"status": "error", "message": f"City '{city}' not found."}
        place = geo["results"][0]
        # TODO 1: Ask Open-Meteo for the forecast of that place on that day.
        #   GET https://api.open-meteo.com/v1/forecast with these query params:
        #     latitude, longitude    -> from `place`
        #     timezone               -> "auto"
        #     daily                  -> "temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        #     start_date, end_date   -> both `date`
        #   Use httpx.get(..., params={...}, headers=USER_AGENT, timeout=HTTP_TIMEOUT).json()
        #   (look at the geocoding call above).
        data = {"error": True, "reason": "TODO 1: forecast not implemented yet"}
    except httpx.HTTPError as e:
        return {"status": "error", "message": f"Weather service unreachable: {type(e).__name__}."}

    # Open-Meteo answers {"error": true, "reason": "..."} for bad input (e.g. a date too far ahead).
    # Passing the reason on lets the model read it and react.
    if data.get("error"):
        return {"status": "error", "message": data.get("reason", "Weather service error.")}
    # TODO 1 (continued): the answer looks like {"daily": {"temperature_2m_min": [14.5], ...}}.
    #   Return a SMALL dict: status "ok", city, date, temp_min_c, temp_max_c, rain_chance_pct.
    #   Everything you return goes into the model's context, so leave out what it doesn't need.
    return {"status": "error", "message": "TODO 1: build the result dict"}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    # TODO 3: This docstring is out of date: the code was moved to a new exchange-rate API, but
    #   nobody updated the docs. First run the agent and ask:
    #   "My budget is 1500 lei, how much is that in euros?"
    #   Watch the trace: what does the model pass as from_currency? What does the tool answer?
    #   How many calls does it take? Then fix the docstring so it matches the code, start a new
    #   session and compare.
    """Convert an amount of money from one currency to another.

    Args:
        amount: The amount to convert.
        from_currency: Name of the currency, in lowercase, e.g. "euro", "leu", "dollar".
        to_currency: Name of the currency to convert into, e.g. "euro".
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


# --------------------------------------------------------------------------------------------
# STATE tools: remember the trip across turns, outside the prompt (session state)
# --------------------------------------------------------------------------------------------


def add_to_trip(item_id: str, description: str, price_eur: float, tool_context: ToolContext) -> dict:
    """Add a chosen flight or stay to the user's trip and update the running total.

    Call this only after the user has picked an option.

    Args:
        item_id: The id from search_flights or search_hotels, e.g. "CLJLIS-2026-11-20-0".
        description: Short human-readable label, e.g. "Flight CLJ->LIS, SkyHop, Fri 06:40".
        price_eur: Price of this item in EUR (for a stay: the total for all nights).

    Returns:
        The trip so far and its total cost in EUR.
    """
    # TODO 2: Store the trip in session state, so it survives across turns without being re-sent.
    #   tool_context.state works like a dict that ADK saves with the session.
    #   1. trip = tool_context.state.get("trip", [])          (a list of items)
    #   2. append {"id": ..., "description": ..., "price_eur": ...}
    #   3. assign it back: tool_context.state["trip"] = trip   (so ADK records the change)
    #   4. store the sum in tool_context.state["trip_total_eur"]
    #   5. return {"status": "ok", "trip": trip, "total_eur": ...}
    #   Afterwards: open the "State" tab in adk web and watch it change.
    return {"status": "error", "message": "TODO 2: add_to_trip not implemented yet"}


def get_trip(tool_context: ToolContext) -> dict:
    """Show everything added to the user's trip so far and the total cost in EUR."""
    # TODO 2 (continued): read "trip" and "trip_total_eur" from tool_context.state (use defaults).
    return {"status": "error", "message": "TODO 2: get_trip not implemented yet"}
