---
name: trip-plan-format
description: Formats the final trip plan for the user. Use when the user asks for the final plan, a summary of the trip, or says they are done planning.
---

# Writing the final trip plan

First call `get_trip` to get the chosen items and the total. Only use prices from tools.

Use exactly this structure:

```markdown
# ✈️ <City> weekend · <dates>

| Item | Details | Price |
|---|---|---|
| Flight | <airline, times> · [book](<booking link>) | €<price> |
| Stay | <name, type, nights> | €<price> |
| **Total** | | **€<total>** |

**Budget:** €<total> of €<budget> · €<left> left for food and transport

**Weather:** <min–max °C, rain chance> → <what to pack, one line>

**Before you go**
- [ ] <2-4 checklist items specific to this trip>
```

## Style
- Friendly and short: a student reads this on their phone.
- Leave out the budget line if the user never gave a budget.
- If something isn't booked yet (no flight or no stay), write "not chosen yet" in the table.
