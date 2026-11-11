---
name: find-destination
description: Finds the cheapest places to fly to when the user has no destination in mind. Use when the user asks "where can I go?", wants ideas for a cheap weekend, or only knows their dates and budget.
metadata:
  adk_additional_tools: [sk_destinations_anywhere]
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
