"""
Custom Exception Classes
Defines application-specific exceptions for better error handling
"""
from typing import Any, Dict, Optional


class VoiceAgentException(Exception):
    """Base exception for all Voice Agent Platform errors"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# ==================== Authentication & Authorization ====================

class AuthenticationError(VoiceAgentException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(VoiceAgentException):
    """Raised when user doesn't have permission"""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, details=details)


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid or expired"""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message)


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are incorrect"""

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message)


class UserAlreadyExistsError(VoiceAgentException):
    """Raised when trying to create a user that already exists"""

    def __init__(self, email: str):
        message = f"User already exists with email: {email}"
        super().__init__(message, status_code=409, details={"email": email})


class UserNotFoundError(VoiceAgentException):
    """Raised when a user is not found"""

    def __init__(self, identifier: str):
        message = f"User not found: {identifier}"
        super().__init__(message, status_code=404, details={"identifier": identifier})


class CompanyNotFoundError(VoiceAgentException):
    """Raised when a company is not found"""

    def __init__(self, identifier: str):
        message = f"Company not found: {identifier}"
        super().__init__(message, status_code=404, details={"identifier": identifier})


class CallNotFoundError(VoiceAgentException):
    """Raised when a call is not found"""

    def __init__(self, identifier: str):
        message = f"Call not found: {identifier}"
        super().__init__(message, status_code=404, details={"identifier": identifier})


class KnowledgeNotFoundError(VoiceAgentException):
    """Raised when a knowledge document is not found"""

    def __init__(self, identifier: str):
        message = f"Knowledge document not found: {identifier}"
        super().__init__(message, status_code=404, details={"identifier": identifier})


class AgentConfigNotFoundError(VoiceAgentException):
    """Raised when agent configuration is not found"""

    def __init__(self, company_id: str):
        message = f"Agent configuration not found for company: {company_id}"
        super().__init__(message, status_code=404, details={"company_id": company_id})


class EmbeddingsError(VoiceAgentException):
    """Raised when embeddings generation fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Embeddings error: {message}", status_code=500, details=details)


# ==================== Database Errors ====================

class DatabaseError(VoiceAgentException):
    """Base exception for database-related errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class DocumentNotFoundError(DatabaseError):
    """Raised when a document is not found in database"""

    def __init__(self, resource: str, identifier: str):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, details={"resource": resource, "identifier": identifier})
        self.status_code = 404


class DuplicateDocumentError(DatabaseError):
    """Raised when trying to create a document that already exists"""

    def __init__(self, resource: str, field: str, value: str):
        message = f"{resource} already exists with {field}: {value}"
        super().__init__(message, details={"resource": resource, "field": field, "value": value})
        self.status_code = 409


class VectorDatabaseError(DatabaseError):
    """Raised when vector database operations fail"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Vector database error: {message}", details=details)


# ==================== AI Provider Errors ====================

class AIProviderError(VoiceAgentException):
    """Base exception for AI provider errors"""

    def __init__(
        self,
        provider_name: str,
        provider_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        full_message = f"{provider_type.upper()} Provider ({provider_name}): {message}"
        details = details or {}
        details.update({"provider_name": provider_name, "provider_type": provider_type})
        super().__init__(full_message, status_code=502, details=details)


class STTProviderError(AIProviderError):
    """Raised when STT provider fails"""

    def __init__(self, provider_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(provider_name, "stt", message, details)


class LLMProviderError(AIProviderError):
    """Raised when LLM provider fails"""

    def __init__(self, provider_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(provider_name, "llm", message, details)


class TTSProviderError(AIProviderError):
    """Raised when TTS provider fails"""

    def __init__(self, provider_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(provider_name, "tts", message, details)


class EmbeddingsProviderError(AIProviderError):
    """Raised when embeddings provider fails"""

    def __init__(self, provider_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(provider_name, "embeddings", message, details)


class ProviderNotFoundError(AIProviderError):
    """Raised when requested provider is not available"""

    def __init__(self, provider_type: str, provider_name: str):
        message = f"Provider not found or not configured"
        super().__init__(provider_name, provider_type, message)
        self.status_code = 400


class ProviderAPIKeyMissingError(AIProviderError):
    """Raised when API key for provider is missing"""

    def __init__(self, provider_type: str, provider_name: str):
        message = "API key not configured"
        super().__init__(provider_name, provider_type, message)
        self.status_code = 500


class ProviderRateLimitError(AIProviderError):
    """Raised when provider rate limit is hit"""

    def __init__(self, provider_type: str, provider_name: str, retry_after: Optional[int] = None):
        message = "Rate limit exceeded"
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(provider_name, provider_type, message, details)
        self.status_code = 429


# ==================== File Processing Errors ====================

class FileProcessingError(VoiceAgentException):
    """Base exception for file processing errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class InvalidFileTypeError(FileProcessingError):
    """Raised when uploaded file type is not allowed"""

    def __init__(self, file_type: str, allowed_types: list):
        message = f"Invalid file type: {file_type}. Allowed types: {', '.join(allowed_types)}"
        super().__init__(message, details={"file_type": file_type, "allowed_types": allowed_types})


class FileSizeExceededError(FileProcessingError):
    """Raised when uploaded file exceeds size limit"""

    def __init__(self, size_mb: float, max_size_mb: int):
        message = f"File size ({size_mb:.2f}MB) exceeds maximum ({max_size_mb}MB)"
        super().__init__(message, details={"size_mb": size_mb, "max_size_mb": max_size_mb})


