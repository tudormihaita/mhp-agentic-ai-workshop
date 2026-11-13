"""Exercise 5 - The trip planner as a classic workflow: your code decides the order.

Run it (from the repo root):
    adk web --reload_agents exercises      -> pick `ex05_workflows`

Your code fixes the order; agents pass data to each other ONLY through session state
(include_contents="none": a step doesn't see the chat, only the {placeholders} in its instruction):

    trip_pipeline (SequentialAgent)
    ├── request_parser          -> state["request"]   (structured output: TripRequest)
    ├── research (ParallelAgent)
    │   ├── flight_scout        -> state["flights"]
    │   ├── stay_scout          -> state["stays"]
    │   └── weather_scout       -> state["weather"]
    ├── budget_loop (LoopAgent, max 3 rounds)
    │   ├── planner             -> state["plan"]      (structured output: TripPlan)
    │   └── budget_checker      -> state["review"], or calls exit_loop when the plan fits
    └── presenter               -> the answer the user sees
"""

from datetime import date

from google.adk.agents import Agent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import exit_loop  # noqa: F401  (used in TODO 3)
from pydantic import BaseModel, Field

from common import get_model
from common.travel import AIRPORTS, convert_currency, get_weather_forecast, search_flights, search_hotels

TODAY = date.today().isoformat()

def reset_state(callback_context: CallbackContext) -> None:
    """Runs before the pipeline. State lives for the whole session: forget the last request's review,
    so the planner's first round doesn't follow advice about a different budget."""
    callback_context.state["review"] = ""

# --------------------------------------------------------------------------------------------
# Structured outputs: the "contract" between steps
# --------------------------------------------------------------------------------------------


class TripRequest(BaseModel):
    origin: str = Field(description="IATA code of the departure airport, e.g. CLJ. CLJ if not given.")
    destination: str = Field(description="IATA code of the destination airport, e.g. LIS.")
    city: str = Field(description="The city the user travels TO (not from), in English, e.g. Lisbon.")
    depart: str = Field(description="Departure date, YYYY-MM-DD.")
    return_date: str = Field(description="Return date, YYYY-MM-DD.")
    # TODO 1: The budget is missing from the request, so no later step can know it.
    #   Add two fields, like the ones above:
    #   - budget_amount: a float, "The user's total budget. 0 if not given."
    #   - budget_currency: a str, "3-letter ISO code of the budget currency, e.g. RON, EUR."
    #   The Field descriptions are instructions for the model, like a tool's docstring.


class TripPlan(BaseModel):
    outbound_flight: str = Field(description="Chosen outbound flight: id, airline, time, price.")
    return_flight: str = Field(description="Chosen return flight: id, airline, time, price.")
    stay: str = Field(description="Chosen stay: name, type, nights, total price.")
    total_eur: float = Field(description="Flights + stay, in EUR.")
    why: str = Field(description="One sentence: why these choices.")


# --------------------------------------------------------------------------------------------
# 1. Understand the request (no tools: only turns free text into a TripRequest)
# --------------------------------------------------------------------------------------------

request_parser = Agent(
    name="request_parser",
    model=get_model(),
    instruction=(
        f"Extract the trip request from the user's message. Today is {TODAY}. "
        f"Known airports: {', '.join(f'{code} ({city})' for code, city in AIRPORTS.items())}."
    ),
    output_schema=TripRequest,
    output_key="request",  # the result is saved in session state under this key
)

# --------------------------------------------------------------------------------------------
# 2. Research: three independent lookups, run at the same time
# --------------------------------------------------------------------------------------------

flight_scout = Agent(
    name="flight_scout",
    model=get_model(),
    include_contents="none",  # sees only what its instruction injects from state, not the chat
    instruction=(
        "Trip request: {request}\n"
        "Search the outbound flight (origin -> destination on depart) and the return flight "
        "(destination -> origin on return_date). List all offers briefly with id, airline, time and price."
    ),
    tools=[search_flights],
    output_key="flights",
)

stay_scout = Agent(
    name="stay_scout",
    model=get_model(),
    include_contents="none",  # sees only what its instruction injects from state, not the chat
    instruction=(
        "Trip request: {request}\n"
        "Search stays in the city for the number of nights between depart and return_date. "
        "List all of them briefly with id, name, type, rating and total price."
    ),
    tools=[search_hotels],
    output_key="stays",
)

weather_scout = Agent(
    name="weather_scout",
    model=get_model(),
    include_contents="none",  # sees only what its instruction injects from state, not the chat
    instruction=(
        "Trip request: {request}\n"
        "Get the forecast in the city for the depart date and the return date. "
        "Summarise it in one line. If it isn't available yet, say so."
    ),
    tools=[get_weather_forecast],
    output_key="weather",
)

# TODO 2: The three scouts don't depend on each other, but they run one after another.
#   Run them at the same time: use ParallelAgent instead of SequentialAgent. Compare the timing
#   in the Trace tab before and after.
research = SequentialAgent(name="research", sub_agents=[flight_scout, stay_scout, weather_scout])

# --------------------------------------------------------------------------------------------
# 3. Plan, check the budget, re-plan if needed (evaluator-optimizer)
# --------------------------------------------------------------------------------------------

planner = Agent(
    name="planner",
    model=get_model(),
    include_contents="none",  # sees only what its instruction injects from state, not the chat
    instruction=(
        "Trip request: {request}\n\nFlights:\n{flights}\n\nStays:\n{stays}\n\n"
        "Budget review of your previous plan (empty on the first round): {review?}\n\n"
        "Choose one outbound flight, one return flight and one stay for the most comfortable weekend: "
        "a good rating and convenient times, not the cheapest. Don't check the budget yourself: the "
        "budget checker does that. If there is a budget review, follow it."
    ),
    output_schema=TripPlan,
    output_key="plan",
)

budget_checker = Agent(
    name="budget_checker",
    model=get_model(),
    include_contents="none",  # sees only what its instruction injects from state, not the chat
    instruction=(
        "Trip request: {request}\n\nPlan: {plan}\n\n"
        "Check the plan's total_eur against the budget. If budget_currency isn't EUR, convert the budget "
        "with convert_currency first. If the budget is 0 or the plan fits, call exit_loop. Otherwise say "
        "by how much it is over and which item to replace with a cheaper option."
    ),
    # TODO 3: The checker is told to "call exit_loop", but it doesn't have that tool: the loop always
    #   runs until max_iterations. Give it the exit_loop tool.
    tools=[convert_currency],
    output_key="review",
)

# max_iterations is the safety net: without it, a plan that can never fit would loop forever.
budget_loop = LoopAgent(name="budget_loop", sub_agents=[planner, budget_checker], max_iterations=3)

# --------------------------------------------------------------------------------------------
# 4. Present the result
# --------------------------------------------------------------------------------------------

presenter = Agent(
    name="presenter",
    model=get_model(),
    include_contents="none",  # sees only what its instruction injects from state, not the chat
    instruction=(
        "Trip request: {request}\n\nPlan: {plan}\n\nWeather: {weather}\n\n"
        "Write the final trip plan for the student: a short table (outbound, return, stay, total in EUR), "
        "the weather in one line, and how much of the budget is left. Friendly and short."
    ),
)

root_agent = SequentialAgent(
    name="trip_pipeline",
    description="Plans a weekend trip in fixed steps: understand, research, plan within budget, present.",
    sub_agents=[request_parser, research, budget_loop, presenter],
    before_agent_callback=reset_state,
)
