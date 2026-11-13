"""Exercise 6 - The trip planner as a graph workflow: nodes, edges, routes.

Run it (from the repo root):
    adk web --reload_agents exercises      -> pick `ex06_graph_workflows`

The same pipeline as Exercise 5, as a graph of nodes and edges. Two kinds of nodes:
  - LLM nodes (Agent): where language is needed (parse, research, plan, present)
  - function nodes (plain Python): rules and arithmetic, no LLM, free and always correct

    START → parse_request → validate_request ──invalid──→ explain_problem
                                  │ ok
                    ┌─────────────┼─────────────┐
               flight_scout   stay_scout   weather_scout
                    └─────────────┼─────────────┘
                               research (JoinNode)
                                  ↓
                               planner ←──over──┐
                                  ↓             │
                             check_budget ──────┘
                                  │ fits / give_up
                               presenter
"""

import re
from datetime import date

from google.adk import Event, Workflow
from google.adk.agents import Agent
from google.adk.workflow import START, JoinNode
from pydantic import BaseModel, Field

from common import get_model
from common.travel import (
    AIRPORTS, HOTELS, ROUTES, convert_currency, get_weather_forecast, search_flights, search_hotels,
)

TODAY = date.today()
MAX_ROUNDS = 3  # a graph has no built-in loop limit: we add our own


class TripRequest(BaseModel):
    origin: str = Field(description="Only the 3-letter IATA code of the departure airport, e.g. CLJ. CLJ if not given.")
    destination: str = Field(description="Only the 3-letter IATA code of the destination airport, e.g. LIS.")
    city: str = Field(description="The city the user travels TO (not from), in English, e.g. Lisbon.")
    depart: str = Field(description="Departure date, YYYY-MM-DD.")
    return_date: str = Field(description="Return date, YYYY-MM-DD.")
    budget_amount: float = Field(description="The user's total budget. 0 if not given.")
    budget_currency: str = Field(description="Only the 3-letter ISO code of the budget currency, e.g. RON for lei.")


class TripPlan(BaseModel):
    outbound_flight_id: str = Field(description="id of the chosen outbound flight, from the flight list.")
    return_flight_id: str = Field(description="id of the chosen return flight, from the flight list.")
    stay_id: str = Field(description="id of the chosen stay, from the stays list.")
    why: str = Field(description="One sentence: why these choices.")


# --------------------------------------------------------------------------------------------
# LLM node: free text -> TripRequest
# --------------------------------------------------------------------------------------------

parse_request = Agent(
    name="parse_request",
    model=get_model(),
    instruction=(
        f"Extract the trip request from the user's message. Today is {TODAY.isoformat()}. "
        f"Known airports: {', '.join(f'{code} ({city})' for code, city in AIRPORTS.items())}."
    ),
    output_schema=TripRequest,
    output_key="request",
)


# --------------------------------------------------------------------------------------------
# Function node: check the request with plain rules, then ROUTE
# --------------------------------------------------------------------------------------------


def _airport_code(value: str) -> str:
    """Forgive small format slips: "Cluj-Napoca (CLJ)" or "Cluj-Napoca" -> "CLJ"."""
    for code, city in AIRPORTS.items():
        if code in value.upper() or city.lower() in value.lower():
            return code
    return value


def _iso_date(value: str) -> str:
    """Forgive extra text around the date: "2026-11-20 (Friday)" -> "2026-11-20"."""
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    return match.group() if match else value


def validate_request(request: TripRequest) -> Event:
    """Parameters are filled from session state by name: here state["request"]."""
    request.origin, request.destination = _airport_code(request.origin), _airport_code(request.destination)
    request.city = AIRPORTS.get(request.destination, request.city)  # trust the code, not the model
    request.depart, request.return_date = _iso_date(request.depart), _iso_date(request.return_date)
    problems = []
    if request.origin not in AIRPORTS or request.destination not in AIRPORTS:
        problems.append(f"I only know these airports: {', '.join(AIRPORTS)}.")
    elif (request.origin, request.destination) not in ROUTES and (request.destination, request.origin) not in ROUTES:
        problems.append(f"There are no flights between {request.origin} and {request.destination}.")
    if request.city.title() not in HOTELS:
        problems.append(f"I have no stays in {request.city}. Try: {', '.join(HOTELS)}.")
    try:
        depart, back = date.fromisoformat(request.depart), date.fromisoformat(request.return_date)
        if depart < TODAY or back <= depart:
            problems.append("The dates must be in the future, and the return after the departure.")
    except ValueError:
        problems.append("I couldn't understand the dates.")
    if request.budget_amount:
        currency = request.budget_currency.upper()
        request.budget_currency = "RON" if "LEI" in currency or "RON" in currency else currency[:3]
        if convert_currency(1, request.budget_currency, "EUR")["status"] != "ok":
            problems.append(f"I don't know the currency '{request.budget_currency}'.")

    if problems:
        return Event(route="invalid", state={"problems": problems})
    # Save the cleaned-up request. State lives for the whole session, so also reset what the
    # previous request left behind: the loop counter and the last budget check.
    return Event(route="ok", state={"request": request.model_dump(), "rounds": 0, "budget_check": ""})


