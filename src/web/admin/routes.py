# src/web/admin/routes.py
from fastapi import APIRouter, Request, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any, Optional
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.web.auth.dependencies import require_admin, require_permission
from src.database.models_comprehensive import User
from src.config import get_settings

# Initialize templates
templates = Jinja2Templates(directory="src/web/admin/templates")
logger = logging.getLogger(__name__)
settings = get_settings()

# Create admin router
admin_router = APIRouter(prefix="/admin", tags=["admin"])
admin_api_router = APIRouter(prefix="/api/v1/admin", tags=["admin-api"])

# WebSocket connection manager for real-time updates
class AdminWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        logger.info(f"Admin WebSocket connected: user_id={user_id}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            user_info = self.connection_info.pop(websocket, {})
            logger.info(f"Admin WebSocket disconnected: user_id={user_info.get('user_id')}")
    
    async def send_to_all(self, data: Dict[str, Any]):
        """Send data to all connected admin clients"""
        if not self.active_connections:
            return
        
        message = json.dumps(data)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_to_user(self, user_id: int, data: Dict[str, Any]):
        """Send data to specific user"""
        message = json.dumps(data)
        for connection, info in self.connection_info.items():
            if info["user_id"] == user_id:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "user_id": info["user_id"],
                    "connected_at": info["connected_at"].isoformat(),
                    "duration_seconds": (datetime.utcnow() - info["connected_at"]).total_seconds()
                }
                for info in self.connection_info.values()
            ]
        }

# Global WebSocket manager
ws_manager = AdminWebSocketManager()

