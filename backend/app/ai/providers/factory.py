from app.core.config import (
    settings,
)

from app.ai.providers.base import (
    AIProvider,
)


def get_ai_provider() -> AIProvider:
    provider = (
        settings.ai_provider
        .strip()
        .lower()
    )

    if provider == "openai":
        from app.ai.providers.openai_provider import (
            OpenAIProvider,
        )

        return OpenAIProvider()

    if provider == "ollama":
        from app.ai.providers.ollama_provider import (
            OllamaProvider,
        )

        return OllamaProvider()

    raise RuntimeError(
        "No AI provider is configured. "
        "Set AI_PROVIDER to openai or ollama."
    )
