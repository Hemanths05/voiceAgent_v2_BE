"""
Admin API Routes
Handles company-specific management for admin users
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from typing import Optional, List

from app.schemas.call import (
    CallResponse,
    CallListResponse,
    CallStatsResponse,
    CallFilterParams
)
from app.schemas.knowledge import (
    KnowledgeUploadRequest,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeListResponse,
    KnowledgeUploadResponse
)
from app.schemas.agent import (
    AgentConfigUpdate,
    AgentConfigResponse
)
from app.schemas.company import CompanyStatsResponse, DashboardMetricsResponse
from app.services.call_service import CallService
from app.services.knowledge_service import KnowledgeService
from app.services.agent_service import AgentService
from app.services.company_service import CompanyService
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import (
    ValidationError,
    CallNotFoundError,
    KnowledgeNotFoundError,
    AgentConfigNotFoundError,
    AuthorizationError
)
from app.core.logging_config import get_logger
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_role("admin"))]
)


# ============================================================
# DASHBOARD & STATISTICS
# ============================================================

@router.get(
    "/dashboard",
    response_model=DashboardMetricsResponse,
    summary="Get company dashboard",
    description="Get dashboard metrics for the admin's company"
)
async def get_dashboard(
    current_user: dict = Depends(get_current_user)
):
    """
    Get dashboard metrics for admin's company

    Args:
        current_user: Current authenticated user (must be admin)

    Returns:
        DashboardMetricsResponse with dashboard metrics

    Raises:
        HTTPException 403: If user is not admin or has no company
        HTTPException 500: If retrieval fails
    """
    try:
        company_id = current_user.get("company_id")
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No company associated with user"
            )

        company_service = CompanyService()
        response = await company_service.get_dashboard_metrics(company_id)

        logger.debug(f"Dashboard retrieved for company: {company_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to get dashboard: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard"
        )


# ============================================================
# CALL MANAGEMENT
# ============================================================

@router.get(
    "/calls",
    response_model=CallListResponse,
    summary="List calls",
    description="Get paginated list of calls for the admin's company"
)
async def list_calls(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    from_number: Optional[str] = Query(None, description="Filter by caller number"),
    direction: Optional[str] = Query(None, description="Filter by direction"),
    start_date: Optional[datetime] = Query(None, description="Filter calls after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter calls before this date"),
    min_duration: Optional[int] = Query(None, description="Filter by minimum duration"),
    max_duration: Optional[int] = Query(None, description="Filter by maximum duration"),
    current_user: dict = Depends(get_current_user)
):
    """
    List calls for admin's company with pagination and filtering

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        status_filter: Filter by status
        from_number: Filter by caller number
        direction: Filter by direction (inbound/outbound)
        start_date: Filter calls after this date
        end_date: Filter calls before this date
        min_duration: Filter by minimum duration (seconds)
        max_duration: Filter by maximum duration (seconds)
        current_user: Current authenticated user (must be admin)

    Returns:
        CallListResponse with paginated call list

    Raises:
        HTTPException 403: If user is not admin or has no company
        HTTPException 500: If listing fails
    """
    try:
        company_id = current_user.get("company_id")
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No company associated with user"
            )

        # Build filter params
        filters = CallFilterParams(
            status=status_filter,
            from_number=from_number,
            direction=direction,
            start_date=start_date,
            end_date=end_date,
            min_duration=min_duration,
            max_duration=max_duration
        )

        call_service = CallService()
        response = await call_service.list_calls(
            company_id=company_id,
            page=page,
            page_size=page_size,
            filters=filters,
            requesting_user_id=current_user.get("user_id")
        )

        logger.debug(f"Listed {len(response.items)} calls (page {page}) for company {company_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to list calls: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve calls"
        )


@router.get(
    "/calls/{call_id}",
    response_model=CallResponse,
    summary="Get call details",
    description="Get detailed information about a specific call including transcript"
)
async def get_call(
    call_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get call details including transcript

    Args:
        call_id: Call ID
        current_user: Current authenticated user (must be admin)

    Returns:
        CallResponse with call details and transcript

    Raises:
        HTTPException 403: If user doesn't have permission
        HTTPException 404: If call not found
        HTTPException 500: If retrieval fails
    """
    try:
        call_service = CallService()
        response = await call_service.get_call(
            call_id=call_id,
            requesting_user_id=current_user.get("user_id")
        )

        logger.debug(f"Call retrieved: {call_id}")
        return response

    except CallNotFoundError as e:
        logger.warning(f"Call not found: {call_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except AuthorizationError as e:
        logger.warning(f"Call access denied: {call_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to get call: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve call"
        )


@router.get(
    "/calls/stats",
    response_model=CallStatsResponse,
    summary="Get call statistics",
    description="Get call statistics for the admin's company"
)
async def get_call_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get call statistics for admin's company

    Args:
        current_user: Current authenticated user (must be admin)

    Returns:
        CallStatsResponse with call statistics

    Raises:
        HTTPException 403: If user is not admin or has no company
        HTTPException 500: If retrieval fails
    """
    try:
        company_id = current_user.get("company_id")
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No company associated with user"
            )

        call_service = CallService()
        response = await call_service.get_call_stats(
            company_id=company_id,
            requesting_user_id=current_user.get("user_id")
        )

        logger.debug(f"Call stats retrieved for company: {company_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to get call stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve call statistics"
        )


# ============================================================
# KNOWLEDGE BASE MANAGEMENT
# ============================================================

@router.post(
    "/knowledge/upload",
    response_model=KnowledgeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload knowledge document",
    description="Upload a document to the company knowledge base"
)
async def upload_knowledge(
    file: UploadFile = File(..., description="Document file (PDF, TXT, DOCX, CSV)"),
    title: str = Form(..., description="Document title"),
    description: Optional[str] = Form(None, description="Document description"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload document to knowledge base

    Args:
        file: Document file to upload
        title: Document title
        description: Optional document description
        tags: Optional comma-separated tags
        current_user: Current authenticated user (must be admin)

    Returns:
        KnowledgeUploadResponse with upload result

    Raises:
        HTTPException 400: If validation fails or file format unsupported
        HTTPException 403: If user is not admin or has no company
        HTTPException 413: If file too large
        HTTPException 500: If upload fails
    """
    try:
        company_id = current_user.get("company_id")
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No company associated with user"
            )

        # Read file data
        file_data = await file.read()

        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

        # Create upload request
        upload_request = KnowledgeUploadRequest(
            title=title,
            description=description,
            tags=tag_list
        )

        knowledge_service = KnowledgeService()
        response = await knowledge_service.upload_knowledge(
            file_data=file_data,
            filename=file.filename,
            data=upload_request,
            company_id=company_id,
            uploaded_by_user_id=current_user.get("user_id")
        )

        logger.info(f"Knowledge uploaded: {title} (ID: {response.knowledge.id})")
        return response

    except ValidationError as e:
        logger.warning(f"Knowledge upload validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to upload knowledge: {str(e)}", exc_info=True)

        # Check if it's a file size error
        if "size" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum size is 10MB."
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload knowledge document"
        )


