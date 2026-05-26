"""
Large Language Model (LLM) Provider Base Class
Abstract base class that all LLM providers must implement
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from pydantic import BaseModel


class LLMMessage(BaseModel):
    """
    Standard message format for LLM conversations
    """
    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    """
    Standard response format for LLM providers
    """
    content: str  # Generated text
    finish_reason: Optional[str] = None  # "stop", "length", "content_filter", etc.
    total_tokens: Optional[int] = None  # Total tokens used
    prompt_tokens: Optional[int] = None  # Tokens in prompt
    completion_tokens: Optional[int] = None  # Tokens in completion
    provider_metadata: Optional[dict] = None  # Provider-specific metadata


class LLMBase(ABC):
    """
    Abstract base class for Large Language Model providers

    All LLM providers must inherit from this class and implement the generate method.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        top_p: float = 1.0,
        **kwargs
    ):
        """
        Initialize LLM provider

        Args:
            api_key: API key for the provider
            model: Model name (provider-specific)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.extra_params = kwargs
        self.provider_name = self.__class__.__name__

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text from messages

        Args:
            messages: List of conversation messages
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            top_p: Override default top_p
            **kwargs: Additional parameters for specific providers

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            LLMProviderError: If generation fails
        """
        pass

    @abstractmethod
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
            **kwargs: Additional parameters for specific providers

        Yields:
            Text chunks as they are generated

        Raises:
            LLMProviderError: If generation fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible

        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    def format_messages(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[LLMMessage]:
        """
        Helper method to format messages for LLM

        Args:
            system_prompt: System prompt/instructions
            user_message: Current user message
            conversation_history: Optional conversation history

        Returns:
            List of formatted LLM messages
        """
        messages = []

        # Add system message
        messages.append(LLMMessage(role="system", content=system_prompt))

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                messages.append(
                    LLMMessage(
                        role=msg.get("role", "user"),
                        content=msg.get("content", "")
                    )
                )

        # Add current user message
        messages.append(LLMMessage(role="user", content=user_message))

        return messages

    def __repr__(self) -> str:
        return (
            f"{self.provider_name}(model={self.model}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens})"
        )


# Export base class and models
__all__ = ["LLMBase", "LLMMessage", "LLMResponse"]
