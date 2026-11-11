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

PROVIDERS = ("deepseek", "bedrock", "ollama", "gemini")

DEFAULT_MODELS = {
    "deepseek": "deepseek-ai/deepseek-v4.1-flash-1017",
    "bedrock": "eu.anthropic.claude-sonnet-5-5",
    "ollama": "qwen3:4b",
    "gemini": "gemini-2.5-flash",
}

# DeepSeek models served by Deploy (Hive's platform, portal.deploy.com): an OpenAI-compatible API.
# For a key from DeepSeek itself (platform.deepseek.com), set DEEPSEEK_API_BASE=https://api.deepseek.com
# and DEEPSEEK_MODEL=deepseek-flash.
DEFAULT_DEEPSEEK_API_BASE = "https://api-cdn.thehive.ai/api/v3"

# A cloud API rejects requests above its limit with "429 Too Many Requests" (e.g. Deploy allows only
# ~5 requests in flight at once). LiteLLM then waits and retries, so the agent just answers a bit later.
NUM_RETRIES = 3


class ModelConfigError(RuntimeError):
    """Raised when the .env configuration is missing something. The message says how to fix it."""


def _require(var: str, hint: str) -> str:
    value = os.getenv(var, "").strip()
    if not value or value.startswith("<"):
        raise ModelConfigError(f"{var} is not set in your .env file. {hint}")
    return value


def current_provider() -> str:
    provider = os.getenv("MODEL_PROVIDER", "deepseek").strip().lower()
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

    - deepseek -> LiteLlm wrapper, authenticated with a DeepSeek API key (from Deploy by default)
    - bedrock  -> LiteLlm wrapper, authenticated with a Bedrock API key
    - ollama   -> LiteLlm wrapper, pointing at your local Ollama server
    - gemini   -> a plain model-name string (ADK talks to Gemini natively)
    """
    provider = (provider or current_provider()).lower()
    model_name = model_name or current_model_name(provider)

    if provider == "gemini":
        _require("GOOGLE_API_KEY", "Get a free key at https://aistudio.google.com/apikey (see docs/setup-gemini.md).")
        # Use the Gemini Developer API (API key), not Vertex AI
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
        return model_name

    import litellm
    from google.adk.models.lite_llm import LiteLlm

    # Without this, LiteLLM prints a "Give Feedback / Get Help" banner on every failed attempt
    litellm.suppress_debug_info = True

    if provider == "deepseek":
        _require("DEEPSEEK_API_KEY", "Create your key on Deploy (see docs/setup-deepseek.md).")
        api_base = os.getenv("DEEPSEEK_API_BASE", "").strip() or DEFAULT_DEEPSEEK_API_BASE
        model = model_name if model_name.startswith("deepseek/") else f"deepseek/{model_name}"
        # LiteLLM reads DEEPSEEK_API_KEY from the environment
        return LiteLlm(model=model, api_base=api_base, num_retries=NUM_RETRIES)

    if provider == "bedrock":
        _require("AWS_BEARER_TOKEN_BEDROCK", "Paste the Bedrock API key you received (see docs/setup-bedrock.md).")
        region = os.getenv("AWS_REGION", "eu-west-1")
        model = model_name if model_name.startswith("bedrock/") else f"bedrock/{model_name}"
        # LiteLLM reads AWS_BEARER_TOKEN_BEDROCK from the environment: no AWS account/CLI needed
        return LiteLlm(model=model, aws_region_name=region, num_retries=NUM_RETRIES)

    if provider == "ollama":
        api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
        model = model_name if model_name.startswith("ollama") else f"ollama_chat/{model_name}"
        return LiteLlm(model=model, api_base=api_base)

    raise ModelConfigError(f"Unknown provider '{provider}'. Use one of: {', '.join(PROVIDERS)}.")


def describe_model(provider: str | None = None, model_name: str | None = None) -> str:
    """Human-readable label, e.g. 'deepseek / deepseek-ai/deepseek-v4.1-flash-1017'."""
    provider = (provider or current_provider()).lower()
    return f"{provider} / {model_name or current_model_name(provider)}"