@router.get(
    "/knowledge",
    response_model=KnowledgeListResponse,
    summary="List knowledge entries",
    description="Get list of knowledge base entries for the admin's company"
)
async def list_knowledge(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    current_user: dict = Depends(get_current_user)
):
    """
    List knowledge base entries

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        tag: Filter by tag
        current_user: Current authenticated user (must be admin)

    Returns:
        KnowledgeListResponse with paginated knowledge list

    Raises:
        HTTPException 403: If user is not admin or has no company
        HTTPException 500: If listing fails
    """
    try:
        company_id = current_user.get("company_id")
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No company associated with user"
            )

        knowledge_service = KnowledgeService()
        response = await knowledge_service.list_knowledge(
            company_id=company_id,
            page=page,
            page_size=page_size,
            tags=[tag] if tag else None,
            requesting_user_id=current_user.get("user_id")
        )

        logger.debug(f"Listed {len(response.items)} knowledge entries (page {page})")
        return response

    except Exception as e:
        logger.error(f"Failed to list knowledge: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve knowledge entries"
        )


@router.delete(
    "/knowledge/{knowledge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete knowledge entry",
    description="Delete a knowledge base entry and its vectors"
)
async def delete_knowledge(
    knowledge_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete knowledge entry

    Args:
        knowledge_id: Knowledge entry ID
        current_user: Current authenticated user (must be admin)

    Returns:
        No content on success

    Raises:
        HTTPException 403: If user doesn't have permission
        HTTPException 404: If knowledge entry not found
        HTTPException 500: If deletion fails
    """
    try:
        knowledge_service = KnowledgeService()
        await knowledge_service.delete_knowledge(
            knowledge_id=knowledge_id,
            company_id=current_user.get("company_id"),
            deleting_user_id=current_user.get("user_id")
        )

        logger.info(f"Knowledge deleted: {knowledge_id}")
        return None

    except KnowledgeNotFoundError as e:
        logger.warning(f"Knowledge not found: {knowledge_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except AuthorizationError as e:
        logger.warning(f"Knowledge deletion access denied: {knowledge_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to delete knowledge: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete knowledge entry"
        )


@router.post(
    "/knowledge/search",
    response_model=KnowledgeSearchResponse,
    summary="Search knowledge base",
    description="Semantic search in company knowledge base"
)
async def search_knowledge(
    data: KnowledgeSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search knowledge base using semantic search

    Args:
        data: Search request with query and parameters
        current_user: Current authenticated user (must be admin)

    Returns:
        KnowledgeSearchResponse with relevant chunks

    Raises:
        HTTPException 403: If user is not admin or has no company
        HTTPException 500: If search fails
    """
    try:
        company_id = current_user.get("company_id")
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No company associated with user"
            )

        knowledge_service = KnowledgeService()
        response = await knowledge_service.search_knowledge(
            query=data.query,
            company_id=company_id,
            top_k=data.top_k or 5,
            score_threshold=data.score_threshold or 0.5
        )

        logger.debug(f"Knowledge search: {data.query} ({len(response.results)} results)")
        return response

    except Exception as e:
        logger.error(f"Failed to search knowledge: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search knowledge base"
        )


