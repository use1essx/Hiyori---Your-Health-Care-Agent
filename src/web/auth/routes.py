"""
Healthcare AI V2 - Authentication Routes
FastAPI endpoints for user authentication, registration, and account management
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from src.core.exceptions import AuthenticationError, SecurityError, ValidationError
from src.core.logging import get_logger, log_security_event
from src.database.models_comprehensive import User, UserSession
from src.database.repositories.user_repository import UserRepository, UserSessionRepository
from src.web.auth.dependencies import (
    auth_rate_limit,
    get_current_active_user,
    get_current_session,
    get_current_user,
    get_token_from_header,
    require_admin,
    validate_session_ownership,
    validate_user_ownership,
)
from src.web.auth.handlers import auth_handler
from src.web.auth.schemas import (
    AccountSecurityResponse,
    AuthStatusResponse,
    BulkUserRequest,
    BulkUserResponse,
    ChangePasswordRequest,
    ErrorResponse,
    LogoutResponse,
    PasswordPolicyResponse,
    PasswordValidationResponse,
    SecurityEventResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    TwoFactorSetupRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    UserLoginRequest,
    UserPermissionResponse,
    UserRegisterRequest,
    UserResponse,
    UserSessionResponse,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        403: {"model": ErrorResponse, "description": "Access forbidden"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    }
)

# Repository instances
user_repo = UserRepository()
session_repo = UserSessionRepository()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
    summary="Register new user",
    description="Create a new user account with email verification"
)
async def register_user(
    request: Request,
    user_data: UserRegisterRequest
) -> UserResponse:
    """
    Register a new user account
    
    Creates a new user with the provided information. The account will require
    email verification before full access is granted.
    """
    try:
        client_ip = _get_client_ip(request)
        
        # Register user
        user = await auth_handler.register_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name,
            department=user_data.department,
            license_number=user_data.license_number,
            organization=user_data.organization,
            language_preference=user_data.language_preference,
            timezone=user_data.timezone
        )
        
        # Log registration
        log_security_event(
            event_type="user_registration",
            description=f"New user registered: {user_data.email}",
            ip_address=client_ip,
            risk_level="low"
        )
        
        return user
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.detail
        )
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.detail
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(auth_rate_limit)],
    summary="User login",
    description="Authenticate user and return JWT tokens"
)
async def login_user(
    request: Request,
    login_data: UserLoginRequest
) -> TokenResponse:
    """
    Authenticate user and return access/refresh tokens
    
    Validates user credentials and returns JWT tokens for API access.
    Failed attempts are tracked and may result in account lockout.
    """
    try:
        client_ip = _get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        
        # Authenticate user
        token_response = await auth_handler.authenticate_user(
            email_or_username=login_data.email_or_username,
            password=login_data.password,
            ip_address=client_ip,
            user_agent=user_agent,
            remember_me=login_data.remember_me
        )
        
        return token_response
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail
        )
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=e.detail
        )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    dependencies=[Depends(auth_rate_limit)],
    summary="Refresh access token",
    description="Generate new access token using refresh token"
)
async def refresh_token(
    request: Request,
    refresh_data: TokenRefreshRequest
) -> TokenRefreshResponse:
    """
    Refresh access token using valid refresh token
    
    Generates a new access token when the current one expires.
    The refresh token remains valid until its own expiration.
    """
    try:
        client_ip = _get_client_ip(request)
        
        # Refresh token
        token_data = await auth_handler.refresh_token(
            refresh_token=refresh_data.refresh_token,
            ip_address=client_ip
        )
        
        return TokenRefreshResponse(**token_data)
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="User logout",
    description="Logout user and revoke tokens"
)
async def logout_user(
    request: Request,
    logout_all: bool = False,
    current_user: User = Depends(get_current_user),
    token: str = Depends(get_token_from_header)
) -> LogoutResponse:
    """
    Logout user and revoke authentication tokens
    
    Revokes the current session or optionally all sessions for the user.
    """
    try:
        client_ip = _get_client_ip(request)
        
        # Logout user
        logout_data = await auth_handler.logout_user(
            access_token=token,
            ip_address=client_ip,
            logout_all=logout_all
        )
        
        return LogoutResponse(**logout_data)
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user information"
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current authenticated user information
    
    Returns detailed information about the currently authenticated user.
    """
    return UserResponse.model_validate(current_user)