# Dashboard metrics collector
class DashboardMetrics:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 30  # 30 seconds cache
        self.last_update = {}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get all dashboard metrics"""
        now = datetime.utcnow()
        
        # Check if cache is still valid
        if "overview" in self.cache and "overview" in self.last_update:
            if (now - self.last_update["overview"]).total_seconds() < self.cache_ttl:
                return self.cache["overview"]
        
        # Collect fresh metrics
        metrics = await self._collect_metrics()
        
        # Update cache
        self.cache["overview"] = metrics
        self.last_update["overview"] = now
        
        return metrics
    
    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics from various sources"""
        try:
            # Import here to avoid circular imports
            from src.database.connection import get_async_session
            from src.core.api_security import APIKeyManager
            
            async with get_async_session() as session:
                # Get system metrics
                system_metrics = await self._get_system_metrics(session)
                
                # Get user metrics
                user_metrics = await self._get_user_metrics(session)
                
                # Get data pipeline metrics
                pipeline_metrics = await self._get_pipeline_metrics()
                
                # Get security metrics
                security_metrics = await self._get_security_metrics(session)
                
                # Get AI service metrics
                ai_metrics = await self._get_ai_metrics()
                
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "system": system_metrics,
                    "users": user_metrics,
                    "pipeline": pipeline_metrics,
                    "security": security_metrics,
                    "ai": ai_metrics,
                    "websockets": ws_manager.get_stats()
                }
        
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "system": {"status": "error"},
                "users": {"active": 0, "total": 0},
                "pipeline": {"status": "unknown"},
                "security": {"alerts": 0},
                "ai": {"status": "unknown"},
                "websockets": ws_manager.get_stats()
            }
    
    async def _get_system_metrics(self, session) -> Dict[str, Any]:
        """Get system performance metrics"""
        import psutil
        import time
        
        # Get system stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get database health
        try:
            start_time = time.time()
            result = await session.execute("SELECT 1")
            db_response_time = (time.time() - start_time) * 1000
            db_status = "healthy"
        except Exception as e:
            db_response_time = 0
            db_status = f"error: {str(e)}"
        
        return {
            "status": "healthy" if cpu_percent < 80 and memory.percent < 80 else "warning",
            "uptime_hours": (time.time() - psutil.boot_time()) / 3600,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "database": {
                "status": db_status,
                "response_time_ms": db_response_time
            }
        }
    
    async def _get_user_metrics(self, session) -> Dict[str, Any]:
        """Get user activity metrics"""
        from sqlalchemy import text
        
        try:
            # Active users (logged in within last 24 hours)
            active_users_query = text("""
                SELECT COUNT(*) as count 
                FROM users 
                WHERE last_login > NOW() - INTERVAL '24 hours'
                AND is_active = true
            """)
            result = await session.execute(active_users_query)
            active_users = result.scalar() or 0
            
            # Total users
            total_users_query = text("SELECT COUNT(*) FROM users WHERE is_active = true")
            result = await session.execute(total_users_query)
            total_users = result.scalar() or 0
            
            # New users today
            new_today_query = text("""
                SELECT COUNT(*) 
                FROM users 
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            result = await session.execute(new_today_query)
            new_today = result.scalar() or 0
            
            return {
                "active": active_users,
                "total": total_users,
                "new_today": new_today,
                "online": len(ws_manager.active_connections)
            }
        
        except Exception as e:
            logger.error(f"Error getting user metrics: {e}")
            return {"active": 0, "total": 0, "new_today": 0, "online": 0}
    
    async def _get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get HK data pipeline metrics"""
        try:
            # This would connect to your Redis cache or monitoring system
            # For now, return simulated data
            return {
                "status": "healthy",
                "last_update": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
                "sources_online": 8,
                "total_sources": 11,
                "data_freshness_minutes": 15,
                "error_rate": 0.02
            }
        except Exception as e:
            logger.error(f"Error getting pipeline metrics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _get_security_metrics(self, session) -> Dict[str, Any]:
        """Get security monitoring metrics"""
        from sqlalchemy import text
        
        try:
            # Failed logins in last hour
            failed_logins_query = text("""
                SELECT COUNT(*) 
                FROM audit_logs 
                WHERE event_type = 'failed_login' 
                AND created_at > NOW() - INTERVAL '1 hour'
            """)
            result = await session.execute(failed_logins_query)
            failed_logins = result.scalar() or 0
            
            # Security alerts today
            alerts_query = text("""
                SELECT COUNT(*) 
                FROM audit_logs 
                WHERE event_category = 'security' 
                AND severity_level IN ('high', 'critical')
                AND DATE(created_at) = CURRENT_DATE
            """)
            result = await session.execute(alerts_query)
            alerts_today = result.scalar() or 0
            
            return {
                "failed_logins_hour": failed_logins,
                "alerts_today": alerts_today,
                "status": "secure" if failed_logins < 10 and alerts_today < 5 else "warning"
            }
        
        except Exception as e:
            logger.error(f"Error getting security metrics: {e}")
            return {
                "failed_logins_hour": 0,
                "alerts_today": 0,
                "status": "unknown"
            }
    
    async def _get_ai_metrics(self) -> Dict[str, Any]:
        """Get AI service metrics"""
        try:
            # Check if AI service is configured and working
            from src.core.api_security import APIKeyManager
            
            api_configured = APIKeyManager.is_api_key_configured()
            
            # This would typically check the AI service health
            # For now, return based on configuration
            return {
                "status": "healthy" if api_configured else "warning",
                "api_configured": api_configured,
                "requests_today": 150,  # This would come from your AI service metrics
                "avg_response_time_ms": 850,
                "error_rate": 0.01
            }
        
        except Exception as e:
            logger.error(f"Error getting AI metrics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

# Global metrics collector
metrics_collector = DashboardMetrics()

# Dashboard routes
@admin_router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """Main admin dashboard page"""
    try:
        # Get initial metrics for page load
        initial_metrics = await metrics_collector.get_metrics()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "page_title": "Healthcare AI V2 Dashboard",
            "initial_metrics": json.dumps(initial_metrics),
            "websocket_url": f"ws://localhost:{settings.port}/ws/admin/dashboard"
        })
    
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        raise HTTPException(status_code=500, detail="Error loading dashboard")

# API endpoints
@admin_api_router.get("/metrics")
async def get_dashboard_metrics(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Get current dashboard metrics"""
    return await metrics_collector.get_metrics()

@admin_api_router.get("/system-status")
async def get_system_status(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Get detailed system status"""
    metrics = await metrics_collector.get_metrics()
    
    return {
        "overall_health": "healthy",  # This would be calculated based on all metrics
        "components": {
            "database": metrics.get("system", {}).get("database", {}),
            "ai_service": metrics.get("ai", {}),
            "data_pipeline": metrics.get("pipeline", {}),
            "security": metrics.get("security", {})
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# WebSocket endpoint for real-time updates
@admin_router.websocket("/ws/dashboard")
async def admin_dashboard_websocket(
    websocket: WebSocket,
    current_user: User = Depends(require_admin)
):
    """WebSocket endpoint for real-time dashboard updates"""
    await ws_manager.connect(websocket, current_user.id)
    
    try:
        # Send initial metrics
        initial_metrics = await metrics_collector.get_metrics()
        await websocket.send_text(json.dumps({
            "type": "initial_metrics",
            "data": initial_metrics
        }))
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client message or timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message.get("type") == "request_metrics":
                    metrics = await metrics_collector.get_metrics()
                    await websocket.send_text(json.dumps({
                        "type": "metrics_update",
                        "data": metrics
                    }))
            
            except asyncio.TimeoutError:
                # Send periodic updates every 30 seconds
                metrics = await metrics_collector.get_metrics()
                await websocket.send_text(json.dumps({
                    "type": "metrics_update",
                    "data": metrics
                }))
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

# Background task to broadcast updates
async def broadcast_metrics_updates():
    """Background task to broadcast metrics to all connected clients"""
    while True:
        try:
            if ws_manager.active_connections:
                metrics = await metrics_collector.get_metrics()
                await ws_manager.send_to_all({
                    "type": "metrics_update",
                    "data": metrics
                })
            
            await asyncio.sleep(30)  # Update every 30 seconds
        
        except Exception as e:
            logger.error(f"Error broadcasting metrics: {e}")
            await asyncio.sleep(60)  # Wait longer on error

# File upload progress tracking
upload_progress = {}

@admin_api_router.get("/upload-progress/{upload_id}")
async def get_upload_progress(
    upload_id: str,
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """Get upload progress for specific upload"""
    progress = upload_progress.get(upload_id, {
        "status": "not_found",
        "progress": 0,
        "message": "Upload not found"
    })
    
    return progress

def update_upload_progress(upload_id: str, progress: int, status: str, message: str):
    """Update upload progress and notify connected clients"""
    upload_progress[upload_id] = {
        "upload_id": upload_id,
        "progress": progress,
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Broadcast to connected clients
    asyncio.create_task(ws_manager.send_to_all({
        "type": "upload_progress",
        "data": upload_progress[upload_id]
    }))

# Recent activity endpoint
@admin_api_router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 50,
    current_user: User = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get recent system activity"""
    try:
        from src.database.connection import get_async_session
        from sqlalchemy import text
        
        async with get_async_session() as session:
            query = text("""
                SELECT 
                    event_type,
                    description,
                    user_id,
                    ip_address,
                    created_at,
                    event_category,
                    severity_level
                FROM audit_logs 
                ORDER BY created_at DESC 
                LIMIT :limit
            """)
            
            result = await session.execute(query, {"limit": limit})
            activities = []
            
            for row in result:
                activities.append({
                    "event_type": row.event_type,
                    "description": row.description,
                    "user_id": row.user_id,
                    "ip_address": row.ip_address,
                    "timestamp": row.created_at.isoformat() if row.created_at else None,
                    "category": row.event_category,
                    "severity": row.severity_level
                })
            
            return activities
    
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return []

@admin_router.get("/data-management", response_class=HTMLResponse)
async def data_management_page(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """Comprehensive data management page with upload and document management"""
    return templates.TemplateResponse("data_management.html", {
        "request": request,
        "user": current_user,
        "page_title": "Data Management",
        "max_file_size": settings.upload_max_size,
        "allowed_extensions": settings.upload_allowed_extensions
    })