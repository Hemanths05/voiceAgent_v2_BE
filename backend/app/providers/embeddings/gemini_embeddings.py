"""
Google Gemini Embeddings Provider
Implementation of embeddings using Google's Gemini API
"""
from typing import List
import google.genai as genai
from app.providers.base.embeddings_base import EmbeddingsBase, EmbeddingsResponse
from app.core.exceptions import EmbeddingsProviderError, ProviderAPIKeyMissingError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class GeminiEmbeddings(EmbeddingsBase):
    """
    Google Gemini Embeddings provider
    Uses Google's Gemini API for text embeddings
    """

    def __init__(
        self,
        api_key: str,
        model: str = "models/gemini-embedding-001",
        dimensions: int = 768,  # Gemini embedding dimension
        **kwargs
    ):
        """
        Initialize Gemini Embeddings provider

        Args:
            api_key: Google API key
            model: Model name (models/text-embedding-004, etc.)
            dimensions: Expected embedding dimensions
            **kwargs: Additional parameters
        """
        super().__init__(api_key, model, dimensions, **kwargs)

        if not api_key:
            raise ProviderAPIKeyMissingError("embeddings", "gemini")

        # Configure Gemini API
        genai.configure(api_key=api_key)

        # Task type for embeddings (retrieval_document, retrieval_query, etc.)
        self.task_type = kwargs.get("task_type", "retrieval_document")

    async def embed(
        self,
        texts: List[str],
        **kwargs
    ) -> EmbeddingsResponse:
        """
        Generate embeddings for texts using Gemini

        Args:
            texts: List of texts to embed
            **kwargs: Additional parameters (task_type, etc.)

        Returns:
            EmbeddingsResponse with embedding vectors

        Raises:
            EmbeddingsProviderError: If embedding generation fails
        """
        try:
            if not texts:
                raise ValueError("No texts provided for embedding")

            # Get task type
            task_type = kwargs.get("task_type", self.task_type)

            logger.info(
                f"Generating embeddings with Gemini: "
                f"model={self.model}, texts={len(texts)}, task_type={task_type}"
            )

            # Gemini processes embeddings synchronously
            # We'll use the blocking API (asyncio.to_thread in real async context)
            embeddings_list = []

            for text in texts:
                # Generate embedding for each text
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type=task_type,
                    output_dimensionality=self.dimensions,
                )

                # Extract embedding vector
                embedding = result['embedding']
                embeddings_list.append(embedding)

            # Validate dimensions
            if embeddings_list and not self.validate_dimensions(embeddings_list):
                actual_dim = len(embeddings_list[0])
                logger.warning(
                    f"Dimension mismatch: expected {self.dimensions}, got {actual_dim}"
                )

            logger.info(
                f"✓ Gemini embeddings generated: "
                f"count={len(embeddings_list)}, dimensions={len(embeddings_list[0]) if embeddings_list else 0}"
            )

            return EmbeddingsResponse(
                embeddings=embeddings_list,
                model=self.model,
                dimensions=len(embeddings_list[0]) if embeddings_list else self.dimensions,
                total_tokens=None,  # Gemini doesn't provide token counts for embeddings
                provider_metadata={
                    "provider": "gemini",
                    "task_type": task_type,
                }
            )

        except Exception as e:
            error_msg = f"Gemini embeddings generation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise EmbeddingsProviderError("gemini", error_msg)

    async def health_check(self) -> bool:
        """
        Check if Gemini API is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to generate a test embedding
            result = genai.embed_content(
                model=self.model,
                content="test",
                task_type="retrieval_document",
                output_dimensionality=self.dimensions,
            )
            return 'embedding' in result and len(result['embedding']) > 0
        except Exception as e:
            logger.error(f"Gemini health check failed: {str(e)}")
            return False


# Export provider
__all__ = ["GeminiEmbeddings"]
