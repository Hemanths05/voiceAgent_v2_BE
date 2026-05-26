"""
SuperAdmin API Routes
Handles company management, user management, and global analytics
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional

from app.schemas.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyStatusUpdate,
    CompanyResponse,
    CompanyListResponse,
    CompanyStatsResponse
)
from app.schemas.user import (
    UserUpdate,
    UserResponse,
    UserListResponse
)
from app.services.company_service import CompanyService
from app.services.user_service import UserService
from app.services.call_service import CallService
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import (
    ValidationError,
    CompanyNotFoundError,
    UserNotFoundError,
    AuthorizationError
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/superadmin",
    tags=["SuperAdmin"],
    dependencies=[Depends(require_role("superadmin"))]
)


# ============================================================
# COMPANY MANAGEMENT
# ============================================================

@router.get(
    "/companies",
    response_model=CompanyListResponse,
    summary="List all companies",
    description="Get paginated list of all companies (SuperAdmin only)"
)
async def list_companies(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or phone"),
    current_user: dict = Depends(get_current_user)
):
    """
    List all companies with pagination and filtering

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        status_filter: Filter by status (active, inactive, suspended)
        search: Search by company name or phone number
        current_user: Current authenticated user (must be superadmin)

    Returns:
        CompanyListResponse with paginated company list

    Raises:
        HTTPException 403: If user is not superadmin
        HTTPException 500: If listing fails
    """
    try:
        company_service = CompanyService()
        response = await company_service.list_companies(
            page=page,
            page_size=page_size,
            status=status_filter
        )

        logger.debug(f"Listed {len(response.companies)} companies (page {page})")
        return response

    except Exception as e:
        logger.error(f"Failed to list companies: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve companies"
        )


@router.post(
    "/companies",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new company",
    description="Create a new company (SuperAdmin only)"
)
async def create_company(
    data: CompanyCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new company

    Args:
        data: Company creation data
        current_user: Current authenticated user (must be superadmin)

    Returns:
        CompanyResponse with created company information

    Raises:
        HTTPException 400: If validation fails
        HTTPException 403: If user is not superadmin
        HTTPException 500: If creation fails
    """
    try:
        company_service = CompanyService()
        response = await company_service.create_company(data)

        logger.info(f"Company created: {response.name} (ID: {response.id})")
        return response

    except ValidationError as e:
        logger.warning(f"Company creation validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to create company: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create company"
        )


