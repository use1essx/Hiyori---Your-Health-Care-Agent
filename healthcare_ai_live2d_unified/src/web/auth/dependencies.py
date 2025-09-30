"""
Healthcare AI V2 - Authentication Dependencies
FastAPI dependencies for authentication and authorization
"""

from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.exceptions import AuthenticationError, AuthorizationError
from src.core.logging import get_logger
from src.database.models_comprehensive import User, UserSession
from src.database.repositories.user_repository import UserRepository, UserSessionRepository
from src.web.auth.handlers import permission_checker, token_validator

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="JWT Bearer token for authentication"
)

# Repository instances
user_repo = UserRepository()
session_repo = UserSessionRepository()


async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract JWT token from Authorization header
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        JWT token string
        
    Raises:
        HTTPException: If token is missing or invalid format
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


async def get_current_user(
    request: Request,
    token: str = Depends(get_token_from_header)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        request: FastAPI request object
        token: JWT access token
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Validate and decode token
        payload = token_validator.decode_token(token)
        user_id = int(payload.get("sub"))
        
        # Get user from database
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Check if account is locked
        if await user_repo.is_account_locked(user.id):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Verify session exists and is active
        session = await session_repo.get_by_field("session_token", token)
        if not session or not session.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Update session activity
        await session_repo.update_activity(session.id)
        
        # Store user in request state for logging
        request.state.current_user = user
        request.state.current_session = session
        
        return user
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(request: Request) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    This allows endpoints to work for both authenticated and anonymous users.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Current authenticated user or None
    """
    try:
        # Try to get authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
            
        # Extract token
        token = auth_header.split(" ")[1]
        if not token:
            return None
            
        # Try to validate token and get user
        payload = token_validator.decode_token(token)
        user_id = int(payload.get("sub"))
        
        user = await user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            return None
            
        # Check if account is locked
        if await user_repo.is_account_locked(user.id):
            return None
            
        # Store user in request state for logging
        request.state.current_user = user
        
        return user
        
    except Exception as e:
        # Log the error but don't fail - return None for anonymous access
        logger.debug(f"Optional authentication failed: {e}")
        return None


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional verification)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active"
        )
    
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current verified user
    
    Args:
        current_user: Current active user
        
    Returns:
        Current verified user
        
    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    return current_user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None
    
    Args:
        request: FastAPI request object
        credentials: Optional HTTP authorization credentials
        
    Returns:
        Current user if authenticated, None otherwise
    """
    if not credentials or not credentials.credentials:
        return None
        
    try:
        return await get_current_user(request, credentials.credentials)
    except HTTPException:
        return None


# Role-based dependencies
def require_role(required_role: str):
    """
    Create dependency that requires specific role or higher
    
    Args:
        required_role: Minimum required role
        
    Returns:
        FastAPI dependency function
    """
    async def role_dependency(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not permission_checker.has_role_level(current_user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role or higher"
            )
        return current_user
    
    return role_dependency


def require_permission(required_permission: str):
    """
    Create dependency that requires specific permission
    
    Args:
        required_permission: Required permission
        
    Returns:
        FastAPI dependency function
    """
    async def permission_dependency(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not permission_checker.has_permission(current_user.role, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {required_permission}"
            )
        return current_user
    
    return permission_dependency


def require_resource_access(resource: str, action: str):
    """
    Create dependency that checks resource access permissions
    
    Args:
        resource: Resource name
        action: Action to perform
        
    Returns:
        FastAPI dependency function
    """
    async def resource_dependency(
        request: Request,
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # Extract resource owner ID from path parameters if available
        resource_owner_id = None
        if hasattr(request, "path_params"):
            resource_owner_id = request.path_params.get("user_id")
            if resource_owner_id:
                try:
                    resource_owner_id = int(resource_owner_id)
                except (ValueError, TypeError):
                    resource_owner_id = None
        
        # Check access permission
        has_access = permission_checker.can_access_resource(
            user_role=current_user.role,
            resource=resource,
            action=action,
            resource_owner_id=resource_owner_id,
            user_id=current_user.id
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot {action} {resource}"
            )
            
        return current_user
    
    return resource_dependency


# Specific role dependencies (commonly used)
require_admin = require_role("admin")
require_medical_reviewer = require_role("medical_reviewer")
require_data_manager = require_role("data_manager")
require_super_admin = require_role("super_admin")

# Specific permission dependencies
require_view_users = require_permission("view_users")
require_manage_users = require_permission("manage_users")
require_view_conversations = require_permission("view_conversations")
require_moderate_conversations = require_permission("moderate_conversations")
require_upload_documents = require_permission("upload_documents")
require_review_documents = require_permission("review_documents")
require_approve_documents = require_permission("approve_documents")
require_view_audit_logs = require_permission("view_audit_logs")
require_manage_system = require_permission("manage_system")


async def get_current_session(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> UserSession:
    """
    Get current user session
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Current user session
        
    Raises:
        HTTPException: If session not found
    """
    if hasattr(request.state, "current_session"):
        return request.state.current_session
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session not found"
    )


async def validate_session_ownership(
    session_id: int,
    current_user: User = Depends(get_current_user)
) -> UserSession:
    """
    Validate that current user owns the specified session
    
    Args:
        session_id: Session ID to validate
        current_user: Current authenticated user
        
    Returns:
        User session if owned by current user
        
    Raises:
        HTTPException: If session not found or not owned by user
    """
    session = await session_repo.get_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other user's session"
        )
        
    return session


async def validate_user_ownership(
    user_id: int,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Validate that current user can access specified user
    
    Args:
        user_id: User ID to validate access for
        current_user: Current authenticated user
        
    Returns:
        Target user if access is allowed
        
    Raises:
        HTTPException: If access is denied
    """
    # Users can always access their own data
    if user_id == current_user.id:
        return current_user
        
    # Admins can access other users
    if permission_checker.has_role_level(current_user.role, "admin"):
        target_user = await user_repo.get_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return target_user
        
    # Other users cannot access different user data
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Cannot access other user's data"
    )


# Rate limiting dependency
class RateLimitChecker:
    """Rate limiting dependency"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # In production, use Redis
        
    def __call__(self, request: Request) -> None:
        """
        Check rate limit for request
        
        Args:
            request: FastAPI request object
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)
        now = datetime.utcnow()
        
        # Clean old requests (simplified in-memory implementation)
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if (now - req_time).total_seconds() < self.window_seconds
            ]
        else:
            self.requests[client_ip] = []
            
        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now.timestamp()) + self.window_seconds)
                }
            )
            
        # Record request
        self.requests[client_ip].append(now)
        
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
            
        forwarded = request.headers.get("X-Real-IP")
        if forwarded:
            return forwarded
            
        return request.client.host if request.client else "unknown"


# Rate limiting instances for different endpoints
auth_rate_limit = RateLimitChecker(max_requests=5, window_seconds=60)  # 5 auth attempts per minute
api_rate_limit = RateLimitChecker(max_requests=100, window_seconds=60)  # 100 API calls per minute
upload_rate_limit = RateLimitChecker(max_requests=10, window_seconds=300)  # 10 uploads per 5 minutes


# Export dependencies
__all__ = [
    # Core dependencies
    "get_token_from_header",
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "get_optional_user",
    "get_current_session",
    
    # Role dependencies
    "require_role",
    "require_admin",
    "require_medical_reviewer",
    "require_data_manager",
    "require_super_admin",
    
    # Permission dependencies
    "require_permission",
    "require_resource_access",
    "require_view_users",
    "require_manage_users",
    "require_view_conversations",
    "require_moderate_conversations",
    "require_upload_documents",
    "require_review_documents",
    "require_approve_documents",
    "require_view_audit_logs",
    "require_manage_system",
    
    # Validation dependencies
    "validate_session_ownership",
    "validate_user_ownership",
    
    # Rate limiting
    "RateLimitChecker",
    "auth_rate_limit",
    "api_rate_limit",
    "upload_rate_limit",
]
