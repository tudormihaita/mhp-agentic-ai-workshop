"""Exercise 3 - local tools and callbacks.

- add_to_trip / get_trip stay local: they need the ADK session state, which an MCP server
  (a separate process) can't see.
- trim_flight_results shrinks Kiwi's answers before the model sees them.
"""

from __future__ import annotations

from typing import Any

from google.adk.tools import BaseTool, ToolContext

# --------------------------------------------------------------------------------------------
# State tools (same as Exercise 2)
# --------------------------------------------------------------------------------------------


def add_to_trip(item_id: str, description: str, price_eur: float, tool_context: ToolContext) -> dict:
    """Add a chosen flight or stay to the user's trip and update the running total.

    Call this only after the user has picked an option.

    Args:
        item_id: An id or booking link from a search result.
        description: Short human-readable label, e.g. "Return flight CLJ<->LIS, 1 stop".
        price_eur: Price of this item in EUR (for a stay: the total for all nights).

    Returns:
        The trip so far and its total cost in EUR.
    """
    trip = tool_context.state.get("trip", [])
    trip.append({"id": item_id, "description": description, "price_eur": price_eur})
    tool_context.state["trip"] = trip
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

    # TODO 4: Return a much smaller dict instead of Kiwi's full answer.
    #   data["itineraries"] is a list; each item has "price", "priceFormatted", "bookingUrl",
    #   "outbound" and "inbound" (each leg has departureTime, arrivalTime, stops, route, segments).
    #   1. sort the itineraries by "price" and keep the first MAX_FLIGHTS
    #   2. for each, keep: price (use priceFormatted), booking_url, and the two legs via _leg(...)
    #   3. return {"status": "ok", "source": "Kiwi.com (live prices)", "flights": [...]}
    #   Then uncomment after_tool_callback in agent.py and compare the size in the trace.
    return None
