"""Exercise 1 - Your first agent: a plain chat agent.

There are no tools yet: this "agent" is just an LLM with instructions.
Goal: see that the model is a replaceable part. The agent definition stays
the same while the model behind it changes (set in .env).

Run it (from the repo root):
    adk web exercises        -> open http://localhost:8000 and pick `ex01_chat`
    adk run exercises/ex01_chat   (terminal chat instead of the browser)
"""

from google.adk.agents import Agent

from common import describe_model, get_model

print(f"[ex01] Using model: {describe_model()}")

root_agent = Agent(
    name="chat_agent",
    model=get_model(),
    # description: a one-line summary for visible to other agents.
    # It explains the agent's role and what it can do.
    description="A simple chat assistant without tools.",
    # TODO 1: Write the agent's instruction (its "system prompt"): how THIS agent behaves.
    #   - Who is it? (e.g. a friendly assistant for travel planning)
    #   - How should it answer? (length, tone, language, format)
    #   - What should it do when it doesn't know something?
    instruction="You are a helpful assistant.",
)
