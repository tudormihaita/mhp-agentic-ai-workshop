# Using DeepSeek via Deploy (default)

The workshop runs on **DeepSeek V4.1 Flash**, served by [Deploy](https://deploy.com) (Hive's AI
platform). You either get a key from the instructor, or you can create your own account: a new account comes
with $1 of free credit, which is enough for the first part of the workshop with normal use.

## Option A: a key from the instructor
Paste it into `.env` (step 3 below) and skip to step 4.

## Option B: your own key
1. Open https://deploy.com/models/deepseek-ai/deepseek-v4.1-flash-1017 and sign up (or log in).
2. In the portal (https://portal.deploy.com), create an **API key** and copy its **Secret Key**.
   It is shown only once: if you lose it, create a new one.
3. In `.env`:
   ```
   MODEL_PROVIDER=deepseek
   DEEPSEEK_API_KEY=<your secret key>
   DEEPSEEK_API_BASE=https://api-cdn.thehive.ai/api/v3
   DEEPSEEK_MODEL=deepseek-ai/deepseek-v4.1-flash-1017
   ```
4. Test it:
   ```bash
   python scripts/check_setup.py
   ```

Your remaining credit and usage are on the **Billing** page of the portal. Keep **auto-recharge off**
if you don't want to be charged beyond the free credit.

Tip: start a **new session** in `adk web` when you change topic. A long chat costs more on every message.

## Troubleshooting
| Error contains | Meaning / fix |
|---|---|
| `DEEPSEEK_API_KEY is not set` | The key is missing from `.env` or still has the `<...>` placeholder |
| `401` / `Authentication` / `invalid` | Wrong key, or a Deploy key sent to `api.deepseek.com`: check `DEEPSEEK_API_BASE` |
| `429` / `Too Many Requests` | Too many requests at once. The agent already retries 3 times; if it still fails, wait a few seconds |
| `402` / `insufficient` / `balance` | Your credit is used up: ask the instructor, or switch provider |
| `404` / `model not found` | Wrong `DEEPSEEK_MODEL`: copy the model name from the Deploy model page |

**Keep your key private.** Don't commit `.env`, and don't paste the key in chats or screenshots.
