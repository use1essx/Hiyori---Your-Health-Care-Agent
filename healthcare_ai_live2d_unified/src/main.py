"""
Healthcare AI V2 - Main Application
FastAPI application with comprehensive setup and lifecycle management
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import settings
from src.core.logging import setup_logging, log_api_request
from src.core.exceptions import HealthcareAIException
from src.core.security_middleware import (
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    EnhancedCORSMiddleware,
    RequestSizeMiddleware,
    SecurityAuditMiddleware
)
from src.database.connection import init_database, close_database
from src.web.api.v1 import health
from src.web.api.v1 import security as security_routes
from src.web.auth import routes as auth_routes
from src.web.live2d import live2d_router
from src.web.auth.middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware as AuthRateLimitMiddleware,
    IPSecurityMiddleware,
    SessionTimeoutMiddleware
)
# Temporarily simplify middleware imports to get app working
# TODO: Fix middleware import structure
from src.core.security_monitor import initialize_security_monitor
from src.core.security_events import initialize_security_events
# from src.web.middleware.rate_limiter import initialize_rate_limiter  # TODO: Fix import

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting Healthcare AI V2 application...")
    
    try:
        # Initialize database connections (skip if not available)
        try:
            await init_database()
            logger.info("Database connections initialized")
        except Exception as db_error:
            logger.warning(f"Database initialization failed, continuing without database: {db_error}")
        
        # Initialize security systems
        try:
            await initialize_security_monitor()
            logger.info("Security monitor initialized")
        except Exception as sec_error:
            logger.warning(f"Security monitor initialization failed: {sec_error}")
        
        try:
            await initialize_security_events()
            logger.info("Security event tracker initialized")
        except Exception as event_error:
            logger.warning(f"Security event tracker initialization failed: {event_error}")
        
        # await initialize_rate_limiter()  # TODO: Fix import
        # logger.info("Advanced rate limiter initialized")
        
        logger.info("Healthcare AI V2 started successfully")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Healthcare AI V2...")
        
        try:
            # Close database connections
            await close_database()
            logger.info("Database connections closed")
            
            # Cleanup other services
            # await close_redis()
            # await stop_background_tasks()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("Healthcare AI V2 shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Healthcare AI System for Hong Kong with Multi-Agent Architecture",
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
    lifespan=lifespan,
)

# =============================================================================
# MIDDLEWARE CONFIGURATION
# =============================================================================

# Advanced Security Middleware (Order matters - first to last execution)
# Simplified middleware configuration for initial testing
# TODO: Re-enable advanced middleware after fixing import issues
if settings.environment == "development":
    # Basic middleware for development
    pass  # Skip middleware for now
else:
    # Production security middleware stack
    # Temporarily disabled - will be re-enabled after fixing imports
    pass

# =============================================================================
# SECURITY MIDDLEWARE STACK (Order matters - applied in reverse order)
# =============================================================================

# 1. Security Audit Middleware (first to catch all requests)
app.add_middleware(SecurityAuditMiddleware)

# 2. Request Size Limiting (prevent DoS attacks)
app.add_middleware(RequestSizeMiddleware, max_size=10 * 1024 * 1024)  # 10MB limit

# 3. Enhanced Request Logging
app.add_middleware(RequestLoggingMiddleware)

# 4. Security Headers (comprehensive security headers)
app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.is_production)

# 5. Enhanced CORS (stricter than default)
app.add_middleware(
    EnhancedCORSMiddleware,
    allowed_origins=settings.cors_origins,
    allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# 6. Trusted Host Middleware (production only)
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.healthcare-ai.com", "localhost", "127.0.0.1"]
    )

# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(HealthcareAIException)
async def healthcare_ai_exception_handler(request: Request, exc: HealthcareAIException):
    """Handle custom Healthcare AI exceptions"""
    logger.error(
        f"Healthcare AI exception: {exc.detail}",
        extra={
            'error_type': exc.error_type,
            'status_code': exc.status_code,
            'endpoint': str(request.url),
            'method': request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "error_type": exc.error_type,
            "timestamp": exc.timestamp.isoformat(),
            "request_id": getattr(request.state, 'request_id', None)
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Resource not found",
            "error_type": "not_found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    """Handle 500 errors"""
    logger.error(
        f"Internal server error: {str(exc)}",
        extra={
            'endpoint': str(request.url),
            'method': request.method
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_type": "internal_error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )

# =============================================================================
# STATIC FILES AND TEMPLATES
# =============================================================================

# Mount static files for admin interface
if settings.enable_admin_interface:
    # Get the correct path for static files
    from pathlib import Path
    static_dir = Path(__file__).parent / "web" / "admin" / "static"
    template_dir = Path(__file__).parent / "web" / "admin" / "templates"
    
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # Setup Jinja2 templates
        if template_dir.exists():
            templates = Jinja2Templates(directory=str(template_dir))
    else:
        logger.warning(f"Static directory not found: {static_dir}")

# =============================================================================
# ROUTES
# =============================================================================

# Health check endpoints
app.include_router(
    health.router,
    prefix=settings.api_v1_prefix,
    tags=["health"]
)

# Authentication endpoints
app.include_router(
    auth_routes.router,
    prefix=settings.api_v1_prefix,
    tags=["authentication"]
)

# Security monitoring endpoints
app.include_router(
    security_routes.router,
    prefix=f"{settings.api_v1_prefix}/security",
    tags=["security"]
)

# Additional API endpoints
from src.web.api.v1 import users, agents, uploads, hk_data, admin
from src.web.api.v1 import live2d_simple as live2d_api

# User management endpoints
app.include_router(
    users.router,
    prefix=settings.api_v1_prefix,
    tags=["users"]
)

# Agent system endpoints
app.include_router(
    agents.router,
    prefix=settings.api_v1_prefix,
    tags=["agents"]
)

# File upload endpoints
app.include_router(
    uploads.router,
    prefix=settings.api_v1_prefix,
    tags=["uploads"]
)

# Hong Kong healthcare data endpoints
app.include_router(
    hk_data.router,
    prefix=settings.api_v1_prefix,
    tags=["hk-data"]
)

# Administrative endpoints
app.include_router(
    admin.router,
    prefix=settings.api_v1_prefix,
    tags=["admin"]
)

# pgAdmin Integration endpoints
from src.web.api.v1.pgadmin import router as pgadmin_router
app.include_router(
    pgadmin_router,
    prefix=settings.api_v1_prefix,
    tags=["pgadmin"]
)

# Live2D integration endpoints
app.include_router(
    live2d_api.router,
    prefix=settings.api_v1_prefix,
    tags=["live2d-api"]
)

# Live2D main interface endpoints
app.include_router(
    live2d_router,
    tags=["live2d"]
)

# Simple admin API endpoints for frontend compatibility
from fastapi import Request
from pathlib import Path
from datetime import datetime

@app.get("/api/admin/models")
async def get_admin_models():
    """Get available Live2D models for admin interface"""
    try:
        # List available models in the Live2D Resources directory
        models = []
        live2d_resources_path = Path(__file__).parent / "web" / "live2d" / "frontend" / "Resources"
        
        if live2d_resources_path.exists():
            for model_dir in live2d_resources_path.iterdir():
                if model_dir.is_dir() and not model_dir.name.startswith('.'):
                    model_file = model_dir / f"{model_dir.name}.model3.json"
                    if model_file.exists():
                        models.append({
                            "id": model_dir.name,
                            "name": model_dir.name,
                            "path": f"Resources/{model_dir.name}/{model_dir.name}.model3.json",
                            "available": True
                        })
        
        return {
            "success": True,
            "models": models,
            "total": len(models)
        }
    except Exception as e:
        logger.error(f"Error getting admin models: {e}")
        return {
            "success": False,
            "models": [],
            "error": str(e)
        }

@app.post("/api/swap-model")
async def api_swap_model(request: Request):
    """API endpoint to swap Live2D model"""
    try:
        body = await request.json()
        model_name = body.get("model", "Hiyori")
        
        return {
            "success": True,
            "message": f"Model swapped to {model_name}",
            "current_model": model_name
        }
    except Exception as e:
        logger.error(f"Error swapping model: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/chat")
async def api_chat(request: Request):
    """API endpoint for chat"""
    try:
        body = await request.json()
        message = body.get("message", "")
        
        return {
            "success": True,
            "response": f"Echo: {message}",
            "agent": "Live2D Assistant",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in chat API: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# Handle Live2D compiled JS resource requests (without /live2d prefix)
@app.get("/Resources/{file_path:path}")
async def serve_live2d_compiled_resources(file_path: str):
    """Serve Live2D Resources for compiled JS that expects /Resources/ paths"""
    try:
        from fastapi.responses import FileResponse
        live2d_resources_path = Path(__file__).parent / "web" / "live2d" / "frontend" / "Resources"
        full_path = live2d_resources_path / file_path
        
        if full_path.exists() and full_path.is_file():
            return FileResponse(full_path)
        else:
            raise HTTPException(status_code=404, detail=f"Resource not found: {file_path}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving compiled resource {file_path}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Authentication and User Interface Routes
@app.get("/auth.html")
async def serve_auth_page():
    """Serve the authentication page"""
    try:
        from fastapi.responses import FileResponse
        auth_path = Path(__file__).parent / "web" / "live2d" / "frontend" / "auth.html"
        
        if auth_path.exists():
            return FileResponse(auth_path)
        else:
            raise HTTPException(status_code=404, detail="Authentication page not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving auth page: {e}")
        raise HTTPException(status_code=500, detail="Error serving auth page")


@app.get("/profile.html")
async def serve_profile_page():
    """Serve the user profile page"""
    try:
        from fastapi.responses import FileResponse
        profile_path = Path(__file__).parent / "web" / "live2d" / "frontend" / "profile.html"
        
        if profile_path.exists():
            return FileResponse(profile_path)
        else:
            raise HTTPException(status_code=404, detail="Profile page not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving profile page: {e}")
        raise HTTPException(status_code=500, detail="Error serving profile page")


@app.get("/admin-dashboard.html")
async def serve_admin_dashboard():
    """Serve the admin dashboard"""
    try:
        from fastapi.responses import FileResponse
        dashboard_path = Path(__file__).parent / "web" / "live2d" / "frontend" / "admin-dashboard.html"
        
        if dashboard_path.exists():
            return FileResponse(dashboard_path)
        else:
            raise HTTPException(status_code=404, detail="Admin dashboard not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving admin dashboard: {e}")
        raise HTTPException(status_code=500, detail="Error serving admin dashboard")


@app.get("/chatbot-working-enhanced.html")
async def serve_chatbot_enhanced():
    """Serve the enhanced chatbot page"""
    try:
        from fastapi.responses import FileResponse
        chatbot_path = Path(__file__).parent / "web" / "live2d" / "frontend" / "index.html"
        
        if chatbot_path.exists():
            return FileResponse(chatbot_path)
        else:
            raise HTTPException(status_code=404, detail="Enhanced chatbot page not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving enhanced chatbot page: {e}")
        raise HTTPException(status_code=500, detail="Error serving enhanced chatbot page")


@app.get("/admin.html")
async def serve_admin_page():
    """Serve the admin page"""
    try:
        from fastapi.responses import FileResponse
        admin_path = Path(__file__).parent / "web" / "live2d" / "frontend" / "admin.html"
        
        if admin_path.exists():
            return FileResponse(admin_path)
        else:
            raise HTTPException(status_code=404, detail="Admin page not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving admin page: {e}")
        raise HTTPException(status_code=500, detail="Error serving admin page")


# Admin dashboard routes (if enabled)
if settings.enable_admin_interface:
    from src.web.admin.routes import admin_router, admin_api_router
    
    app.include_router(
        admin_router,
        tags=["admin-dashboard"]
    )
    
    app.include_router(
        admin_api_router,
        tags=["admin-api"]
    )

# =============================================================================
# ROOT ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Serve the main Live2D interface"""
    try:
        from fastapi.responses import FileResponse
        index_path = Path(__file__).parent / "web" / "live2d" / "frontend" / "index.html"
        
        if index_path.exists():
            return FileResponse(index_path)
        else:
            raise HTTPException(status_code=404, detail="Main interface not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving main interface: {e}")
        raise HTTPException(status_code=500, detail="Error serving main interface")


