---
name: find-destination
# TODO 3a: Write the description. It is the ONLY part of this skill the model sees until it loads
#   it, so it must say what the skill does AND when to use it (e.g. which user requests trigger it).
#   Write it in the third person ("Finds ...", not "I can ...").
description: TODO
metadata:
  # TODO 3b: List the tool(s) this skill unlocks: the Skiplagged tool for "flexible destination"
  #   searches. Find its name in the trace (Step 4 in the README), e.g. adk_additional_tools: [tool_name]
  adk_additional_tools: []
---

# Finding a destination

1. You need a departure date and a return date. Ask for them if they are missing.
   The user starts from Cluj (CLJ) unless they say otherwise.
2. Search with `sk_destinations_anywhere`:
   - `from`: the user's airport (CLJ by default). Bucharest (OTP) has more and often cheaper
     flights: if the results are few or expensive, search OTP too and mention the train
     to Bucharest (about 8h).
   - `depart` / `return`: format YYYY-MM-DD.
   - `currency`: EUR.
3. Show the 5 cheapest destinations as a list: city, country, price in EUR.
   Prices are approximate (converted from USD): say so.
4. Ask which one the user likes. Then plan it with your other tools: the exact flight
   (search-flight), a stay (search_hotels) and the weather (get_weather_forecast).
