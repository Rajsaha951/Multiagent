"""The chat model shared by every agent and chain."""
import os

from langchain_openai import ChatOpenAI


def get_model() -> ChatOpenAI:
    """Works with OpenAI by default. For another OpenAI-compatible provider (e.g. Gemini),
    set OPENAI_BASE_URL, OPENAI_API_KEY and MODEL_NAME in .env."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file and restart.")
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        temperature=0,
        api_key=key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
