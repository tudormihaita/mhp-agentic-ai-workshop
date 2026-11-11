"""Finished travel tools, shared by Exercises 4-6 (the same code you wrote in Exercises 2 and 3).

  - DEMO:  search_flights, search_hotels (fake data, deterministic prices)
  - LIVE:  get_weather_forecast (Open-Meteo), convert_currency (ECB rates via Frankfurter)
  - STATE: add_to_trip, get_trip (session state)
  - trim_flight_results: after_tool_callback that shrinks Kiwi's search-flight answers

Tools return small dicts; on failure {"status": "error", "message": ...} so the model can react.
"""

from __future__ import annotations

import hashlib
from datetime import date as Date

import httpx
from typing import Any

from google.adk.tools import BaseTool, ToolContext

HTTP_TIMEOUT = 10.0
USER_AGENT = {"User-Agent": "agentic-ai-workshop/1.0"}

# --------------------------------------------------------------------------------------------
# Demo data; Prices in EUR.
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
    trip = tool_context.state.get("trip", [])
    trip.append({"id": item_id, "description": description, "price_eur": price_eur})
    tool_context.state["trip"] = trip  # assign back so ADK records the change
    tool_context.state["trip_total_eur"] = round(sum(i["price_eur"] for i in trip), 2)
    return {"status": "ok", "trip": trip, "total_eur": tool_context.state["trip_total_eur"]}


def get_trip(tool_context: ToolContext) -> dict:
    """Show everything added to the user's trip so far and the total cost in EUR."""
    return {
        "status": "ok",
        "trip": tool_context.state.get("trip", []),
        "total_eur": tool_context.state.get("trip_total_eur", 0),
    }


# --------------------------------------------------------------------------------------------
# Context management: trim a third-party tool's answer
# --------------------------------------------------------------------------------------------

MAX_FLIGHTS = 3


def _leg(leg: dict | None) -> dict | None:
    if not leg:
        return None
    return {
        "departure": leg.get("departureTime"),
        "arrival": leg.get("arrivalTime"),
        "stops": leg.get("stops"),
        "route": " -> ".join(leg.get("route", [])),
    }


def trim_flight_results(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: Any
) -> dict | None:
    """after_tool_callback: runs after EVERY tool call, before the result goes to the model.

    Return None to keep the original result, or a dict to replace it.
    Kiwi's search-flight returns ~15 itineraries with every segment (~25,000 tokens). That would be
    re-sent to the model on every later call. We keep only the cheapest few, with the useful fields.
    """
    if tool.name != "search-flight" or not isinstance(tool_response, dict):
        return None
    data = tool_response.get("structuredContent")
    if not isinstance(data, dict) or "itineraries" not in data:
        return None  # an error or an unexpected shape: let the model see the original
    cheapest = sorted(data["itineraries"], key=lambda i: i.get("price", float("inf")))[:MAX_FLIGHTS]
    return {
        "status": "ok",
        "source": "Kiwi.com (live prices)",
        "query": data.get("query"),
        "results_found": data.get("resultsCount"),
        "showing": f"cheapest {len(cheapest)}",
        "flights": [
            {
                "price": i.get("priceFormatted") or i.get("price"),
                "booking_url": i.get("bookingUrl"),
                "outbound": _leg(i.get("outbound")),
                "inbound": _leg(i.get("inbound")),
            }
            for i in cheapest
        ],
    }