class DocumentParsingError(FileProcessingError):
    """Raised when document parsing fails"""

    def __init__(self, file_name: str, error: str):
        message = f"Failed to parse document '{file_name}': {error}"
        super().__init__(message, details={"file_name": file_name, "error": error})


# ==================== Audio Processing Errors ====================

class AudioProcessingError(VoiceAgentException):
    """Base exception for audio processing errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class AudioConversionError(AudioProcessingError):
    """Raised when audio format conversion fails"""

    def __init__(self, source_format: str, target_format: str, error: str):
        message = f"Failed to convert audio from {source_format} to {target_format}: {error}"
        super().__init__(message, details={
            "source_format": source_format,
            "target_format": target_format,
            "error": error
        })


class InvalidAudioFormatError(AudioProcessingError):
    """Raised when audio format is invalid or unsupported"""

    def __init__(self, format_info: str):
        message = f"Invalid or unsupported audio format: {format_info}"
        super().__init__(message, details={"format_info": format_info})


# ==================== Voice Pipeline Errors ====================

class PipelineError(VoiceAgentException):
    """Simple exception for voice pipeline errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class VoicePipelineError(VoiceAgentException):
    """Base exception for voice pipeline errors with stage tracking"""

    def __init__(self, message: str, stage: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["pipeline_stage"] = stage
        super().__init__(f"Voice pipeline error at {stage}: {message}", status_code=500, details=details)


class PipelineTimeoutError(VoicePipelineError):
    """Raised when voice pipeline exceeds timeout"""

    def __init__(self, stage: str, timeout_seconds: int):
        message = f"Pipeline timeout ({timeout_seconds}s)"
        super().__init__(message, stage, details={"timeout_seconds": timeout_seconds})


# ==================== Telephony Errors ====================

class TelephonyError(VoiceAgentException):
    """Base exception for telephony-related errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class TwilioWebhookError(TelephonyError):
    """Raised when Twilio webhook processing fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Twilio webhook error: {message}", details=details)


class InvalidTwilioSignatureError(TelephonyError):
    """Raised when Twilio webhook signature is invalid"""

    def __init__(self):
        super().__init__("Invalid Twilio webhook signature")
        self.status_code = 403


class CallSessionError(TelephonyError):
    """Raised when call session management fails"""

    def __init__(self, call_sid: str, message: str):
        super().__init__(
            f"Call session error for {call_sid}: {message}",
            details={"call_sid": call_sid}
        )


# ==================== Business Logic Errors ====================

class BusinessLogicError(VoiceAgentException):
    """Base exception for business logic errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class CompanySuspendedError(BusinessLogicError):
    """Raised when trying to use a suspended company"""

    def __init__(self, company_id: str):
        message = "Company account is suspended"
        super().__init__(message, details={"company_id": company_id})
        self.status_code = 403


class InvalidAgentConfigError(BusinessLogicError):
    """Raised when agent configuration is invalid"""

    def __init__(self, message: str, config_field: Optional[str] = None):
        details = {"config_field": config_field} if config_field else {}
        super().__init__(f"Invalid agent configuration: {message}", details=details)


class InsufficientKnowledgeError(BusinessLogicError):
    """Raised when knowledge base doesn't have enough information"""

    def __init__(self, company_id: str):
        message = "No knowledge base configured for company"
        super().__init__(message, details={"company_id": company_id})


# ==================== Validation Errors ====================

class ValidationError(VoiceAgentException):
    """Raised when input validation fails"""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(f"Validation error: {message}", status_code=400, details=details)


class RequiredFieldMissingError(ValidationError):
    """Raised when required field is missing"""

    def __init__(self, field: str):
        super().__init__(f"Required field missing: {field}", field=field)


# ==================== Configuration Errors ====================

class ConfigurationError(VoiceAgentException):
    """Raised when application configuration is invalid"""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(f"Configuration error: {message}", status_code=500, details=details)


# Export all exceptions
__all__ = [
    "VoiceAgentException",
    "AuthenticationError",
    "AuthorizationError",
    "InvalidTokenError",
    "InvalidCredentialsError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "CompanyNotFoundError",
    "CallNotFoundError",
    "KnowledgeNotFoundError",
    "AgentConfigNotFoundError",
    "EmbeddingsError",
    "DatabaseError",
    "DocumentNotFoundError",
    "DuplicateDocumentError",
    "VectorDatabaseError",
    "AIProviderError",
    "STTProviderError",
    "LLMProviderError",
    "TTSProviderError",
    "EmbeddingsProviderError",
    "ProviderNotFoundError",
    "ProviderAPIKeyMissingError",
    "ProviderRateLimitError",
    "FileProcessingError",
    "InvalidFileTypeError",
    "FileSizeExceededError",
    "DocumentParsingError",
    "AudioProcessingError",
    "AudioConversionError",
    "InvalidAudioFormatError",
    "PipelineError",
    "VoicePipelineError",
    "PipelineTimeoutError",
    "TelephonyError",
    "TwilioWebhookError",
    "InvalidTwilioSignatureError",
    "CallSessionError",
    "BusinessLogicError",
    "CompanySuspendedError",
    "InvalidAgentConfigError",
    "InsufficientKnowledgeError",
    "ValidationError",
    "RequiredFieldMissingError",
    "ConfigurationError",
]
