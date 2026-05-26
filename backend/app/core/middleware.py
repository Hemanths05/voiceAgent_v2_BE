"""
Middleware Module
Handles CORS, request logging, error handling
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
from app.core.logging_config import get_logger
from app.core.exceptions import VoiceAgentException

logger = get_logger(__name__)


# ==================== Request ID Middleware ====================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store request ID in request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


# ==================== Logging Middleware ====================

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests and responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request ID
        request_id = getattr(request.state, "request_id", "unknown")

        # Start timer
        start_time = time.time()

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else "unknown",
            }
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            logger.error(
                f"Request failed: {str(e)}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                }
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            f"Response: {response.status_code} - {duration_ms:.2f}ms",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )

        # Add duration header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


# ==================== Error Handling Middleware ====================

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches and formats all exceptions
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except VoiceAgentException as e:
            # Handle custom exceptions
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "error": {
                        "message": e.message,
                        "type": type(e).__name__,
                        "details": e.details,
                    },
                    "request_id": getattr(request.state, "request_id", None),
                }
            )
        except ValueError as e:
            # Handle validation errors
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": {
                        "message": str(e),
                        "type": "ValueError",
                        "details": {},
                    },
                    "request_id": getattr(request.state, "request_id", None),
                }
            )
        except Exception as e:
            # Handle unexpected exceptions
            logger.error(
                f"Unexpected error: {str(e)}",
                exc_info=True,
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "path": request.url.path,
                }
            )

            # Don't expose internal errors in production
            if settings.environment == "production":
                error_message = "An internal server error occurred"
            else:
                error_message = str(e)

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": {
                        "message": error_message,
                        "type": "InternalServerError",
                        "details": {},
                    },
                    "request_id": getattr(request.state, "request_id", None),
                }
            )


# ==================== CORS Configuration ====================

def get_cors_middleware():
    """
    Get configured CORS middleware

    Returns:
        CORS middleware configuration
    """
    return CORSMiddleware, {
        "allow_origins": settings.cors_origins_list,
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": settings.cors_allow_methods.split(",") if settings.cors_allow_methods != "*" else ["*"],
        "allow_headers": settings.cors_allow_headers.split(",") if settings.cors_allow_headers != "*" else ["*"],
        "expose_headers": ["X-Request-ID", "X-Response-Time"],
    }


# Export middleware classes and functions
__all__ = [
    "RequestIDMiddleware",
    "LoggingMiddleware",
    "ErrorHandlingMiddleware",
    "get_cors_middleware",
]
