"""Model configuration for the Ammu Assignment Review System.

Centralised here so review stages never construct or configure a chat model
directly -- this is the one place model/provider choice changes.

Configuration comes entirely from the environment, not from code:

- ``OPENAI_API_KEY`` -- required, read automatically by ``ChatOpenAI``.
- ``AMMU_MODEL_NAME`` -- optional, overrides the default model.
- ``LANGSMITH_TRACING`` / ``LANGSMITH_API_KEY`` / ``LANGSMITH_PROJECT`` --
  optional standard LangSmith variables. If set, LangChain traces every run
  automatically; nothing in this codebase needs to know LangSmith exists.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

DEFAULT_MODEL_NAME = "gpt-4o-mini"


def get_model() -> ChatOpenAI:
    """Build the chat model used by review stages."""
    return ChatOpenAI(
        model=os.getenv("AMMU_MODEL_NAME", DEFAULT_MODEL_NAME),
        temperature=0,
    )


def is_openai_api_key_configured() -> bool:
    """Presence check only, not a validity check -- confirming the key is
    genuinely valid would require a real API call, which this deliberately
    avoids. Lets the UI fail fast with a safe, generic message instead of a
    raw construction error surfacing from deep inside ChatOpenAI."""
    return bool(os.getenv("OPENAI_API_KEY"))
