"""
User Management API Endpoints

This module provides comprehensive user management functionality including:
- User profile management
- User listing and search (admin only)
- User activation/deactivation (admin only)
- User preferences and settings
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError, AuthorizationError, ValidationError
from src.core.logging import get_logger, log_api_request
from src.core.security import InputSanitizer
from src.database.connection import get_async_db
from src.database.models_comprehensive import User
from src.database.repositories.user_repository import UserRepository
from src.web.auth.dependencies import get_current_user, require_role, require_permission, auth_rate_limit

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UserProfileResponse(BaseModel):
    """User profile response model"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    department: Optional[str] = None
    license_number: Optional[str] = None
    is_active: bool
    is_verified: bool
    language_preference: str
    timezone: str
    notification_preferences: Dict[str, Any]
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list item response model"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    department: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UpdateUserProfileRequest(BaseModel):
    """Update user profile request model"""
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")
    department: Optional[str] = Field(None, max_length=100, description="User's department")
    license_number: Optional[str] = Field(None, max_length=100, description="Professional license number")
    language_preference: Optional[str] = Field(None, pattern="^(en|zh-HK|zh-CN)$", description="Preferred language")
    timezone: Optional[str] = Field(None, max_length=50, description="User's timezone")
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification preferences")


class UpdateUserRequest(BaseModel):
    """Update user request model (admin only)"""
    full_name: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    license_number: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern="^(user|admin|medical_reviewer|data_manager|super_admin)$")
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    language_preference: Optional[str] = Field(None, pattern="^(en|zh-HK|zh-CN)$")
    timezone: Optional[str] = Field(None, max_length=50)


class UserSearchResponse(BaseModel):
    """User search response model"""
    users: List[UserListResponse]
    total: int
    page: int
    page_size: int
    pages: int


class UserStatsResponse(BaseModel):
    """User statistics response model"""
    total_users: int
    active_users: int
    inactive_users: int
    verified_users: int
    unverified_users: int
    users_by_role: Dict[str, int]
    recent_registrations: int
    recent_logins: int


# ============================================================================
# USER PROFILE ENDPOINTS
# ============================================================================

@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Get the profile information for the currently authenticated user",
    responses={
        200: {"description": "User profile retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "User not found"}
    }
)
async def get_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    _: None = Depends(auth_rate_limit)
) -> UserProfileResponse:
    """Get current user's profile information"""
    start_time = datetime.now()
    
    try:
        user_repo = UserRepository()
        user_with_permissions = await user_repo.get_with_permissions(current_user.id, db)
        
        if not user_with_permissions:
            raise NotFoundError("User profile not found")
        
        # Log successful API request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None
        )
        
        return UserProfileResponse.from_orm(user_with_permissions)
        
    except Exception as e:
        logger.error(f"Error retrieving user profile for user {current_user.id}: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=500,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        if isinstance(e, (NotFoundError, AuthorizationError, ValidationError)):
            raise e
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user profile"
        )


@router.put(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current user profile",
    description="Update the profile information for the currently authenticated user",
    responses={
        200: {"description": "User profile updated successfully"},
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        404: {"description": "User not found"}
    }
)
  # 10 updates per minute
async def update_current_user_profile(
    request: Request,
    user_data: UpdateUserProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
) -> UserProfileResponse:
    """Update current user's profile information"""
    start_time = datetime.now()
    
    try:
        # Sanitize input data
        sanitizer = InputSanitizer()
        update_data = {}
        
        for field, value in user_data.dict(exclude_unset=True).items():
            if value is not None:
                if isinstance(value, str):
                    sanitized_value = sanitizer.sanitize_string(value)
                    if sanitized_value != value:
                        logger.warning(f"Input sanitized for field {field}")
                    update_data[field] = sanitized_value
                else:
                    update_data[field] = value
        
        user_repo = UserRepository()
        
        # Update user profile
        if update_data:
            updated_user = await user_repo.update(current_user.id, update_data, db)
            if not updated_user:
                raise NotFoundError("User not found")
        else:
            updated_user = current_user
        
        # Get updated user with permissions
        user_with_permissions = await user_repo.get_with_permissions(updated_user.id, db)
        
        # Log successful update
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None
        )
        
        logger.info(f"User {current_user.id} updated their profile")
        
        return UserProfileResponse.from_orm(user_with_permissions)
        
    except Exception as e:
        logger.error(f"Error updating user profile for user {current_user.id}: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=500,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        if isinstance(e, (NotFoundError, AuthorizationError, ValidationError)):
            raise e
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user profile"
        )