@router.get(
    "/profile",
    response_model=UserResponse,
    summary="Get user profile",
    description="Get current user profile including health data"
)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current user profile with health data
    
    Returns detailed user information including health profile for the profile page.
    """
    return UserResponse.model_validate(current_user)


@router.get(
    "/status",
    response_model=AuthStatusResponse,
    summary="Get authentication status", 
    description="Get detailed authentication and authorization status"
)
async def get_auth_status(
    current_user: User = Depends(get_current_user),
    current_session: UserSession = Depends(get_current_session)
) -> AuthStatusResponse:
    """
    Get comprehensive authentication status
    
    Returns authentication status, user info, permissions, and session details.
    """
    # Get user permissions (simplified - in full implementation, load from database)
    permissions = []
    
    # Get session info
    session_response = UserSessionResponse.model_validate(current_session)
    
    return AuthStatusResponse(
        authenticated=True,
        user=UserResponse.model_validate(current_user),
        permissions=permissions,
        session=session_response,
        requires_2fa=current_user.two_factor_enabled and False  # Check if 2FA verification needed
    )


@router.put(
    "/change-password",
    summary="Change password",
    description="Change user password with current password verification"
)
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Change user password
    
    Requires current password verification and validates new password strength.
    All sessions will be revoked upon successful password change.
    """
    try:
        client_ip = _get_client_ip(request)
        
        # Change password
        result = await auth_handler.change_password(
            user_id=current_user.id,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
            ip_address=client_ip
        )
        
        return result
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.detail
        )


@router.post(
    "/validate-password",
    response_model=PasswordValidationResponse,
    summary="Validate password strength",
    description="Check password strength without storing"
)
async def validate_password(
    password: str,
    current_user: Optional[User] = Depends(get_current_user)
) -> PasswordValidationResponse:
    """
    Validate password strength and security requirements
    
    Checks password against security policies and provides feedback
    for improvement without storing the password.
    """
    user_info = None
    if current_user:
        user_info = {
            "email": current_user.email,
            "username": current_user.username,
            "full_name": current_user.full_name
        }
    
    return auth_handler.validate_password_strength(password, user_info)


@router.get(
    "/password-policy",
    response_model=PasswordPolicyResponse,
    summary="Get password policy",
    description="Get current password policy requirements"
)
async def get_password_policy() -> PasswordPolicyResponse:
    """
    Get password policy requirements
    
    Returns the current password policy configuration including
    minimum length, character requirements, and forbidden patterns.
    """
    return PasswordPolicyResponse(
        min_length=8,
        require_uppercase=True,
        require_lowercase=True,
        require_numbers=True,
        require_special_chars=True,
        forbidden_patterns=["password", "123456", "qwerty"],
        expiry_days=None
    )


@router.get(
    "/sessions",
    response_model=List[UserSessionResponse],
    summary="Get user sessions",
    description="Get all active sessions for current user"
)
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user)
) -> List[UserSessionResponse]:
    """
    Get all active sessions for the current user
    
    Returns list of active sessions including device info and last activity.
    """
    sessions = await session_repo.get_active_sessions(current_user.id)
    return [UserSessionResponse.model_validate(session) for session in sessions]


@router.delete(
    "/sessions/{session_id}",
    summary="Revoke user session",
    description="Revoke a specific user session"
)
async def revoke_session(
    session_id: int,
    session: UserSession = Depends(validate_session_ownership)
) -> Dict:
    """
    Revoke a specific user session
    
    Terminates the specified session. Users can only revoke their own sessions.
    """
    success = await session_repo.revoke_session(session_id, "user_requested")
    
    if success:
        return {"message": "Session revoked successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke session"
        )


@router.delete(
    "/sessions",
    summary="Revoke all sessions",
    description="Revoke all sessions except current"
)
async def revoke_all_sessions(
    current_session: UserSession = Depends(get_current_session),
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Revoke all user sessions except the current one
    
    Terminates all other active sessions for the user.
    """
    revoked_count = await session_repo.revoke_all_sessions(
        current_user.id,
        except_session_id=current_session.id
    )
    
    return {
        "message": "Sessions revoked successfully",
        "revoked_count": revoked_count
    }


@router.get(
    "/security",
    response_model=AccountSecurityResponse,
    summary="Get account security info",
    description="Get account security status and recent events"
)
async def get_account_security(
    current_user: User = Depends(get_current_active_user)
) -> AccountSecurityResponse:
    """
    Get account security information
    
    Returns security status, recent events, active sessions, and 2FA status.
    """
    # Check if account is locked
    is_locked = await user_repo.is_account_locked(current_user.id)
    
    # Get active sessions
    sessions = await session_repo.get_active_sessions(current_user.id)
    session_responses = [UserSessionResponse.model_validate(s) for s in sessions]
    
    # Get recent security events (simplified - in production, query audit logs)
    recent_events = []
    
    return AccountSecurityResponse(
        account_locked=is_locked,
        lockout_expires=current_user.account_locked_until,
        failed_attempts=current_user.failed_login_attempts,
        last_login=current_user.last_login,
        recent_events=recent_events,
        active_sessions=session_responses,
        two_factor_enabled=current_user.two_factor_enabled
    )


# 2FA endpoints (setup for future implementation)
@router.post(
    "/2fa/setup",
    response_model=TwoFactorSetupResponse,
    summary="Setup two-factor authentication",
    description="Initialize 2FA setup for user account"
)
async def setup_two_factor(
    setup_data: TwoFactorSetupRequest,
    current_user: User = Depends(get_current_active_user)
) -> TwoFactorSetupResponse:
    """
    Setup two-factor authentication
    
    Initializes 2FA for the user account with QR code and backup codes.
    This endpoint is prepared for future 2FA implementation.
    """
    # TODO: Implement 2FA setup logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Two-factor authentication not yet implemented"
    )


@router.post(
    "/2fa/verify",
    summary="Verify two-factor authentication",
    description="Verify 2FA code during authentication"
)
async def verify_two_factor(
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Verify two-factor authentication code
    
    Verifies 2FA code during authentication process.
    This endpoint is prepared for future 2FA implementation.
    """
    # TODO: Implement 2FA verification logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Two-factor authentication not yet implemented"
    )


