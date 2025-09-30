"""
Healthcare AI V2 - Custom Exceptions
Application-specific exceptions for better error handling
"""

from datetime import datetime
from typing import Any, Dict, Optional


class HealthcareAIException(Exception):
    """Base exception for Healthcare AI application"""
    
    def __init__(
        self,
        detail: str,
        status_code: int = 500,
        error_type: str = "healthcare_ai_error",
        context: Optional[Dict[str, Any]] = None
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_type = error_type
        self.context = context or {}
        self.timestamp = datetime.utcnow()
        super().__init__(self.detail)


class AuthenticationError(HealthcareAIException):
    """Authentication related errors"""
    
    def __init__(self, detail: str = "Authentication required", context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=401,
            error_type="authentication_error",
            context=context
        )


class AuthorizationError(HealthcareAIException):
    """Authorization related errors"""
    
    def __init__(self, detail: str = "Insufficient permissions", context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=403,
            error_type="authorization_error",
            context=context
        )


class ValidationError(HealthcareAIException):
    """Data validation errors"""
    
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=422,
            error_type="validation_error",
            context=context
        )


class NotFoundError(HealthcareAIException):
    """Resource not found errors"""
    
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=404,
            error_type="not_found_error",
            context=context
        )


class ConflictError(HealthcareAIException):
    """Resource conflict errors"""
    
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=409,
            error_type="conflict_error",
            context=context
        )


class RateLimitError(HealthcareAIException):
    """Rate limiting errors"""
    
    def __init__(self, detail: str = "Rate limit exceeded", context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=429,
            error_type="rate_limit_error",
            context=context
        )


class DatabaseError(HealthcareAIException):
    """Database related errors"""
    
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=500,
            error_type="database_error",
            context=context
        )


class ExternalAPIError(HealthcareAIException):
    """External API related errors"""
    
    def __init__(self, detail: str, service: str, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        context["service"] = service
        super().__init__(
            detail=detail,
            status_code=503,
            error_type="external_api_error",
            context=context
        )


class AgentError(HealthcareAIException):
    """Agent system related errors"""
    
    def __init__(self, detail: str, agent_type: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if agent_type:
            context["agent_type"] = agent_type
        super().__init__(
            detail=detail,
            status_code=500,
            error_type="agent_error",
            context=context
        )


class FileProcessingError(HealthcareAIException):
    """File processing related errors"""
    
    def __init__(self, detail: str, filename: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if filename:
            context["filename"] = filename
        super().__init__(
            detail=detail,
            status_code=422,
            error_type="file_processing_error",
            context=context
        )


class SecurityError(HealthcareAIException):
    """Security related errors"""
    
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=403,
            error_type="security_error",
            context=context
        )
