"""Instructor tool: run an agent with scripted messages and print what happens inside.

Each message is sent in the same session (like typing them one after another in adk web).
Prints every tool call, tool result and model reply: a text version of the trace view.

    python scripts/smoke_test.py solutions/ex02_tools "Flights from CLJ to LIS on 2026-11-20?"
    python scripts/smoke_test.py solutions/ex02_tools "first message" "second message"
    python scripts/smoke_test.py --provider bedrock solutions/ex02_tools "..."
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def short(value, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + " …"


def load_agent(agent_dir: Path):
    sys.path.insert(0, str(agent_dir.parent))  # same as adk web: the agents dir is importable
    return importlib.import_module(f"{agent_dir.name}.agent").root_agent


async def run(root_agent, app_name: str, messages: list[str], pause: float = 0) -> None:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=root_agent, app_name=app_name)
    session = await runner.session_service.create_session(app_name=app_name, user_id="instructor")
    for i, text in enumerate(messages):
        if i and pause:
            await asyncio.sleep(pause)  # stay under free-tier rate limits (Gemini: ~5 requests/min)
        print(f"\n\033[1m>>> USER: {text}\033[0m")
        start = time.time()
        content = types.Content(role="user", parts=[types.Part(text=text)])
        try:
            await print_turn(runner, session.id, content)
        except Exception as e:  # e.g. rate limit: report it and stop instead of dumping a traceback
            print(f"  \033[31mFAILED: {type(e).__name__}: {short(str(e), 300)}\033[0m")
            break
        print(f"  ({time.time() - start:.1f}s)")

    final = await runner.session_service.get_session(app_name=app_name, user_id="instructor", session_id=session.id)
    calls = sum(1 for e in final.events for p in (e.content.parts if e.content and e.content.parts else []) if p.function_call)
    print(f"\n--- {calls} tool calls · final state: {short(dict(final.state), 600)}")
    print_usage()


# Token usage per agent: {author: [model calls, input tokens, largest input, output tokens]}
USAGE: dict[str, list[int]] = {}


def record_usage(event) -> None:
    usage = getattr(event, "usage_metadata", None)
    if not usage or not usage.prompt_token_count:
        return
    row = USAGE.setdefault(event.author, [0, 0, 0, 0])
    row[0] += 1
    row[1] += usage.prompt_token_count
    row[2] = max(row[2], usage.prompt_token_count)
    row[3] += usage.candidates_token_count or 0


def print_usage() -> None:
    if not USAGE:
        return
    print(f"\n{'agent':<20}{'calls':>6}{'input':>10}{'largest':>10}{'output':>9}")
    for author, (n, tokens_in, largest, tokens_out) in USAGE.items():
        print(f"{author:<20}{n:>6}{tokens_in:>10,}{largest:>10,}{tokens_out:>9,}")
    totals = [sum(r[0] for r in USAGE.values()), sum(r[1] for r in USAGE.values()),
              max(r[2] for r in USAGE.values()), sum(r[3] for r in USAGE.values())]
    print(f"{'TOTAL':<20}{totals[0]:>6}{totals[1]:>10,}{totals[2]:>10,}{totals[3]:>9,}")


async def print_turn(runner, session_id: str, content) -> None:
    async for event in runner.run_async(user_id="instructor", session_id=session_id, new_message=content):
        record_usage(event)
        if event.error_code:
            print(f"  [{event.author}] ERROR {event.error_code}: {short(event.error_message or '', 200)}")
        for part in (event.content.parts if event.content and event.content.parts else []):
            if part.function_call:
                print(f"  [{event.author}] CALL   {part.function_call.name}({short(part.function_call.args)})")
            elif part.function_response:
                print(f"  [{event.author}] RESULT {part.function_response.name} -> {short(part.function_response.response)}")
            elif part.text and part.text.strip():
                label = "THOUGHT" if part.thought else "SAYS"
                print(f"  [{event.author}] {label}: {short(part.text.strip(), 1500)}")
        if event.actions and event.actions.transfer_to_agent:
            print(f"  [{event.author}] TRANSFER -> {event.actions.transfer_to_agent}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("agent_dir", type=Path, help="e.g. solutions/ex02_tools")
    parser.add_argument("messages", nargs="+", help="user messages, sent in order in one session")
    parser.add_argument("--provider", choices=["deepseek", "bedrock", "ollama", "gemini"], help="override MODEL_PROVIDER")
    parser.add_argument("--pause", type=float, default=0, help="seconds to wait between messages (rate limits)")
    args = parser.parse_args()
    if args.provider:
        os.environ["MODEL_PROVIDER"] = args.provider
    agent_dir = args.agent_dir.resolve()
    asyncio.run(run(load_agent(agent_dir), agent_dir.name, args.messages, args.pause))


if __name__ == "__main__":
    main()