def explain_problem(problems: list[str]) -> Event:
    """No LLM needed to say what's wrong: the rules already know."""
    return Event(message="I can't plan this trip yet:\n" + "\n".join(f"- {p}" for p in problems))


# --------------------------------------------------------------------------------------------
# LLM nodes: research, run in parallel (fan-out), collected by a JoinNode (fan-in)
# --------------------------------------------------------------------------------------------

flight_scout = Agent(
    name="flight_scout",
    model=get_model(),
    instruction=(
        "Trip request: {request}\nSearch the outbound flight (origin -> destination on depart) and the "
        "return flight (destination -> origin on return_date). List all offers with id, airline, time, price."
    ),
    tools=[search_flights],
    output_key="flights",
)

stay_scout = Agent(
    name="stay_scout",
    model=get_model(),
    instruction=(
        "Trip request: {request}\nSearch stays in the city for the nights between depart and return_date. "
        "List all of them with id, name, type, rating and total price."
    ),
    tools=[search_hotels],
    output_key="stays",
)

weather_scout = Agent(
    name="weather_scout",
    model=get_model(),
    instruction=(
        "Trip request: {request}\nGet the forecast in the city for the depart and return dates. "
        "Summarise it in one line. If it isn't available yet, say so."
    ),
    tools=[get_weather_forecast],
    output_key="weather",
)

research = JoinNode(name="research")  # waits for all three scouts

# --------------------------------------------------------------------------------------------
# The budget loop: an LLM plans, CODE checks
# --------------------------------------------------------------------------------------------

planner = Agent(
    name="planner",
    model=get_model(),
    instruction=(
        "Trip request: {request}\n\nFlights:\n{flights}\n\nStays:\n{stays}\n\n"
        "Budget check of your previous plan (empty on the first round): {budget_check?}\n\n"
        "Choose one outbound flight, one return flight and one stay for the most comfortable weekend: a "
        "good rating and convenient times, not the cheapest. Don't check the budget yourself: code does "
        "that. If there is a budget check that says you're over, follow it."
    ),
    output_schema=TripPlan,
    output_key="plan",
)


def _flight_price(flight_id: str) -> float:
    origin, destination, day = flight_id[:3], flight_id[3:6], flight_id[7:17]  # e.g. CLJBCN-2026-11-20-2
    offers = search_flights(origin, destination, day).get("flights", [])
    return next(o["price_eur"] for o in offers if o["id"] == flight_id)


def _stay_price(request: TripRequest, stay_id: str) -> float:
    nights = (date.fromisoformat(request.return_date) - date.fromisoformat(request.depart)).days
    stay = next(s for s in HOTELS[request.city.title()] if s["id"] == stay_id)
    return stay["price_per_night"] * nights


def check_budget(request: TripRequest, plan: TripPlan, rounds: int = 0) -> Event:
    """Recompute the total from the real prices: the planner's word is not trusted."""
    total = _flight_price(plan.outbound_flight_id) + _flight_price(plan.return_flight_id)
    total += _stay_price(request, plan.stay_id)
    budget = request.budget_amount
    if budget and request.budget_currency.upper() != "EUR":
        budget = convert_currency(budget, request.budget_currency, "EUR")["amount"]
    rounds += 1

    # TODO 2: Decide the verdict with plain Python. It becomes the ROUTE (see the edges at the bottom):
    #   - "fits"    if there is no budget (0) or the total is within it
    #   - "give_up" if it's over budget and we already tried MAX_ROUNDS times
    #   - "over"    otherwise
    verdict = "fits"
    check = {"total_eur": total, "budget_eur": budget, "verdict": verdict,
             "note": f"Over by {total - budget:.2f} EUR: choose cheaper items." if verdict == "over" else ""}
    return Event(route=verdict, state={"budget_check": check, "rounds": rounds})


# --------------------------------------------------------------------------------------------
# LLM node: present
# --------------------------------------------------------------------------------------------

presenter = Agent(
    name="presenter",
    model=get_model(),
    instruction=(
        "Trip request: {request}\nPlan (ids): {plan}\nFlights: {flights}\nStays: {stays}\n"
        "Weather: {weather}\nBudget check (computed by code, trust these numbers): {budget_check}\n\n"
        "Write the final plan for the student: a short table (outbound, return, stay, total in EUR), the "
        "weather in one line, and the budget. If the verdict is give_up, say honestly that no option "
        "fits the budget and show the cheapest plan found."
    ),
)

# --------------------------------------------------------------------------------------------
# The graph
# --------------------------------------------------------------------------------------------

root_agent = Workflow(
    name="trip_graph",
    edges=[
        (START, parse_request, validate_request),
        # TODO 1: validate_request can also return the route "invalid". Map it to explain_problem.
        (validate_request, {"ok": (flight_scout, stay_scout, weather_scout)}),
        ((flight_scout, stay_scout, weather_scout), research, planner, check_budget),
        # TODO 3: After TODO 2, check_budget can return "over". Send it back to the planner:
        #   that edge makes the loop. (What stops the loop from running forever?)
        (check_budget, {"fits": presenter, "give_up": presenter}),
    ],
)