# ============================================================================
# ADMIN USER MANAGEMENT ENDPOINTS
# ============================================================================

@router.get(
    "",
    response_model=UserSearchResponse,
    dependencies=[Depends(require_role("admin"))],
    summary="List users (Admin)",
    description="Get a paginated list of users with optional search and filtering",
    responses={
        200: {"description": "Users retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"}
    }
)
  # 20 calls per minute for admin
async def list_users(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for username, email, or full name"),
    role: Optional[str] = Query(None, description="Filter by user role"),
    active_only: bool = Query(default=False, description="Show only active users"),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_async_db)
) -> UserSearchResponse:
    """Get paginated list of users with search and filtering"""
    start_time = datetime.now()
    
    try:
        user_repo = UserRepository()
        
        # Build filters
        filters = {}
        if role:
            filters["role"] = role
        if active_only:
            filters["is_active"] = True
        
        # Get paginated results
        if search:
            # Sanitize search term
            sanitizer = InputSanitizer()
            safe_search = sanitizer.sanitize_string(search, max_length=100)
            users = await user_repo.search_users(
                search_term=safe_search,
                limit=page_size,
                offset=(page - 1) * page_size
            )
            total = len(users)  # For simplicity, using length of results
        else:
            result = await user_repo.get_paginated(
                page=page,
                page_size=page_size,
                filters=filters,
                order_by="created_at",
                order_desc=True,
                session=db
            )
            users = result["items"]
            total = result["total"]
        
        # Calculate pagination info
        pages = (total + page_size - 1) // page_size
        
        # Convert to response models
        user_list = [UserListResponse.from_orm(user) for user in users]
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None
        )
        
        return UserSearchResponse(
            users=user_list,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=500,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving users"
        )


@router.get(
    "/{user_id}",
    response_model=UserProfileResponse,
    dependencies=[Depends(require_role("admin"))],
    summary="Get user by ID (Admin)",
    description="Get detailed information about a specific user",
    responses={
        200: {"description": "User retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"}
    }
)

async def get_user_by_id(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_async_db)
) -> UserProfileResponse:
    """Get user by ID (admin only)"""
    start_time = datetime.now()
    
    try:
        user_repo = UserRepository()
        user = await user_repo.get_with_permissions(user_id, db)
        
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None
        )
        
        return UserProfileResponse.from_orm(user)
        
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=404 if isinstance(e, NotFoundError) else 500,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        if isinstance(e, NotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user"
        )


@router.put(
    "/{user_id}",
    response_model=UserProfileResponse,
    dependencies=[Depends(require_role("admin"))],
    summary="Update user (Admin)",
    description="Update user information (admin only)",
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"}
    }
)

