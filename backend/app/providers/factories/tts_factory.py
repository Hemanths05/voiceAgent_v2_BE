"""
TTS Provider Factory
Creates TTS provider instances based on configuration
"""
from typing import Optional
from app.providers.base.tts_base import TTSBase
from app.providers.tts.elevenlabs import ElevenLabsTTS
from app.providers.tts.google_tts import GoogleTTS
# from app.providers.tts.openai_tts import OpenAITTS  # TODO: Phase 8
# from app.providers.tts.azure_tts import AzureTTS  # TODO: Phase 8
from app.core.exceptions import ProviderNotFoundError, ProviderAPIKeyMissingError
from app.config import get_provider_api_key, get_provider_model
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class TTSFactory:
    """
    Factory for creating TTS provider instances
    """

    # Registry of available TTS providers
    _providers = {
        "elevenlabs": ElevenLabsTTS,
        "google": GoogleTTS,
        # "openai": OpenAITTS,  # TODO: Phase 8
        # "azure": AzureTTS,  # TODO: Phase 8
    }

    @classmethod
    def create(
        cls,
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> TTSBase:
        """
        Create a TTS provider instance

        Args:
            provider_name: Name of the provider (elevenlabs, openai, google, azure)
            api_key: API key (if None, will be loaded from config)
            model: Model name (if None, will be loaded from config)
            voice_id: Voice ID
            language: Language code
            **kwargs: Additional provider-specific parameters

        Returns:
            TTS provider instance

        Raises:
            ProviderNotFoundError: If provider is not available
            ProviderAPIKeyMissingError: If API key is not configured
        """
        provider_name = provider_name.lower()

        # Check if provider exists
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ProviderNotFoundError("tts", provider_name)

        # Get API key from config if not provided
        if api_key is None:
            api_key = get_provider_api_key("tts", provider_name)
            if not api_key:
                raise ProviderAPIKeyMissingError("tts", provider_name)

        # Get model from config if not provided
        if model is None:
            model = get_provider_model("tts", provider_name)

        # Get provider class
        provider_class = cls._providers[provider_name]

        # Create instance
        logger.info(
            f"Creating TTS provider: {provider_name} "
            f"(model={model}, voice_id={voice_id}, language={language})"
        )

        try:
            instance = provider_class(
                api_key=api_key,
                model=model,
                voice_id=voice_id,
                language=language,
                **kwargs
            )
            return instance
        except Exception as e:
            logger.error(
                f"Failed to create TTS provider {provider_name}: {str(e)}",
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
        Register a new TTS provider (for extensibility)

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from TTSBase)
        """
        if not issubclass(provider_class, TTSBase):
            raise ValueError(f"{provider_class} must inherit from TTSBase")

        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered TTS provider: {name}")


# Export factory
__all__ = ["TTSFactory"]
