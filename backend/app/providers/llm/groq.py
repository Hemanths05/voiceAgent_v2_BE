"""
Groq LLM Provider
Implementation of LLM using Groq's fast inference API (Llama models)
"""
from typing import List, Optional, AsyncIterator
from groq import AsyncGroq
from app.providers.base.llm_base import LLMBase, LLMMessage, LLMResponse
from app.core.exceptions import LLMProviderError, ProviderAPIKeyMissingError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class GroqLLM(LLMBase):
    """
    Groq LLM provider
    Uses Groq's fast inference for Llama models (3.1, 3.3)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 150,
        top_p: float = 1.0,
        **kwargs
    ):
        """
        Initialize Groq LLM provider

        Args:
            api_key: Groq API key
            model: Model name (llama-3.3-70b-versatile, llama-3.1-8b-instant, etc.)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters
        """
        super().__init__(api_key, model, temperature, max_tokens, top_p, **kwargs)

        if not api_key:
            raise ProviderAPIKeyMissingError("llm", "groq")

        # Initialize Groq client
        self.client = AsyncGroq(api_key=api_key)

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text from messages using Groq

        Args:
            messages: List of conversation messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            top_p: Override default top_p
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated text

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            # Use provided values or defaults
            temp = temperature if temperature is not None else self.temperature
            max_tok = max_tokens if max_tokens is not None else self.max_tokens
            top_p_val = top_p if top_p is not None else self.top_p

            # Convert messages to Groq format
            groq_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            logger.info(
                f"Generating with Groq: model={self.model}, "
                f"messages={len(messages)}, temperature={temp}, max_tokens={max_tok}"
            )

            # Call Groq API
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=groq_messages,
                temperature=temp,
                max_tokens=max_tok,
                top_p=top_p_val,
                stream=False,
                **kwargs
            )

            # Extract response
            content = completion.choices[0].message.content
            finish_reason = completion.choices[0].finish_reason

            # Extract token usage
            usage = completion.usage
            total_tokens = usage.total_tokens if usage else None
            prompt_tokens = usage.prompt_tokens if usage else None
            completion_tokens = usage.completion_tokens if usage else None

            logger.info(
                f"✓ Groq generation successful: "
                f"response_length={len(content)}, tokens={total_tokens}"
            )

            return LLMResponse(
                content=content,
                finish_reason=finish_reason,
                total_tokens=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                provider_metadata={
                    "model": self.model,
                    "provider": "groq",
                }
            )

        except Exception as e:
            error_msg = f"Groq generation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMProviderError("groq", error_msg)

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate text from messages with streaming

        Args:
            messages: List of conversation messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            top_p: Override default top_p
            **kwargs: Additional parameters

        Yields:
            Text chunks as they are generated

        Raises:
            LLMProviderError: If generation fails
        """
        try:
            # Use provided values or defaults
            temp = temperature if temperature is not None else self.temperature
            max_tok = max_tokens if max_tokens is not None else self.max_tokens
            top_p_val = top_p if top_p is not None else self.top_p

            # Convert messages to Groq format
            groq_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            logger.info(
                f"Streaming generation with Groq: model={self.model}, "
                f"messages={len(messages)}"
            )

            # Call Groq API with streaming
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=groq_messages,
                temperature=temp,
                max_tokens=max_tok,
                top_p=top_p_val,
                stream=True,
                **kwargs
            )

            # Yield chunks as they arrive
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            logger.info("✓ Groq streaming generation completed")

        except Exception as e:
            error_msg = f"Groq streaming generation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMProviderError("groq", error_msg)

    async def health_check(self) -> bool:
        """
        Check if Groq API is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to list models as a health check
            models = await self.client.models.list()
            return len(models.data) > 0
        except Exception as e:
            logger.error(f"Groq health check failed: {str(e)}")
            return False


# Export provider
__all__ = ["GroqLLM"]