async def update_user(
    request: Request,
    user_id: int,
    user_data: UpdateUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_async_db)
) -> UserProfileResponse:
    """Update user information (admin only)"""
    start_time = datetime.now()
    
    try:
        # Prevent admin from modifying super admin users unless they are super admin
        user_repo = UserRepository()
        target_user = await user_repo.get_by_id(user_id, db)
        
        if not target_user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        # Super admin protection
        if target_user.is_super_admin and not current_user.is_super_admin:
            raise AuthorizationError("Cannot modify super admin users")
        
        # Sanitize input data
        sanitizer = InputSanitizer()
        update_data = {}
        
        for field, value in user_data.dict(exclude_unset=True).items():
            if value is not None:
                if isinstance(value, str):
                    sanitized_value = sanitizer.sanitize_string(value)
                    if sanitized_value != value:
                        logger.warning(f"Input sanitized for field {field}")
                    update_data[field] = sanitized_value
                else:
                    update_data[field] = value
        
        # Update user
        if update_data:
            updated_user = await user_repo.update(user_id, update_data, db)
            if not updated_user:
                raise NotFoundError(f"User with ID {user_id} not found")
        else:
            updated_user = target_user
        
        # Get updated user with permissions
        user_with_permissions = await user_repo.get_with_permissions(updated_user.id, db)
        
        # Log successful update
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None
        )
        
        logger.info(f"Admin {current_user.id} updated user {user_id}")
        
        return UserProfileResponse.from_orm(user_with_permissions)
        
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=500,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        if isinstance(e, (NotFoundError, AuthorizationError, ValidationError)):
            status_code = status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_403_FORBIDDEN
            raise HTTPException(status_code=status_code, detail=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )


@router.post(
    "/{user_id}/activate",
    dependencies=[Depends(require_role("admin"))],
    summary="Activate user (Admin)",
    description="Activate a user account",
    responses={
        200: {"description": "User activated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"}
    }
)

async def activate_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, str]:
    """Activate a user account"""
    start_time = datetime.now()
    
    try:
        user_repo = UserRepository()
        success = await user_repo.activate_user(user_id)
        
        if not success:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        # Log successful activation
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None
        )
        
        logger.info(f"Admin {current_user.id} activated user {user_id}")
        
        return {"message": f"User {user_id} activated successfully"}
        
    except Exception as e:
        logger.error(f"Error activating user {user_id}: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=404 if isinstance(e, NotFoundError) else 500,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        if isinstance(e, NotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error activating user"
        )


@router.post(
    "/{user_id}/deactivate",
    dependencies=[Depends(require_role("admin"))],
    summary="Deactivate user (Admin)",
    description="Deactivate a user account",
    responses={
        200: {"description": "User deactivated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"}
    }
)

async def deactivate_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, str]:
    """Deactivate a user account"""
    start_time = datetime.now()
    
    try:
        # Prevent deactivating self or super admins
        if user_id == current_user.id:
            raise AuthorizationError("Cannot deactivate your own account")
        
        user_repo = UserRepository()
        target_user = await user_repo.get_by_id(user_id, db)
        
        if not target_user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        if target_user.is_super_admin:
            raise AuthorizationError("Cannot deactivate super admin users")
        
        success = await user_repo.deactivate_user(user_id)
        
        if not success:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        # Log successful deactivation
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None
        )
        
        logger.info(f"Admin {current_user.id} deactivated user {user_id}")
        
        return {"message": f"User {user_id} deactivated successfully"}
        
    except Exception as e:
        logger.error(f"Error deactivating user {user_id}: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=500,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        if isinstance(e, (NotFoundError, AuthorizationError)):
            status_code = status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundError) else status.HTTP_403_FORBIDDEN
            raise HTTPException(status_code=status_code, detail=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deactivating user"
        )


@router.get(
    "/stats",
    response_model=UserStatsResponse,
    dependencies=[Depends(require_role("admin"))],
    summary="Get user statistics (Admin)",
    description="Get comprehensive user statistics for admin dashboard",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"}
    }
)

async def get_user_statistics(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_async_db)
) -> UserStatsResponse:
    """Get user statistics for admin dashboard"""
    start_time = datetime.now()
    
    try:
        user_repo = UserRepository()
        stats = await user_repo.get_user_statistics()
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None
        )
        
        return UserStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error retrieving user statistics: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=500,
            response_time_ms=processing_time,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user statistics"
        )
