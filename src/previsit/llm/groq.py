"""Groq free tier - no card required. https://console.groq.com/keys"""

from langchain_groq import ChatGroq

from previsit.config import settings


def build_groq_model() -> ChatGroq:
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys "
            "and set it in .env."
        )
    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0,
    )
