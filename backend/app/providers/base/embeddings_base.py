"""
Embeddings Provider Base Class
Abstract base class that all Embeddings providers must implement
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class EmbeddingsResponse(BaseModel):
    """
    Standard response format for Embeddings providers
    """
    embeddings: List[List[float]]  # List of embedding vectors
    model: str  # Model used for embeddings
    dimensions: int  # Embedding dimension size
    total_tokens: Optional[int] = None  # Total tokens processed
    provider_metadata: Optional[dict] = None  # Provider-specific metadata


class EmbeddingsBase(ABC):
    """
    Abstract base class for Embeddings providers

    All Embeddings providers must inherit from this class and implement the embed method.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        dimensions: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize Embeddings provider

        Args:
            api_key: API key for the provider
            model: Model name (provider-specific)
            dimensions: Expected embedding dimensions (for validation)
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.extra_params = kwargs
        self.provider_name = self.__class__.__name__

    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> EmbeddingsResponse:
        """
        Generate embeddings for texts

        Args:
            texts: List of texts to embed
            **kwargs: Additional parameters for specific providers

        Returns:
            EmbeddingsResponse with embedding vectors and metadata

        Raises:
            EmbeddingsProviderError: If embedding generation fails
        """
        pass

    async def embed_single(
        self,
        text: str,
        **kwargs
    ) -> List[float]:
        """
        Generate embedding for a single text (convenience method)

        Args:
            text: Text to embed
            **kwargs: Additional parameters for specific providers

        Returns:
            Single embedding vector

        Raises:
            EmbeddingsProviderError: If embedding generation fails
        """
        response = await self.embed([text], **kwargs)
        return response.embeddings[0]

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible

        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    def validate_dimensions(self, embeddings: List[List[float]]) -> bool:
        """
        Validate that embeddings have expected dimensions

        Args:
            embeddings: List of embedding vectors

        Returns:
            True if dimensions match, False otherwise
        """
        if not embeddings:
            return True

        if self.dimensions is None:
            return True

        # Check first embedding dimension
        actual_dim = len(embeddings[0])
        return actual_dim == self.dimensions

    def normalize_embeddings(
        self,
        embeddings: List[List[float]]
    ) -> List[List[float]]:
        """
        Normalize embeddings to unit length (optional)

        Args:
            embeddings: List of embedding vectors

        Returns:
            Normalized embedding vectors
        """
        import math

        normalized = []
        for embedding in embeddings:
            # Calculate magnitude
            magnitude = math.sqrt(sum(x * x for x in embedding))

            # Normalize
            if magnitude > 0:
                normalized_embedding = [x / magnitude for x in embedding]
            else:
                normalized_embedding = embedding

            normalized.append(normalized_embedding)

        return normalized

    def __repr__(self) -> str:
        return f"{self.provider_name}(model={self.model}, dimensions={self.dimensions})"


# Export base class and response model
__all__ = ["EmbeddingsBase", "EmbeddingsResponse"]
