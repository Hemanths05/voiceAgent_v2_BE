"""
Agent Service
Handles agent configuration management
"""
from typing import Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.exceptions import (
    AgentConfigNotFoundError,
    ValidationError,
    AuthorizationError
)
from app.core.logging_config import get_logger
from app.database.mongodb import get_database
from app.schemas.agent import AgentConfigUpdate, AgentConfigResponse
from app.utils.validators import Validators

logger = get_logger(__name__)


class AgentService:
    """
    Service for handling agent configuration operations
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """
        Initialize agent service

        Args:
            db: MongoDB database instance (if None, will use get_database())
        """
        self.db = db or get_database()
        self.agent_configs_collection = self.db.agent_configs
        self.users_collection = self.db.users

    async def get_agent_config(
        self,
        company_id: str,
        requesting_user_id: Optional[str] = None
    ) -> AgentConfigResponse:
        """
        Get agent configuration for a company

        Args:
            company_id: Company ID
            requesting_user_id: ID of user making request (for authorization)

        Returns:
            Agent configuration

        Raises:
            AgentConfigNotFoundError: If config not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            if not company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})

            # Check authorization
            if requesting_user_id:
                await self._check_company_authorization(requesting_user_id, company_id)

            # Get agent config
            config = await self.agent_configs_collection.find_one({"company_id": company_id})

            if not config:
                raise AgentConfigNotFoundError(f"Agent config not found for company: {company_id}")

            return self._build_config_response(config)

        except (AgentConfigNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting agent config: {str(e)}", exc_info=True)
            raise

    async def update_agent_config(
        self,
        company_id: str,
        data: AgentConfigUpdate,
        updating_user_id: Optional[str] = None
    ) -> AgentConfigResponse:
        """
        Update agent configuration

        Args:
            company_id: Company ID
            data: Configuration update data
            updating_user_id: ID of user making update (for authorization)

        Returns:
            Updated agent configuration

        Raises:
            AgentConfigNotFoundError: If config not found
            ValidationError: If validation fails
            AuthorizationError: If user doesn't have permission
        """
        try:
            if not company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})

            # Check authorization
            if updating_user_id:
                await self._check_company_authorization(updating_user_id, company_id)

            # Get existing config
            config = await self.agent_configs_collection.find_one({"company_id": company_id})

            # If config doesn't exist, create it with defaults
            if not config:
                from app.config import settings

                # Create new config with default values from settings
                new_config = {
                    "company_id": company_id,
                    "stt_provider": settings.stt_provider,
                    "llm_provider": settings.llm_provider,
                    "tts_provider": settings.tts_provider,
                    "embeddings_provider": settings.embeddings_provider,
                    "stt_model": None,
                    "llm_model": None,
                    "tts_model": None,
                    "embeddings_model": None,
                    "temperature": settings.default_temperature,
                    "max_tokens": settings.default_max_tokens,
                    "top_p": settings.default_top_p,
                    "voice_id": None,
                    "voice_settings": {},
                    "system_prompt": settings.default_system_prompt,
                    "greeting_message": settings.default_greeting,
                    "enable_rag": False,
                    "rag_top_k": settings.rag_top_k,
                    "conversation_history_limit": 10,
                    "fallback_stt_provider": None,
                    "fallback_llm_provider": None,
                    "fallback_tts_provider": None,
                    "enable_interruption": True,
                    "silence_timeout": 3,
                    "metadata": {},
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }

                # Insert the new config
                await self.agent_configs_collection.insert_one(new_config)
                config = new_config
                logger.info(f"Created new agent config for company: {company_id}")

            # Build update document
            update_doc = {"updated_at": datetime.utcnow()}

            # AI Provider selection
            if data.stt_provider is not None:
                self._validate_provider("stt", data.stt_provider)
                update_doc["stt_provider"] = data.stt_provider

            if data.llm_provider is not None:
                self._validate_provider("llm", data.llm_provider)
                update_doc["llm_provider"] = data.llm_provider

            if data.tts_provider is not None:
                self._validate_provider("tts", data.tts_provider)
                update_doc["tts_provider"] = data.tts_provider

            if data.embeddings_provider is not None:
                self._validate_provider("embeddings", data.embeddings_provider)
                update_doc["embeddings_provider"] = data.embeddings_provider

            # AI Provider models
            if data.stt_model is not None:
                update_doc["stt_model"] = data.stt_model

            if data.llm_model is not None:
                update_doc["llm_model"] = data.llm_model

            if data.tts_model is not None:
                update_doc["tts_model"] = data.tts_model

            if data.embeddings_model is not None:
                update_doc["embeddings_model"] = data.embeddings_model

            # LLM parameters
            if data.temperature is not None:
                update_doc["temperature"] = data.temperature

            if data.max_tokens is not None:
                update_doc["max_tokens"] = data.max_tokens

            if data.top_p is not None:
                update_doc["top_p"] = data.top_p

            # TTS parameters
            if data.voice_id is not None:
                update_doc["voice_id"] = data.voice_id

            if data.voice_settings is not None:
                update_doc["voice_settings"] = data.voice_settings

            # Agent behavior
            if data.system_prompt is not None:
                update_doc["system_prompt"] = data.system_prompt

            if data.greeting_message is not None:
                update_doc["greeting_message"] = data.greeting_message

            if data.enable_rag is not None:
                update_doc["enable_rag"] = data.enable_rag

            if data.rag_top_k is not None:
                update_doc["rag_top_k"] = data.rag_top_k

            if data.conversation_history_limit is not None:
                update_doc["conversation_history_limit"] = data.conversation_history_limit

            # Fallback configuration
            if data.fallback_stt_provider is not None:
                if data.fallback_stt_provider:
                    self._validate_provider("stt", data.fallback_stt_provider)
                update_doc["fallback_stt_provider"] = data.fallback_stt_provider

            if data.fallback_llm_provider is not None:
                if data.fallback_llm_provider:
                    self._validate_provider("llm", data.fallback_llm_provider)
                update_doc["fallback_llm_provider"] = data.fallback_llm_provider

            if data.fallback_tts_provider is not None:
                if data.fallback_tts_provider:
                    self._validate_provider("tts", data.fallback_tts_provider)
                update_doc["fallback_tts_provider"] = data.fallback_tts_provider

            # Advanced settings
            if data.enable_interruption is not None:
                update_doc["enable_interruption"] = data.enable_interruption

            if data.silence_timeout is not None:
                update_doc["silence_timeout"] = data.silence_timeout

            if data.metadata is not None:
                update_doc["metadata"] = data.metadata

            # Update config
            await self.agent_configs_collection.update_one(
                {"company_id": company_id},
                {"$set": update_doc}
            )

            logger.info(f"Agent config updated for company: {company_id}")

            # Return updated config
            return await self.get_agent_config(company_id)

        except (AgentConfigNotFoundError, ValidationError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error updating agent config: {str(e)}", exc_info=True)
            raise

    def _validate_provider(self, provider_type: str, provider_name: str) -> None:
        """
        Validate provider name is valid

        Args:
            provider_type: Type of provider (stt, llm, tts, embeddings)
            provider_name: Provider name

        Raises:
            ValidationError: If provider is invalid
        """
        valid_providers = {
            "stt": ["groq", "openai", "assemblyai", "deepgram"],
            "llm": ["groq", "openai", "anthropic", "gemini"],
            "tts": ["elevenlabs", "openai", "google", "azure"],
            "embeddings": ["openai", "voyage", "cohere", "gemini"]
        }

        if provider_name not in valid_providers.get(provider_type, []):
            raise ValidationError(
                f"Invalid {provider_type} provider: {provider_name}",
                {
                    "provider_type": provider_type,
                    "provider_name": provider_name,
                    "valid_providers": valid_providers[provider_type]
                }
            )

    def _build_config_response(self, config: dict) -> AgentConfigResponse:
        """
        Build agent config response from MongoDB document

        Args:
            config: MongoDB document

        Returns:
            Agent config response
        """
        return AgentConfigResponse(
            id=str(config["_id"]),
            company_id=config["company_id"],
            # AI Provider selection
            stt_provider=config["stt_provider"],
            llm_provider=config["llm_provider"],
            tts_provider=config["tts_provider"],
            embeddings_provider=config["embeddings_provider"],
            # AI Provider models
            stt_model=config.get("stt_model"),
            llm_model=config.get("llm_model"),
            tts_model=config.get("tts_model"),
            embeddings_model=config.get("embeddings_model"),
            # LLM parameters
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            top_p=config["top_p"],
            # TTS parameters
            voice_id=config.get("voice_id"),
            voice_settings=config.get("voice_settings"),
            # Agent behavior
            system_prompt=config["system_prompt"],
            greeting_message=config["greeting_message"],
            enable_rag=config["enable_rag"],
            rag_top_k=config["rag_top_k"],
            conversation_history_limit=config["conversation_history_limit"],
            # Fallback configuration
            fallback_stt_provider=config.get("fallback_stt_provider"),
            fallback_llm_provider=config.get("fallback_llm_provider"),
            fallback_tts_provider=config.get("fallback_tts_provider"),
            # Advanced settings
            enable_interruption=config["enable_interruption"],
            silence_timeout=config["silence_timeout"],
            metadata=config.get("metadata"),
            # Timestamps
            created_at=config["created_at"],
            updated_at=config["updated_at"]
        )

    async def _check_company_authorization(
        self,
        user_id: str,
        company_id: str
    ) -> None:
        """
        Check if user can access company's agent config

        Args:
            user_id: User ID
            company_id: Company ID

        Raises:
            AuthorizationError: If not authorized
        """
        user = await self.users_collection.find_one({"_id": int(user_id)})
        if not user:
            raise AuthorizationError("User not found")

        # Superadmin can access all companies
        if user["role"] == "superadmin":
            return

        # Admin can only access their own company
        if user["role"] == "admin":
            if user.get("company_id") != company_id:
                raise AuthorizationError("Cannot access other companies' agent config")
            return

        raise AuthorizationError("Insufficient permissions")


# Export service
__all__ = ["AgentService"]
