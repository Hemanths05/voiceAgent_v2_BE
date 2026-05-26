"""
STT Provider Factory
Creates STT provider instances based on configuration
"""
from typing import Optional
from app.providers.base.stt_base import STTBase
from app.providers.stt.groq_whisper import GroqWhisperSTT
# from app.providers.stt.openai_whisper import OpenAIWhisperSTT  # TODO: Phase 6
# from app.providers.stt.assemblyai import AssemblyAISTT  # TODO: Phase 6
# from app.providers.stt.deepgram import DeepgramSTT  # TODO: Phase 6
from app.core.exceptions import ProviderNotFoundError, ProviderAPIKeyMissingError
from app.config import get_provider_api_key, get_provider_model
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class STTFactory:
    """
    Factory for creating STT provider instances
    """

    # Registry of available STT providers
    _providers = {
        "groq": GroqWhisperSTT,
        # "openai": OpenAIWhisperSTT,  # TODO: Phase 6
        # "assemblyai": AssemblyAISTT,  # TODO: Phase 6
        # "deepgram": DeepgramSTT,  # TODO: Phase 6
    }

    @classmethod
    def create(
        cls,
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> STTBase:
        """
        Create an STT provider instance

        Args:
            provider_name: Name of the provider (groq, openai, assemblyai, deepgram)
            api_key: API key (if None, will be loaded from config)
            model: Model name (if None, will be loaded from config)
            language: Language code
            **kwargs: Additional provider-specific parameters

        Returns:
            STT provider instance

        Raises:
            ProviderNotFoundError: If provider is not available
            ProviderAPIKeyMissingError: If API key is not configured
        """
        provider_name = provider_name.lower()

        # Check if provider exists
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ProviderNotFoundError(
                "stt",
                provider_name
            )

        # Get API key from config if not provided
        if api_key is None:
            api_key = get_provider_api_key("stt", provider_name)
            if not api_key:
                raise ProviderAPIKeyMissingError("stt", provider_name)

        # Get model from config if not provided
        if model is None:
            model = get_provider_model("stt", provider_name)

        # Get provider class
        provider_class = cls._providers[provider_name]

        # Create instance
        logger.info(
            f"Creating STT provider: {provider_name} "
            f"(model={model}, language={language})"
        )

        try:
            instance = provider_class(
                api_key=api_key,
                model=model,
                language=language,
                **kwargs
            )
            return instance
        except Exception as e:
            logger.error(
                f"Failed to create STT provider {provider_name}: {str(e)}",
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
        Register a new STT provider (for extensibility)

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from STTBase)
        """
        if not issubclass(provider_class, STTBase):
            raise ValueError(f"{provider_class} must inherit from STTBase")

        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered STT provider: {name}")


# Export factory
__all__ = ["STTFactory"]
