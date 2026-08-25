"""Provider abstraction. Switching LLM backends is a `settings.llm_provider`
config change, never a code change - SPEC.md non-negotiable #7.

Returns a LangChain BaseChatModel so graph.py can use LangGraph's normal
`.bind_tools()` / `.with_structured_output()` patterns regardless of which
provider is actually configured - the provider-specific class only appears
inside each llm/<provider>.py module, never in graph.py.
"""

from langchain_core.language_models import BaseChatModel

from previsit.config import settings


def get_chat_model() -> BaseChatModel:
    provider = settings.llm_provider.lower()

    if provider == "gemini":
        from previsit.llm.gemini import build_gemini_model

        return build_gemini_model()

    if provider == "groq":
        from previsit.llm.groq import build_groq_model

        return build_groq_model()

    if provider == "azure_openai":
        from previsit.llm.azure_openai import build_azure_openai_model

        return build_azure_openai_model()

    raise ValueError(
        f"Unknown LLM_PROVIDER {settings.llm_provider!r}. Expected one of: gemini, groq, azure_openai."
    )
