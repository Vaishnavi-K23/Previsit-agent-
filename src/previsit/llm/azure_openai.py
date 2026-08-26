"""Azure OpenAI provider - implemented but not used by default. Exists to
prove the swappable-provider claim: switching to it is setting
LLM_PROVIDER=azure_openai plus the four AZURE_OPENAI_* variables in .env,
never a code change. Requires an actual Azure subscription - per this
project's zero-paid-services rule, this is never selected without you
explicitly choosing to pay for Azure.
"""

from langchain_openai import AzureChatOpenAI

from previsit.config import settings


def build_azure_openai_model() -> AzureChatOpenAI:
    if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
        raise RuntimeError(
            "Azure OpenAI is not configured. Set AZURE_OPENAI_API_KEY, "
            "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, and "
            "AZURE_OPENAI_API_VERSION in .env - note this requires an Azure "
            "subscription and will incur cost."
        )
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        azure_deployment=settings.azure_openai_deployment,
        api_version=settings.azure_openai_api_version,
        temperature=0,
    )
