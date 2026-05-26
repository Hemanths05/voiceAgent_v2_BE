"""
Embeddings Provider Factory
Creates embeddings provider instances based on configuration
"""
from typing import Optional
from app.providers.base.embeddings_base import EmbeddingsBase
from app.providers.embeddings.gemini_embeddings import GeminiEmbeddings
# from app.providers.embeddings.openai_embeddings import OpenAIEmbeddings  # TODO: Phase 9
# from app.providers.embeddings.voyage import VoyageEmbeddings  # TODO: Phase 9
# from app.providers.embeddings.cohere import CohereEmbeddings  # TODO: Phase 9
from app.core.exceptions import ProviderNotFoundError, ProviderAPIKeyMissingError
from app.config import get_provider_api_key, get_provider_model, settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingsFactory:
    """
    Factory for creating embeddings provider instances
    """

    # Registry of available embeddings providers
    _providers = {
        "gemini": GeminiEmbeddings,
        # "openai": OpenAIEmbeddings,  # TODO: Phase 9
        # "voyage": VoyageEmbeddings,  # TODO: Phase 9
        # "cohere": CohereEmbeddings,  # TODO: Phase 9
    }

    # Default dimensions for each provider
    _default_dimensions = {
        "gemini": 768,
        # "openai": 1536,  # ada-002
        # "voyage": 1024,  # voyage-2
        # "cohere": 1024,  # embed-english-v3.0
    }

    @classmethod
    def create(
        cls,
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
        **kwargs
    ) -> EmbeddingsBase:
        """
        Create an embeddings provider instance

        Args:
            provider_name: Name of the provider (openai, voyage, cohere, gemini)
            api_key: API key (if None, will be loaded from config)
            model: Model name (if None, will be loaded from config)
            dimensions: Expected embedding dimensions (if None, uses default)
            **kwargs: Additional provider-specific parameters

        Returns:
            Embeddings provider instance

        Raises:
            ProviderNotFoundError: If provider is not available
            ProviderAPIKeyMissingError: If API key is not configured
        """
        provider_name = provider_name.lower()

        # Check if provider exists
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ProviderNotFoundError("embeddings", provider_name)

        # Get API key from config if not provided
        if api_key is None:
            api_key = get_provider_api_key("embeddings", provider_name)
            if not api_key:
                raise ProviderAPIKeyMissingError("embeddings", provider_name)

        # Get model from config if not provided
        if model is None:
            model = get_provider_model("embeddings", provider_name)

        # Get dimensions if not provided
        if dimensions is None:
            dimensions = cls._default_dimensions.get(
                provider_name,
                settings.qdrant_vector_size  # Fallback to Qdrant config
            )

        # Get provider class
        provider_class = cls._providers[provider_name]

        # Create instance
        logger.info(
            f"Creating Embeddings provider: {provider_name} "
            f"(model={model}, dimensions={dimensions})"
        )

        try:
            instance = provider_class(
                api_key=api_key,
                model=model,
                dimensions=dimensions,
                **kwargs
            )
            return instance
        except Exception as e:
            logger.error(
                f"Failed to create Embeddings provider {provider_name}: {str(e)}",
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
    def register_provider(
        cls,
        name: str,
        provider_class: type,
        default_dimensions: int
    ):
        """
        Register a new embeddings provider (for extensibility)

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from EmbeddingsBase)
            default_dimensions: Default embedding dimensions for this provider
        """
        if not issubclass(provider_class, EmbeddingsBase):
            raise ValueError(f"{provider_class} must inherit from EmbeddingsBase")

        cls._providers[name.lower()] = provider_class
        cls._default_dimensions[name.lower()] = default_dimensions
        logger.info(f"Registered Embeddings provider: {name} (dimensions={default_dimensions})")


# Export factory
__all__ = ["EmbeddingsFactory"]