# ============================================================
# AGENT CONFIGURATION
# ============================================================

@router.get(
    "/agent/config",
    response_model=AgentConfigResponse,
    summary="Get agent configuration",
    description="Get AI agent configuration for the admin's company"
)
async def get_agent_config(
    current_user: dict = Depends(get_current_user)
):
    """
    Get agent configuration

    Args:
        current_user: Current authenticated user (must be admin)

    Returns:
        AgentConfigResponse with agent configuration

    Raises:
        HTTPException 403: If user is not admin or has no company
        HTTPException 404: If agent config not found
        HTTPException 500: If retrieval fails
    """
    try:
        company_id = current_user.get("company_id")
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No company associated with user"
            )

        agent_service = AgentService()
        response = await agent_service.get_agent_config(
            company_id=company_id,
            requesting_user_id=current_user.get("user_id")
        )

        logger.debug(f"Agent config retrieved for company: {company_id}")
        return response

    except AgentConfigNotFoundError as e:
        logger.warning(f"Agent config not found for company: {current_user.get('company_id')}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to get agent config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent configuration"
        )


@router.put(
    "/agent/config",
    response_model=AgentConfigResponse,
    summary="Update agent configuration",
    description="Update AI agent configuration for the admin's company"
)
async def update_agent_config(
    data: AgentConfigUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update agent configuration

    Args:
        data: Agent configuration update data
        current_user: Current authenticated user (must be admin)

    Returns:
        AgentConfigResponse with updated agent configuration

    Raises:
        HTTPException 400: If validation fails
        HTTPException 403: If user is not admin or has no company
        HTTPException 404: If agent config not found
        HTTPException 500: If update fails
    """
    try:
        company_id = current_user.get("company_id")
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No company associated with user"
            )

        agent_service = AgentService()
        response = await agent_service.update_agent_config(
            company_id=company_id,
            data=data,
            updating_user_id=current_user.get("user_id")
        )

        logger.info(f"Agent config updated for company: {company_id}")
        return response

    except AgentConfigNotFoundError as e:
        logger.warning(f"Agent config not found for company: {current_user.get('company_id')}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except ValidationError as e:
        logger.warning(f"Agent config update validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to update agent config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent configuration"
        )


# Export router
__all__ = ["router"]
