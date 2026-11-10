"""Utils for setting up the LLM model configuration for an agent.
Usage in any agent.py:
    from common import get_model
    root_agent = Agent(name="my_agent", model=get_model(), ...)
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env"

load_dotenv(ENV_FILE, override=False)

PROVIDERS = ("bedrock", "ollama", "gemini")

DEFAULT_MODELS = {
    "bedrock": "eu.anthropic.claude-sonnet-5-5",
    "ollama": "qwen3:4b",
    "gemini": "gemini-2.5-flash",
}


class ModelConfigError(RuntimeError):
    """Raised when the .env configuration is missing something. The message says how to fix it."""


def _require(var: str, hint: str) -> str:
    value = os.getenv(var, "").strip()
    if not value or value.startswith("<"):
        raise ModelConfigError(f"{var} is not set in your .env file. {hint}")
    return value


def current_provider() -> str:
    provider = os.getenv("MODEL_PROVIDER", "bedrock").strip().lower()
    if provider not in PROVIDERS:
        raise ModelConfigError(
            f"MODEL_PROVIDER='{provider}' is not valid. Use one of: {', '.join(PROVIDERS)}."
        )
    return provider


def current_model_name(provider: str | None = None) -> str:
    provider = provider or current_provider()
    return os.getenv(f"{provider.upper()}_MODEL", "").strip() or DEFAULT_MODELS[provider]


def get_model(provider: str | None = None, model_name: str | None = None):
    """Return something you can pass as `model=` to an ADK agent.

    - gemini  -> a plain model-name string (ADK talks to Gemini natively)
    - bedrock -> LiteLlm wrapper, authenticated with a Bedrock API key
    - ollama  -> LiteLlm wrapper, pointing at your local Ollama server
    """
    provider = (provider or current_provider()).lower()
    model_name = model_name or current_model_name(provider)

    if provider == "gemini":
        _require("GOOGLE_API_KEY", "Get a free key at https://aistudio.google.com/apikey (see docs/setup-gemini.md).")
        # Use the Gemini Developer API (API key), not Vertex AI
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
        return model_name

    from google.adk.models.lite_llm import LiteLlm

    if provider == "bedrock":
        _require("AWS_BEARER_TOKEN_BEDROCK", "Paste the Bedrock API key you received (see docs/setup-bedrock.md).")
        region = os.getenv("AWS_REGION", "eu-west-1")
        model = model_name if model_name.startswith("bedrock/") else f"bedrock/{model_name}"
        # LiteLLM reads AWS_BEARER_TOKEN_BEDROCK from the environment: no AWS account/CLI needed
        return LiteLlm(model=model, aws_region_name=region)

    if provider == "ollama":
        api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        model = model_name if model_name.startswith("ollama") else f"ollama_chat/{model_name}"
        return LiteLlm(model=model, api_base=api_base)

    raise ModelConfigError(f"Unknown provider '{provider}'. Use one of: {', '.join(PROVIDERS)}.")


def describe_model(provider: str | None = None, model_name: str | None = None) -> str:
    """Human-readable label, e.g. 'bedrock / eu.anthropic.claude-sonnet-5-5'."""
    provider = (provider or current_provider()).lower()
    return f"{provider} / {model_name or current_model_name(provider)}"
