"""
LLM Provider Factory
Creates LLM provider instances based on configuration
"""
from typing import Optional
from app.providers.base.llm_base import LLMBase
from app.providers.llm.groq import GroqLLM
# from app.providers.llm.openai import OpenAILLM  # TODO: Phase 7
# from app.providers.llm.anthropic import AnthropicLLM  # TODO: Phase 7
# from app.providers.llm.google_gemini import GoogleGeminiLLM  # TODO: Phase 7
from app.core.exceptions import ProviderNotFoundError, ProviderAPIKeyMissingError
from app.config import get_provider_api_key, get_provider_model
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class LLMFactory:
    """
    Factory for creating LLM provider instances
    """

    # Registry of available LLM providers
    _providers = {
        "groq": GroqLLM,
        # "openai": OpenAILLM,  # TODO: Phase 7
        # "anthropic": AnthropicLLM,  # TODO: Phase 7
        # "gemini": GoogleGeminiLLM,  # TODO: Phase 7
    }

    @classmethod
    def create(
        cls,
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 150,
        top_p: float = 1.0,
        **kwargs
    ) -> LLMBase:
        """
        Create an LLM provider instance

        Args:
            provider_name: Name of the provider (groq, openai, anthropic, gemini)
            api_key: API key (if None, will be loaded from config)
            model: Model name (if None, will be loaded from config)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional provider-specific parameters

        Returns:
            LLM provider instance

        Raises:
            ProviderNotFoundError: If provider is not available
            ProviderAPIKeyMissingError: If API key is not configured
        """
        provider_name = provider_name.lower()

        # Check if provider exists
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ProviderNotFoundError("llm", provider_name)

        # Get API key from config if not provided
        if api_key is None:
            api_key = get_provider_api_key("llm", provider_name)
            if not api_key:
                raise ProviderAPIKeyMissingError("llm", provider_name)

        # Get model from config if not provided
        if model is None:
            model = get_provider_model("llm", provider_name)

        # Get provider class
        provider_class = cls._providers[provider_name]

        # Create instance
        logger.info(
            f"Creating LLM provider: {provider_name} "
            f"(model={model}, temperature={temperature}, max_tokens={max_tokens})"
        )

        try:
            instance = provider_class(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                **kwargs
            )
            return instance
        except Exception as e:
            logger.error(
                f"Failed to create LLM provider {provider_name}: {str(e)}",
                exc_info=True
            )
            raise

    @classmethod
    def get_available_providers(cls) -> list:
        """
        Get list of available provider names

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        Register a new LLM provider (for extensibility)

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from LLMBase)
        """
        if not issubclass(provider_class, LLMBase):
            raise ValueError(f"{provider_class} must inherit from LLMBase")

        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered LLM provider: {name}")


# Export factory
__all__ = ["LLMFactory"]
