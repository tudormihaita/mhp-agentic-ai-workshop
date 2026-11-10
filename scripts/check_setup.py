"""Checks that your environment is ready for the workshop.

Run from the repo root, with your virtual environment active:
    python scripts/check_setup.py
    python scripts/check_setup.py --provider ollama     # test another provider
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

OK, FAIL, WARN = "[ OK ]", "[FAIL]", "[WARN]"


def step(label: str, status: str, detail: str = "") -> None:
    print(f"{status} {label}" + (f" - {detail}" if detail else ""))


def check_python() -> bool:
    v = sys.version_info
    if v < (3, 11):
        step("Python version", FAIL, f"{v.major}.{v.minor} found, 3.11+ required")
        return False
    step("Python version", OK, f"{v.major}.{v.minor}.{v.micro}")
    return True


def check_imports() -> bool:
    try:
        import google.adk  # noqa: F401
        import litellm  # noqa: F401
        import common  # noqa: F401
    except ImportError as e:
        step("Packages", FAIL, f"{e}. Run: pip install -r requirements.txt")
        return False
    from importlib.metadata import version

    step("Packages", OK, f"google-adk {version('google-adk')}, litellm {version('litellm')}")
    return True


def check_env_file() -> bool:
    from common.models import ENV_FILE

    if not ENV_FILE.exists():
        step(".env file", FAIL, "missing. Copy .env.example to .env and fill it in")
        return False
    step(".env file", OK, str(ENV_FILE))
    return True


async def ask_model(model) -> str:
    from google.adk.agents import Agent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    agent = Agent(name="setup_check", model=model, instruction="Reply with exactly: READY")
    runner = InMemoryRunner(agent=agent, app_name="setup_check")
    session = await runner.session_service.create_session(app_name="setup_check", user_id="student")
    message = types.Content(role="user", parts=[types.Part(text="Are you ready?")])
    reply = ""
    async for event in runner.run_async(user_id="student", session_id=session.id, new_message=message):
        if event.is_final_response() and event.content and event.content.parts:
            reply = "".join(p.text or "" for p in event.content.parts)
    return reply.strip()


HINTS = [
    ("11434", "Ollama isn't running. Start the Ollama app or run `ollama serve` (docs/setup-ollama.md)."),
    ("not found, try pulling", "Download the model first: `ollama pull <OLLAMA_MODEL>`."),
    ("model identifier is invalid", "Wrong BEDROCK_MODEL ID or region prefix (eu./us.) - see docs/setup-bedrock.md."),
    ("API key not valid", "Your GOOGLE_API_KEY is wrong - copy it again from AI Studio."),
    ("RESOURCE_EXHAUSTED", "Gemini free-tier rate limit - wait a minute and retry."),
    ("Throttling", "Too many requests right now - wait a few seconds and retry."),
    ("403", "Access denied - your key may be wrong or expired. Ask the instructor."),
    ("401", "Authentication failed - check the key in your .env file."),
]


def hint_for(error: str) -> str:
    for needle, hint in HINTS:
        if needle.lower() in error.lower():
            return hint
    return "Copy the [FAIL] line above and show it to the instructor."


def check_model(provider: str | None) -> bool:
    from common import ModelConfigError, describe_model, get_model

    try:
        model = get_model(provider)
        label = describe_model(provider)
    except ModelConfigError as e:
        step("Model config", FAIL, str(e))
        return False
    step("Model config", OK, label)

    print("Sending a test message (can take ~30 s the first time with Ollama)...")
    start = time.time()
    try:
        reply = asyncio.run(ask_model(model))
    except Exception as e:
        step("Model call", FAIL, f"{type(e).__name__}: {str(e)[:400]}")
        print(f"       Hint: {hint_for(str(e))}")
        return False
    if not reply:
        step("Model call", WARN, "the model answered with an empty message")
        return True
    step("Model call", OK, f"{time.time() - start:.1f}s, reply: {reply[:80]!r}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", choices=["bedrock", "ollama", "gemini"], help="override MODEL_PROVIDER")
    args = parser.parse_args()

    print("Agentic AI workshop - setup check\n")
    ok = check_python() and check_imports() and check_env_file() and check_model(args.provider)
    print("\nAll good - you're ready!" if ok else "\nSomething needs fixing - see the [FAIL] line above.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