@router.delete(
    "/2fa/disable",
    summary="Disable two-factor authentication",
    description="Disable 2FA for user account"
)
async def disable_two_factor(
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Disable two-factor authentication
    
    Disables 2FA for the user account after password verification.
    This endpoint is prepared for future 2FA implementation.
    """
    # TODO: Implement 2FA disable logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Two-factor authentication not yet implemented"
    )


# Admin endpoints
@router.get(
    "/admin/users",
    response_model=List[UserResponse],
    dependencies=[Depends(require_admin)],
    summary="Get all users (Admin only)",
    description="Get list of all users - admin access required"
)
async def get_all_users(
    limit: int = 50,
    offset: int = 0,
    active_only: bool = False
) -> List[UserResponse]:
    """
    Get all users (admin only)
    
    Returns paginated list of all users. Requires admin access.
    """
    filters = {"is_active": True} if active_only else {}
    users = await user_repo.get_filtered(
        filters=filters,
        limit=limit,
        offset=offset,
        order_by="created_at",
        order_desc=True
    )
    
    return [UserResponse.model_validate(user) for user in users]


@router.get(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_admin)],
    summary="Get user by ID (Admin only)",
    description="Get specific user information - admin access required"
)
async def get_user_by_id(
    user_id: int,
    target_user: User = Depends(validate_user_ownership)
) -> UserResponse:
    """
    Get user by ID (admin only)
    
    Returns detailed information for a specific user. Requires admin access.
    """
    return UserResponse.model_validate(target_user)


@router.put(
    "/admin/users/{user_id}/activate",
    dependencies=[Depends(require_admin)],
    summary="Activate user (Admin only)",
    description="Activate user account - admin access required"
)
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_admin)
) -> Dict:
    """
    Activate user account (admin only)
    
    Activates a deactivated user account. Requires admin access.
    """
    success = await user_repo.activate_user(user_id)
    
    if success:
        log_security_event(
            event_type="user_activated",
            description=f"User {user_id} activated by admin {current_user.id}",
            user_id=current_user.id,
            risk_level="medium"
        )
        return {"message": "User activated successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to activate user"
        )


@router.put(
    "/admin/users/{user_id}/deactivate", 
    dependencies=[Depends(require_admin)],
    summary="Deactivate user (Admin only)",
    description="Deactivate user account - admin access required"
)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(require_admin)
) -> Dict:
    """
    Deactivate user account (admin only)
    
    Deactivates a user account and revokes all sessions. Requires admin access.
    """
    success = await user_repo.deactivate_user(user_id)
    
    if success:
        # Revoke all user sessions
        await session_repo.revoke_all_sessions(user_id)
        
        log_security_event(
            event_type="user_deactivated",
            description=f"User {user_id} deactivated by admin {current_user.id}",
            user_id=current_user.id,
            risk_level="high"
        )
        return {"message": "User deactivated successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to deactivate user"
        )


@router.post(
    "/admin/users/bulk",
    response_model=BulkUserResponse,
    dependencies=[Depends(require_admin)],
    summary="Bulk user operations (Admin only)",
    description="Perform bulk operations on users - admin access required"
)
async def bulk_user_operations(
    bulk_request: BulkUserRequest,
    current_user: User = Depends(require_admin)
) -> BulkUserResponse:
    """
    Perform bulk operations on users (admin only)
    
    Supports bulk activation, deactivation, and other user management operations.
    Requires admin access.
    """
    # TODO: Implement bulk operations
    return BulkUserResponse(
        total_requested=len(bulk_request.user_ids),
        successful=0,
        failed=len(bulk_request.user_ids),
        errors=["Bulk operations not yet implemented"]
    )


def _get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for forwarded headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
        
    forwarded = request.headers.get("X-Real-IP")
    if forwarded:
        return forwarded
        
    return request.client.host if request.client else "unknown"


# Export router
__all__ = ["router"]
