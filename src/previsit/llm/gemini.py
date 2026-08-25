"""Google AI Studio (Gemini) free tier - no card required.
https://aistudio.google.com/apikey
"""

from langchain_google_genai import ChatGoogleGenerativeAI

from previsit.config import settings


def build_gemini_model() -> ChatGoogleGenerativeAI:
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey "
            "and set it in .env."
        )
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.gemini_api_key,
        temperature=0,  # deterministic narration of already-deterministic findings
    )