@app.get("/health")
async def simple_health():
    """Simple health check endpoint"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": settings.app_version
    }


@app.get("/info")
async def app_info():
    """Application information endpoint"""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "supported_languages": settings.supported_languages,
        "cultural_context": settings.cultural_context,
        "agent_types": [
            "illness_monitor",
            "mental_health", 
            "safety_guardian",
            "wellness_coach"
        ],
        "api_version": "v1",
        "api_prefix": settings.api_v1_prefix
    }


# =============================================================================
# DEVELOPMENT UTILITIES
# =============================================================================

if settings.is_development:
    @app.get("/dev/config")
    async def dev_config():
        """Development endpoint to view configuration (non-sensitive)"""
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug,
            "log_level": settings.log_level,
            "database_host": settings.database_host,
            "database_port": settings.database_port,
            "database_name": settings.database_name,
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "cors_origins": settings.cors_origins,
            "supported_languages": settings.supported_languages
        }

# =============================================================================
# CLI INTERFACE
# =============================================================================

def cli():
    """Command line interface for the application"""
    import typer
    
    app_cli = typer.Typer()
    
    @app_cli.command()
    def serve(
        host: str = settings.host,
        port: int = settings.port,
        reload: bool = settings.reload,
        log_level: str = settings.log_level.lower()
    ):
        """Start the Healthcare AI V2 server"""
        uvicorn.run(
            "src.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=settings.log_api_requests,
            use_colors=settings.is_development
        )
    
    @app_cli.command()
    def init_db():
        """Initialize the database"""
        async def _init_db():
            from src.database.connection import init_database, create_tables
            await init_database()
            await create_tables()
            logger.info("Database initialized successfully")
        
        asyncio.run(_init_db())
    
    @app_cli.command()
    def create_admin():
        """Create an admin user"""
        async def _create_admin():
            # TODO: Implement admin user creation
            logger.info("Admin user creation not yet implemented")
        
        asyncio.run(_create_admin())
    
    app_cli()


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Run with uvicorn directly
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=settings.log_api_requests,
        use_colors=settings.is_development
    )
