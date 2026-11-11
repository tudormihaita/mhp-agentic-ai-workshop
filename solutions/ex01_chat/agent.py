"""Exercise 1 - solution."""

from google.adk.agents import Agent

from common import describe_model, get_model

print(f"[ex01 solution] Using model: {describe_model()}")

root_agent = Agent(
    name="chat_agent",
    model=get_model(),
    description="A simple chat assistant without tools.",
    instruction=(
        "You are a friendly study assistant for second-year Computer Science students.\n"
        "- Answer clearly and concisely; use short code examples when they help.\n"
        "- Prefer Python in examples unless the user asks for another language.\n"
        "- If you are not sure about something, or it depends on recent information "
        "(dates, versions, news, prices), say so explicitly instead of guessing.\n"
        "- Answer in the language the user writes in."
    ),
)