@router.get(
    "/companies/{company_id}",
    response_model=CompanyResponse,
    summary="Get company by ID",
    description="Get company details (SuperAdmin only)"
)
async def get_company(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get company by ID

    Args:
        company_id: Company ID
        current_user: Current authenticated user (must be superadmin)

    Returns:
        CompanyResponse with company information

    Raises:
        HTTPException 403: If user is not superadmin
        HTTPException 404: If company not found
        HTTPException 500: If retrieval fails
    """
    try:
        company_service = CompanyService()
        response = await company_service.get_company(company_id)

        logger.debug(f"Company retrieved: {company_id}")
        return response

    except CompanyNotFoundError as e:
        logger.warning(f"Company not found: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to get company: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company"
        )


@router.put(
    "/companies/{company_id}",
    response_model=CompanyResponse,
    summary="Update company",
    description="Update company details (SuperAdmin only)"
)
async def update_company(
    company_id: str,
    data: CompanyUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update company

    Args:
        company_id: Company ID
        data: Company update data
        current_user: Current authenticated user (must be superadmin)

    Returns:
        CompanyResponse with updated company information

    Raises:
        HTTPException 400: If validation fails
        HTTPException 403: If user is not superadmin
        HTTPException 404: If company not found
        HTTPException 500: If update fails
    """
    try:
        company_service = CompanyService()
        response = await company_service.update_company(company_id, data)

        logger.info(f"Company updated: {company_id}")
        return response

    except CompanyNotFoundError as e:
        logger.warning(f"Company not found: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except ValidationError as e:
        logger.warning(f"Company update validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to update company: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company"
        )


@router.patch(
    "/companies/{company_id}/status",
    response_model=CompanyResponse,
    summary="Update company status",
    description="Change company status (active/inactive/suspended) (SuperAdmin only)"
)
async def update_company_status(
    company_id: str,
    data: CompanyStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update company status

    Args:
        company_id: Company ID
        data: Status update data
        current_user: Current authenticated user (must be superadmin)

    Returns:
        CompanyResponse with updated company information

    Raises:
        HTTPException 400: If validation fails
        HTTPException 403: If user is not superadmin
        HTTPException 404: If company not found
        HTTPException 500: If update fails
    """
    try:
        company_service = CompanyService()
        response = await company_service.update_company_status(company_id, data.status)

        logger.info(f"Company status updated: {company_id} → {data.status}")
        return response

    except CompanyNotFoundError as e:
        logger.warning(f"Company not found: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except ValidationError as e:
        logger.warning(f"Status update validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to update company status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company status"
        )


@router.get(
    "/companies/{company_id}/stats",
    response_model=CompanyStatsResponse,
    summary="Get company statistics",
    description="Get detailed statistics for a company (SuperAdmin only)"
)
async def get_company_stats(
    company_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get company statistics

    Args:
        company_id: Company ID
        current_user: Current authenticated user (must be superadmin)

    Returns:
        CompanyStatsResponse with company statistics

    Raises:
        HTTPException 403: If user is not superadmin
        HTTPException 404: If company not found
        HTTPException 500: If retrieval fails
    """
    try:
        company_service = CompanyService()
        response = await company_service.get_company_stats(company_id)

        logger.debug(f"Company stats retrieved: {company_id}")
        return response

    except CompanyNotFoundError as e:
        logger.warning(f"Company not found: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to get company stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company statistics"
        )


# ============================================================
# USER MANAGEMENT
# ============================================================

@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users",
    description="Get paginated list of all users (SuperAdmin only)"
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    role_filter: Optional[str] = Query(None, description="Filter by role"),
    company_id: Optional[str] = Query(None, description="Filter by company"),
    current_user: dict = Depends(get_current_user)
):
    """
    List all users with pagination and filtering

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        role_filter: Filter by role (superadmin, admin)
        company_id: Filter by company ID
        current_user: Current authenticated user (must be superadmin)

    Returns:
        UserListResponse with paginated user list

    Raises:
        HTTPException 403: If user is not superadmin
        HTTPException 500: If listing fails
    """
    try:
        user_service = UserService()
        response = await user_service.list_users(
            page=page,
            page_size=page_size,
            role=role_filter,
            company_id=company_id
        )

        logger.debug(f"Listed {len(response.users)} users (page {page})")
        return response

    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Get user details (SuperAdmin only)"
)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user by ID

    Args:
        user_id: User ID
        current_user: Current authenticated user (must be superadmin)

    Returns:
        UserResponse with user information

    Raises:
        HTTPException 403: If user is not superadmin
        HTTPException 404: If user not found
        HTTPException 500: If retrieval fails
    """
    try:
        user_service = UserService()
        response = await user_service.get_user(user_id)

        logger.debug(f"User retrieved: {user_id}")
        return response

    except UserNotFoundError as e:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to get user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user details (SuperAdmin only)"
)
async def update_user(
    user_id: str,
    data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user

    Args:
        user_id: User ID
        data: User update data
        current_user: Current authenticated user (must be superadmin)

    Returns:
        UserResponse with updated user information

    Raises:
        HTTPException 400: If validation fails
        HTTPException 403: If user is not superadmin
        HTTPException 404: If user not found
        HTTPException 500: If update fails
    """
    try:
        user_service = UserService()
        response = await user_service.update_user(
            user_id=user_id,
            data=data,
            updating_user_id=current_user.get("user_id")
        )

        logger.info(f"User updated: {user_id}")
        return response

    except UserNotFoundError as e:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except ValidationError as e:
        logger.warning(f"User update validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to update user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user (SuperAdmin only)"
)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete user

    Args:
        user_id: User ID
        current_user: Current authenticated user (must be superadmin)

    Returns:
        No content on success

    Raises:
        HTTPException 403: If user is not superadmin or trying to delete self
        HTTPException 404: If user not found
        HTTPException 500: If deletion fails
    """
    try:
        # Prevent self-deletion
        if user_id == current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete your own account"
            )

        user_service = UserService()
        await user_service.delete_user(
            user_id=user_id,
            deleting_user_id=current_user.get("user_id")
        )

        logger.info(f"User deleted: {user_id}")
        return None

    except UserNotFoundError as e:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except AuthorizationError as e:
        logger.warning(f"User deletion authorization failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Failed to delete user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


# ============================================================
# GLOBAL ANALYTICS
# ============================================================

@router.get(
    "/analytics/global",
    summary="Get global analytics",
    description="Get platform-wide analytics (SuperAdmin only)"
)
async def get_global_analytics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get global platform analytics

    Args:
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Global analytics including total companies, users, calls, etc.

    Raises:
        HTTPException 403: If user is not superadmin
        HTTPException 500: If retrieval fails
    """
    try:
        company_service = CompanyService()
        user_service = UserService()

        # Get aggregated statistics
        # NOTE: This is a simplified version. In production, you'd want to
        # cache these results and update them periodically

        # Get company count by status
        all_companies = await company_service.list_companies(page=1, page_size=1000)
        total_companies = all_companies.total
        active_companies = len([c for c in all_companies.companies if c.status == "active"])
        suspended_companies = len([c for c in all_companies.companies if c.status == "suspended"])

        # Get user count by role
        all_users = await user_service.list_users(page=1, page_size=1000)
        total_users = all_users.total
        superadmins = len([u for u in all_users.users if u.role == "superadmin"])
        admins = len([u for u in all_users.users if u.role == "admin"])

        # Get call statistics from database
        call_service = CallService()
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = datetime(now.year, now.month, 1)

        total_calls = await call_service.calls_collection.count_documents({})
        calls_today = await call_service.calls_collection.count_documents({"created_at": {"$gte": today_start}})
        calls_this_week = await call_service.calls_collection.count_documents({"created_at": {"$gte": week_start}})
        calls_this_month = await call_service.calls_collection.count_documents({"created_at": {"$gte": month_start}})

        analytics = {
            "companies": {
                "total": total_companies,
                "active": active_companies,
                "suspended": suspended_companies,
                "inactive": total_companies - active_companies - suspended_companies
            },
            "users": {
                "total": total_users,
                "superadmins": superadmins,
                "admins": admins
            },
            "calls": {
                "total": total_calls,
                "today": calls_today,
                "this_week": calls_this_week,
                "this_month": calls_this_month
            }
        }

        logger.debug("Global analytics retrieved")
        return analytics

    except Exception as e:
        logger.error(f"Failed to get global analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve global analytics"
        )


@router.get(
    "/analytics",
    summary="Get superadmin analytics",
    description="Get analytics for superadmin dashboard"
)
async def get_analytics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get superadmin analytics

    Returns basic statistics about the platform
    """
    try:
        require_role(current_user, "superadmin")

        company_service = CompanyService()
        user_service = UserService()
        call_service = CallService()

        # Get counts
        companies = await company_service.list_companies(page=1, page_size=1)
        users = await user_service.list_users(page=1, page_size=1)

        # Count active companies
        all_companies = await company_service.list_companies(page=1, page_size=1000)
        active_companies = len([c for c in all_companies.companies if c.status == "active"])
        suspended_companies = len([c for c in all_companies.companies if c.status == "suspended"])

        # Get call counts from database
        total_calls = await call_service.calls_collection.count_documents({})
        active_calls = await call_service.calls_collection.count_documents({
            "status": {"$in": ["initiated", "ringing", "in_progress", "in-progress"]}
        })

        return {
            "total_companies": companies.total,
            "active_companies": active_companies,
            "suspended_companies": suspended_companies,
            "total_users": users.total,
            "total_calls_all_companies": total_calls,
            "active_calls_all_companies": active_calls,
            "total_subscriptions_revenue": 0
        }
    except Exception as e:
        logger.error(f"Failed to get analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )


@router.get(
    "/analytics/calls-by-status",
    summary="Get calls by status",
    description="Get call statistics grouped by status"
)
async def get_calls_by_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Get calls grouped by status
    """
    try:
        require_role(current_user, "superadmin")

        call_service = CallService()

        # Aggregate calls by status across all companies
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        results = await call_service.calls_collection.aggregate(pipeline).to_list(length=100)

        # Convert to expected format
        status_counts = {r["_id"]: r["count"] for r in results if r["_id"]}

        # Return all statuses, defaulting to 0 for those not present
        all_statuses = ["completed", "in_progress", "in-progress", "initiated", "ringing", "failed", "no_answer", "no-answer", "busy", "canceled"]
        response = []
        seen = set()
        for s in all_statuses:
            count = status_counts.get(s, 0)
            if count > 0 or s in ("completed", "in_progress", "failed", "no_answer"):
                if s not in seen:
                    response.append({"status": s, "count": count})
                    seen.add(s)

        return response
    except Exception as e:
        logger.error(f"Failed to get calls by status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve calls by status"
        )


@router.get(
    "/analytics/calls-by-day",
    summary="Get calls by day",
    description="Get call statistics grouped by day"
)
async def get_calls_by_day(
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_current_user)
):
    """
    Get calls grouped by day
    """
    try:
        require_role(current_user, "superadmin")

        from datetime import datetime, timedelta

        call_service = CallService()
        today = datetime.utcnow()
        start_date = today - timedelta(days=days)

        # Aggregate calls by day across all companies
        pipeline = [
            {"$match": {"created_at": {"$gte": start_date}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        results = await call_service.calls_collection.aggregate(pipeline).to_list(length=days)
        day_counts = {r["_id"]: r["count"] for r in results}

        # Fill in all days (including days with 0 calls)
        result = []
        for i in range(days):
            date = (today - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            result.append({"date": date, "count": day_counts.get(date, 0)})

        return result
    except Exception as e:
        logger.error(f"Failed to get calls by day: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve calls by day"
        )


# Export router
__all__ = ["router"]
