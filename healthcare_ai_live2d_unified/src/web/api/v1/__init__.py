"""
API v1 Router Registration

This module centralizes all API v1 endpoint routers and provides
a single router for inclusion in the main FastAPI application.
"""

from fastapi import APIRouter

from src.web.api.v1 import health, security, users, agents, uploads, hk_data, admin

# Create main v1 router
router = APIRouter()

# Include all endpoint routers
router.include_router(health.router, tags=["health"])
router.include_router(security.router, prefix="/security", tags=["security"])
router.include_router(users.router, tags=["users"])  
router.include_router(agents.router, tags=["agents"])
router.include_router(uploads.router, tags=["uploads"])
router.include_router(hk_data.router, tags=["hk-data"])
router.include_router(admin.router, tags=["admin"])
