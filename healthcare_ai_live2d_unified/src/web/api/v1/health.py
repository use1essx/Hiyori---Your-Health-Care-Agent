"""
Healthcare AI V2 - Health Check Endpoints
System health monitoring and status endpoints
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.database.connection import check_database_health
from src.core.logging import get_logger
from src.core.api_security import APIKeyManager, log_api_operation
from src.web.auth.dependencies import get_optional_user

logger = get_logger(__name__)
router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model"""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    checks: Dict[str, Any]


class DetailedHealthStatus(BaseModel):
    """Detailed health status response model"""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    system_info: Dict[str, Any]
    database: Dict[str, Any]
    external_services: Dict[str, Any]
    performance_metrics: Dict[str, Any]


# Track application start time
app_start_time = time.time()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Basic health check endpoint
    Returns simple status for load balancers and monitoring
    """
    try:
        # Quick database check
        db_status = await check_database_health()
        
        # Determine overall status
        overall_status = "healthy"
        if db_status["status"] != "healthy":
            overall_status = "unhealthy"
        
        uptime = time.time() - app_start_time
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            environment=settings.environment,
            uptime_seconds=uptime,
            checks={
                "database": db_status["status"],
                "api": "healthy"
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        )


@router.get("/health/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check():
    """
    Detailed health check endpoint
    Returns comprehensive system status information
    """
    try:
        start_time = time.time()
        
        # Gather all health information
        db_health, system_info, external_services = await asyncio.gather(
            check_database_health(),
            get_system_info(),
            check_external_services(),
            return_exceptions=True
        )
        
        # Handle exceptions in parallel tasks
        if isinstance(db_health, Exception):
            logger.error(f"Database health check failed: {db_health}")
            db_health = {"status": "unhealthy", "error": str(db_health)}
        
        if isinstance(system_info, Exception):
            logger.error(f"System info gathering failed: {system_info}")
            system_info = {"error": str(system_info)}
        
        if isinstance(external_services, Exception):
            logger.error(f"External services check failed: {external_services}")
            external_services = {"error": str(external_services)}
        
        # Calculate performance metrics
        check_duration = time.time() - start_time
        uptime = time.time() - app_start_time
        
        performance_metrics = {
            "health_check_duration_ms": int(check_duration * 1000),
            "uptime_seconds": uptime,
            "uptime_human": format_duration(uptime)
        }
        
        # Determine overall status
        overall_status = "healthy"
        if db_health.get("status") != "healthy":
            overall_status = "unhealthy"
        elif any(service.get("status") == "unhealthy" for service in external_services.values() if isinstance(service, dict)):
            overall_status = "degraded"
        
        return DetailedHealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            environment=settings.environment,
            uptime_seconds=uptime,
            system_info=system_info,
            database=db_health,
            external_services=external_services,
            performance_metrics=performance_metrics
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        )


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint
    Returns 200 if the application is running
    """
    return {"status": "alive", "timestamp": datetime.utcnow()}


@router.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint
    Returns 200 if the application is ready to serve requests
    """
    try:
        # Check critical dependencies
        db_health = await check_database_health()
        
        if db_health["status"] != "healthy":
            raise HTTPException(
                status_code=503,
                detail="Database not ready"
            )
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow(),
            "checks": {
                "database": "ready"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service not ready"
        )


@router.get("/health/startup")
async def startup_probe():
    """
    Kubernetes startup probe endpoint
    Returns 200 when the application has finished starting up
    """
    try:
        # Check if application has been running for at least 10 seconds
        uptime = time.time() - app_start_time
        if uptime < 10:
            raise HTTPException(
                status_code=503,
                detail="Application still starting up"
            )
        
        # Check database connection
        db_health = await check_database_health()
        if not db_health["async_connection"] or not db_health["sync_connection"]:
            raise HTTPException(
                status_code=503,
                detail="Database connections not established"
            )
        
        return {
            "status": "started",
            "timestamp": datetime.utcnow(),
            "uptime_seconds": uptime
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Startup check failed"
        )


async def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    import psutil
    import platform
    
    try:
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.architecture()[0],
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {"error": str(e)}


async def check_external_services() -> Dict[str, Any]:
    """Check external service health"""
    services = {}
    
    # TODO: Add checks for external services
    # For now, return placeholder
    services["openai_api"] = {
        "status": "unknown",
        "message": "Not implemented yet"
    }
    
    services["hk_government_apis"] = {
        "status": "unknown", 
        "message": "Not implemented yet"
    }
    
    return services


@router.get("/api-key-status")
async def api_key_status(current_user = Depends(get_optional_user)) -> Dict[str, Any]:
    """
    Check API key configuration status without exposing sensitive data
    Available to both authenticated and anonymous users
    """
    try:
        # Get secure API key status
        status = APIKeyManager.get_safe_status()
        
        # Log the check (without exposing sensitive data)
        log_api_operation(
            operation="api_key_status_check",
            success=True,
            details=f"Status check by {'authenticated' if current_user else 'anonymous'} user"
        )
        
        # Return safe status information
        return {
            "configured": status["configured"],
            "format_valid": status["format_valid"],
            "status": status["status"],
            "key_prefix": status["key_prefix"],
            "key_suffix": status["key_suffix"],
            "key_length": status["key_length"],
            "source": status["source"],
            "last_checked": status["last_checked"],
            "message": _get_status_message(status["status"])
        }
        
    except Exception as e:
        logger.error(f"API key status check failed: {e}")
        log_api_operation(
            operation="api_key_status_check",
            success=False,
            details=f"Error: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Could not check API key status")


def _get_status_message(status: str) -> str:
    """Get user-friendly status message"""
    messages = {
        "configured": "API key is properly configured and ready to use",
        "not_configured": "API key not found. Please set OPENROUTER_API_KEY environment variable",
        "invalid_format": "API key format appears invalid. Expected format: sk-or-v1-..."
    }
    return messages.get(status, f"Unknown status: {status}")


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    duration = timedelta(seconds=int(seconds))
    
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)
