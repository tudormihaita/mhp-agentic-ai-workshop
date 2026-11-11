# Using Google Gemini (optional)

> **A Google AI subscription (Plus / Pro / Ultra) does not give you API access.** Those plans cover the
> Gemini app and the AI Studio web UI. Code (like ADK) needs a **Gemini API key**, which has a
> **free tier** that needs no credit card. That's enough for this workshop.

1. Go to https://aistudio.google.com/apikey and sign in with your Google account.
2. Click **Create API key** (let it create a new project if asked) and copy the key (starts with `AIza`).
3. In `.env`:
   ```
   MODEL_PROVIDER=gemini
   GOOGLE_API_KEY=<your key>
   GEMINI_MODEL=gemini-3.5-flash
   ```
4. Test: `python scripts/check_setup.py`

Model names change over time: the current list is in AI Studio's model picker. Flash models are fast
and have the most generous free-tier limits.

## Troubleshooting
| Error contains | Fix |
|---|---|
| `API key not valid` | Re-copy the key; no quotes or spaces in `.env` |
| `429` / `RESOURCE_EXHAUSTED` | Free-tier rate limit hit: wait a minute or use a Flash/Flash-Lite model |
| `404 ... model not found` | Model name is wrong or retired: check AI Studio for current names |
| Errors mentioning Vertex / project / credentials | Make sure `GOOGLE_GENAI_USE_VERTEXAI` isn't set to TRUE in your terminal |
