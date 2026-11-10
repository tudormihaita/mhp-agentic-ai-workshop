# Agentic AI Workshop: Building LLM-based agents with Google ADK

Hands-on exercises for building LLM-based agents with Google's
[Agent Development Kit (ADK)](https://adk.dev). Each exercise introduces one concept:
chat agents, tools and the agent loop, multi-agent delegation, workflows and MCP.

Every exercise works with any of three model providers. You choose one in a single `.env` file:

| Provider | What it is | What you need |
|---|---|---|
| **Amazon Bedrock** *(default)* | Cloud models (Amazon Nova, Claude, Llama, …) | The personal API key from your instructor |
| **Ollama** *(optional)* | Open models running on your own laptop | Ollama installed + a model downloaded: [guide](docs/setup-ollama.md) |
| **Google Gemini** *(optional)* | Google's cloud models | A free Gemini API key: [guide](docs/setup-gemini.md) |

---

## Setup (≈10 minutes, do it before the workshop)

**Requirements:** Python **3.11 or newer** and `git`. Check with `python --version`
(on macOS/Linux it may be `python3`).

```bash
# 1. Get the code
git clone <REPO_URL> mhp-agentic-ai-workshop
cd mhp-agentic-ai-workshop

# 2. Create and activate a virtual environment
python -m venv .venv
#   macOS / Linux:
source .venv/bin/activate
#   Windows (PowerShell):
.venv\Scripts\Activate.ps1
#   Windows (cmd):
.venv\Scripts\activate.bat

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your config file and fill in your key
cp .env.example .env # Windows: copy .env.example .env
# open .env and paste your Bedrock API key (see docs/setup-bedrock.md)

# 5. Check everything works
python scripts/check_setup.py
```

You should see `All good - you're ready!`. If not, the `[FAIL]` line tells you what to fix.

> **Windows tip:** if PowerShell refuses to activate the venv, run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.
> **Every new terminal:** activate the venv again (step 2) before running anything.

---

## Running the exercises

From the repo root, with the venv active:

```bash
adk web --reload_agents exercises
```

Open **http://localhost:8000** and choose an exercise in the top-left dropdown.
The web UI shows the chat **and** what happens inside the agent (model requests, tool calls, state).
Every folder in `exercises/` is one entry in the dropdown. An exercise's code only runs when you select it.

Other ways to run:
```bash
adk web exercises/ex02_tools      # only one exercise
adk run exercises/ex01_chat       # chat in the terminal instead of the browser
adk web solutions                 # the reference solutions (same dropdown, finished code)
```

With `--reload_agents`, saving `agent.py` is picked up automatically: start a **new session** in
the UI to see the change. After editing `.env`, **restart** `adk web` (Ctrl+C, then run it again).

### Switching models
Edit `.env`. Change `MODEL_PROVIDER` (`bedrock` / `ollama` / `gemini`) or the model name for that
provider (`BEDROCK_MODEL`, `OLLAMA_MODEL`, `GEMINI_MODEL`), then restart. No code changes needed.

---

## Exercises

| # | Folder | Concept |
|---|---|---|
| 1 | [`ex01_chat`](exercises/ex01_chat/README.md) | Chat agent: the LLM is a replaceable part |
| 2 | [`ex02_tools`](exercises/ex02_tools/README.md) | Tools and the agent loop |
| 3 | [`ex03_delegation`](exercises/ex03_delegation/README.md) | Delegation: a coordinator and specialists |
| 4 | [`ex04_workflows`](exercises/ex04_workflows/README.md) | Workflows: sequential and parallel |
| 5 | [`ex05_mcp`](exercises/ex05_mcp/README.md) | MCP: tools from a server |

Each exercise folder has a `README.md` with the steps, and an `agent.py` with `TODO`s.
Reference solutions are in [`solutions/`](solutions). Try first, peek later.

---

## Repository layout

```
mhp-agentic-ai-workshop/
├── README.md               ← you are here
├── requirements.txt        ← pip dependencies
├── pyproject.toml          ← makes common importable (installed via requirements.txt)
├── .env.example            ← copy to .env and fill in (never commit .env)
├── common/                ← shared helper, you do not need to edit it
│   └── models.py           ← get_model(): picks Bedrock / Ollama / Gemini from .env
├── scripts/
│   └── check_setup.py      ← verifies Python, packages, .env and a live model call
├── docs/
│   ├── setup-bedrock.md    ← provider guides + troubleshooting
│   ├── setup-ollama.md
│   ├── setup-gemini.md
│   └── instructor/         ← key generation & cleanup (instructor only)
├── exercises/              ← one folder per exercise = one ADK agent (run: adk web exercises)
│   ├── ex01_chat/
│   │   ├── __init__.py     ← one line: `from . import agent`
│   │   ├── agent.py        ← defines `root_agent` (ADK looks for this name), has the TODOs
│   │   └── README.md       ← concept, steps, example
│   ├── ex02_tools/
│   ├── ex03_delegation/
│   ├── ex04_workflows/
│   └── ex05_mcp/
└── solutions/              ← same structure, completed code
```

## Common problems
| Problem | Fix |
|---|---|
| `ModuleNotFoundError: common` | venv not active, or you skipped `pip install -r requirements.txt` |
| `adk: command not found` | venv not active |
| Exercise missing from the dropdown | Run `adk web exercises` from the **repo root**, not inside a folder |
| Provider-specific errors | See [Bedrock](docs/setup-bedrock.md) · [Ollama](docs/setup-ollama.md) · [Gemini](docs/setup-gemini.md) |
