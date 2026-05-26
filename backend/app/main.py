"""
FastAPI Application Entry Point
Main application with all routes and middleware
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.middleware import (
    RequestIDMiddleware,
    LoggingMiddleware,
    ErrorHandlingMiddleware,
    get_cors_middleware,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)


# ==================== Lifespan Context Manager ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info("=" * 60)

    # Connect to databases
    try:
        from app.database.mongodb import connect_to_mongo
        await connect_to_mongo()
        logger.info("✓ Connected to MongoDB")
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
        # Don't raise - allow app to start for health checks

    try:
        from app.database.qdrant import connect_to_qdrant
        await connect_to_qdrant()
        logger.info("✓ Connected to Qdrant")
    except Exception as e:
        logger.error(f"✗ Failed to connect to Qdrant: {str(e)}")
        # Don't raise - allow app to start for health checks

    logger.info("=" * 60)
    logger.info(f"Server running at {settings.public_url}")
    logger.info(f"API Documentation: {settings.public_url}/docs")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info(f"Shutting down {settings.app_name}")
    logger.info("=" * 60)

    # Close database connections
    try:
        from app.database.mongodb import close_mongo_connection
        await close_mongo_connection()
        logger.info("✓ Closed MongoDB connection")
    except Exception as e:
        logger.error(f"✗ Failed to close MongoDB connection: {str(e)}")

    try:
        from app.database.qdrant import close_qdrant_connection
        await close_qdrant_connection()
        logger.info("✓ Closed Qdrant connection")
    except Exception as e:
        logger.error(f"✗ Failed to close Qdrant connection: {str(e)}")

    logger.info("=" * 60)
    logger.info("Shutdown complete")
    logger.info("=" * 60)


# ==================== FastAPI Application ====================

app = FastAPI(
    title=settings.app_name,
    description="Multi-tenant SaaS platform for AI-powered voice agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=settings.debug,
    lifespan=lifespan,
)


# ==================== Middleware ====================

# Add CORS middleware
cors_middleware, cors_config = get_cors_middleware()
app.add_middleware(cors_middleware, **cors_config)

# Add custom middleware (order matters - executed in reverse order)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)


# ==================== Root Endpoints ====================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "success": True,
        "data": {
            "name": settings.app_name,
            "version": "1.0.0",
            "environment": settings.environment,
            "docs": f"{settings.public_url}/docs",
            "status": "operational",
        }
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """
    Health check endpoint for monitoring
    """
    # Check database connections
    mongodb_status = "unknown"
    qdrant_status = "unknown"

    try:
        from app.database.mongodb import get_database
        db = get_database()
        if db:
            mongodb_status = "connected"
        else:
            mongodb_status = "disconnected"
    except Exception as e:
        mongodb_status = f"error: {str(e)}"

    try:
        from app.database.qdrant import get_qdrant_client
        client = get_qdrant_client()
        if client:
            qdrant_status = "connected"
        else:
            qdrant_status = "disconnected"
    except Exception as e:
        qdrant_status = f"error: {str(e)}"

    # Determine overall health
    is_healthy = mongodb_status == "connected" and qdrant_status == "connected"

    return {
        "success": True,
        "data": {
            "status": "healthy" if is_healthy else "degraded",
            "environment": settings.environment,
            "services": {
                "mongodb": mongodb_status,
                "qdrant": qdrant_status,
            }
        }
    }


# ==================== API Routes ====================

# Phase 18 - Authentication routes
from app.api.v1 import auth
app.include_router(auth.router, prefix="/api")

# Phase 19 - SuperAdmin routes
from app.api.v1 import superadmin
app.include_router(superadmin.router, prefix="/api")

# Phase 20 - Admin routes
from app.api.v1 import admin
app.include_router(admin.router, prefix="/api")

# Phase 21 - Webhook routes
from app.api.v1 import webhooks
app.include_router(webhooks.router)

# Phase 22 - WebSocket call handler
from fastapi import WebSocket
from app.api.websockets.call_handler import handle_call_websocket

@app.websocket("/ws/call/{call_sid}")
async def websocket_call_endpoint(websocket: WebSocket, call_sid: str):
    """
    WebSocket endpoint for real-time call audio streaming

    Args:
        websocket: WebSocket connection
        call_sid: Twilio Call SID from URL path
    """
    await handle_call_websocket(websocket, call_sid)


# ==================== Error Handlers ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """
    Custom 404 handler
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "error": {
                "message": f"Endpoint not found: {request.url.path}",
                "type": "NotFoundError",
                "details": {},
            }
        }
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    """
    Custom 405 handler
    """
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={
            "success": False,
            "error": {
                "message": f"Method not allowed: {request.method} {request.url.path}",
                "type": "MethodNotAllowedError",
                "details": {},
            }
        }
    )


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
