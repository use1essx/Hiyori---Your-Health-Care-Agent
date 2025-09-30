"""
Live2D Integration Routes for Healthcare AI V2
==============================================

FastAPI routes that integrate Live2D avatar functionality with the Healthcare AI system.
Provides endpoints for avatar interaction, model management, and real-time chat.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# from ...ai.ai_service import HealthcareAIService
# from ...agents.orchestrator import AgentOrchestrator  
# from ...agents.context_manager import ConversationContextManager
from ...core.logging import get_logger
from ..auth.dependencies import get_optional_user
from .backend.healthcare_ai_bridge import HealthcareAIBridge

logger = get_logger(__name__)

# Initialize Live2D router
live2d_router = APIRouter(prefix="/live2d", tags=["Live2D Integration"])

# Initialize components
healthcare_bridge = HealthcareAIBridge()
# context_manager = ConversationContextManager()

# Live2D static files path
LIVE2D_STATIC_PATH = Path(__file__).parent / "frontend"
LIVE2D_RESOURCES_PATH = LIVE2D_STATIC_PATH / "Resources"
LIVE2D_SAMPLES_PATH = Path(__file__).parent / "Samples" / "TypeScript" / "Demo" / "dist"


# Pydantic models for Live2D API
class ChatMessage(BaseModel):
    """Chat message model for Live2D interface"""
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    language: str = Field(default="en", pattern="^(en|zh-HK|zh-CN)$")
    agent_preference: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None


class Live2DResponse(BaseModel):
    """Live2D chat response model"""
    message: str
    agent_type: str
    agent_name: str
    emotion: str
    gesture: str
    urgency: str
    language: str
    confidence: float
    processing_time_ms: int
    hk_facilities: List[Dict[str, Any]] = []
    avatar_state: Dict[str, Any] = {}
    voice_settings: Dict[str, Any] = {}
    animation_cues: List[str] = []
    session_id: str
    timestamp: str


class ModelSwitchRequest(BaseModel):
    """Model switch request"""
    model_name: str = Field(..., description="Name of the Live2D model to switch to")
    reason: Optional[str] = Field(None, description="Reason for model switch")


class BackgroundSwitchRequest(BaseModel):
    """Background switch request"""
    background_name: str = Field(..., description="Name of the background to switch to")


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.connection_metadata[session_id] = {
            "connected_at": datetime.now().isoformat(),
            "message_count": 0,
            "last_activity": datetime.now().isoformat()
        }
        logger.info(f"Live2D WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.connection_metadata:
            del self.connection_metadata[session_id]
        logger.info(f"Live2D WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: Dict[str, Any]):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
                # Update metadata
                if session_id in self.connection_metadata:
                    metadata = self.connection_metadata[session_id]
                    metadata["message_count"] += 1
                    metadata["last_activity"] = datetime.now().isoformat()
                return True
            except Exception as e:
                logger.error(f"Error sending WebSocket message to {session_id}: {e}")
                self.disconnect(session_id)
                return False
        return False

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
                disconnected.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected:
            self.disconnect(session_id)


connection_manager = ConnectionManager()


# Main Live2D interface route
@live2d_router.get("/", response_class=HTMLResponse)
async def live2d_interface():
    """Serve the main Live2D chat interface"""
    try:
        html_path = LIVE2D_STATIC_PATH / "index.html"
        if html_path.exists():
            logger.info(f"Serving Live2D interface from: {html_path}")
            return FileResponse(html_path)
        else:
            logger.warning(f"Live2D interface not found at: {html_path}")
            # Return a basic HTML page if the Live2D interface isn't found
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Healthcare AI V2 - Live2D Interface</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body>
                <h1>Healthcare AI V2 - Live2D Interface</h1>
                <p>Live2D interface is being set up. Please check back soon.</p>
                <p><a href="/docs">View API Documentation</a></p>
                <p><a href="/live2d/admin">Admin Panel</a></p>
            </body>
            </html>
            """)
    except Exception as e:
        logger.error(f"Error serving Live2D interface: {e}")
        raise HTTPException(status_code=500, detail="Live2D interface unavailable")


# Chat endpoint for Live2D integration
@live2d_router.post("/chat", response_model=Live2DResponse)
async def live2d_chat(
    message: ChatMessage,
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Chat endpoint optimized for Live2D avatar interaction
    """
    try:
        start_time = datetime.now()
        
        # Generate session ID if not provided
        session_id = message.session_id or f"live2d_{uuid.uuid4().hex[:12]}"
        user_id = current_user.id if current_user else f"guest_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Live2D chat request: {message.message[:50]}... (session: {session_id})")
        
        # Process with Healthcare AI V2 backend
        response = await healthcare_bridge.process_chat_message(
            message=message.message,
            session_id=session_id,
            user_id=str(user_id),
            language=message.language,
            agent_preference=message.agent_preference,
            user_context=message.user_context or {}
        )
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Format response for Live2D
        live2d_response = Live2DResponse(
            message=response.get("message", "I'm experiencing technical difficulties."),
            agent_type=response.get("agent_type", "wellness_coach"),
            agent_name=response.get("agent_name", "Healthcare Assistant"),
            emotion=response.get("emotion", "neutral"),
            gesture=response.get("gesture", "default"),
            urgency=response.get("urgency", "low"),
            language=response.get("language", message.language),
            confidence=response.get("confidence", 0.8),
            processing_time_ms=processing_time,
            hk_facilities=response.get("hk_facilities", []),
            avatar_state=response.get("avatar_state", {}),
            voice_settings=response.get("voice_settings", {}),
            animation_cues=response.get("animation_cues", []),
            session_id=session_id,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Live2D response generated: {live2d_response.agent_type} ({processing_time}ms)")
        return live2d_response
        
    except Exception as e:
        logger.error(f"Error in Live2D chat: {e}")
        # Return fallback response
        return Live2DResponse(
            message="I apologize, but I'm experiencing technical difficulties. Please try again or contact support if this persists.",
            agent_type="wellness_coach",
            agent_name="Healthcare Assistant",
            emotion="apologetic",
            gesture="bow",
            urgency="low",
            language=message.language,
            confidence=0.5,
            processing_time_ms=100,
            session_id=message.session_id or f"error_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat()
        )


# WebSocket endpoint for real-time Live2D chat
@live2d_router.websocket("/ws/chat")
async def live2d_websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time Live2D chat interaction
    """
    session_id = f"ws_{uuid.uuid4().hex[:12]}"
    await connection_manager.connect(websocket, session_id)
    
    try:
        # Send welcome message
        await connection_manager.send_message(session_id, {
            "type": "welcome",
            "session_id": session_id,
            "message": "Welcome to Healthcare AI V2 with Live2D! How can I help you today?",
            "available_agents": ["illness_monitor", "mental_health", "safety_guardian", "wellness_coach"],
            "supported_languages": ["en", "zh-HK"]
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process different message types
            if message_data.get("type") == "user_message":
                # Send thinking indicator
                await connection_manager.send_message(session_id, {
                    "type": "agent_thinking",
                    "message": "Processing your request..."
                })
                
                # Process with Healthcare AI
                response = await healthcare_bridge.process_chat_message(
                    message=message_data.get("message", ""),
                    session_id=session_id,
                    user_id=f"ws_user_{session_id}",
                    language=message_data.get("language", "en")
                )
                
                # Send agent response
                await connection_manager.send_message(session_id, {
                    "type": "agent_response",
                    **response,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                })
                
            elif message_data.get("type") == "ping":
                # Respond to ping with pong
                await connection_manager.send_message(session_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                
            elif message_data.get("type") == "typing_start":
                # Handle typing indicators (optional)
                pass
                
            elif message_data.get("type") == "typing_stop":
                # Handle typing indicators (optional)
                pass
    
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        connection_manager.disconnect(session_id)


# Model management endpoints
@live2d_router.get("/models")
async def get_available_models():
    """Get list of available Live2D models"""
    try:
        config_path = Path(__file__).parent / "admin_config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            return {"models": config.get("models", {})}
        else:
            # Scan for models dynamically
            models = {}
            if LIVE2D_RESOURCES_PATH.exists():
                for model_dir in LIVE2D_RESOURCES_PATH.iterdir():
                    if model_dir.is_dir() and not model_dir.name.startswith('@'):
                        model_file = model_dir / f"{model_dir.name}.model3.json"
                        if model_file.exists():
                            models[model_dir.name] = {
                                "enabled": True,
                                "path": str(model_dir),
                                "model_file": model_file.name
                            }
            return {"models": models}
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return {"models": {}, "error": str(e)}


@live2d_router.post("/models/switch")
async def switch_model(request: ModelSwitchRequest):
    """Switch the active Live2D model"""
    try:
        # This would implement the model switching logic
        # For now, return success response
        logger.info(f"Model switch requested: {request.model_name}")
        return {
            "success": True,
            "message": f"Switched to model: {request.model_name}",
            "model_name": request.model_name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to switch model: {str(e)}")


@live2d_router.get("/backgrounds")
async def get_available_backgrounds():
    """Get list of available backgrounds"""
    try:
        config_path = Path(__file__).parent / "admin_config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            return {"backgrounds": config.get("backgrounds", {})}
        else:
            return {"backgrounds": {}}
    except Exception as e:
        logger.error(f"Error getting backgrounds: {e}")
        return {"backgrounds": {}, "error": str(e)}


@live2d_router.post("/backgrounds/switch")
async def switch_background(request: BackgroundSwitchRequest):
    """Switch the active background"""
    try:
        logger.info(f"Background switch requested: {request.background_name}")
        return {
            "success": True,
            "message": f"Switched to background: {request.background_name}",
            "background_name": request.background_name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error switching background: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to switch background: {str(e)}")


# Static file serving for Live2D assets
@live2d_router.get("/static/{file_path:path}")
async def serve_live2d_static(file_path: str):
    """Serve Live2D static files (models, textures, etc.)"""
    try:
        # Try frontend directory first
        full_path = LIVE2D_STATIC_PATH / file_path
        if full_path.exists() and full_path.is_file():
            return FileResponse(full_path)
        
        # Fallback to samples directory for Live2D core files
        fallback_path = LIVE2D_SAMPLES_PATH / file_path
        if fallback_path.exists() and fallback_path.is_file():
            return FileResponse(fallback_path)
            
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving static file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Error serving file")

# Additional route to serve frontend assets directly
@live2d_router.get("/assets/{file_path:path}")
async def serve_live2d_assets(file_path: str):
    """Serve Live2D frontend assets (CSS, JS, images, etc.)"""
    try:
        full_path = LIVE2D_STATIC_PATH / "assets" / file_path
        if full_path.exists() and full_path.is_file():
            return FileResponse(full_path)
        else:
            raise HTTPException(status_code=404, detail=f"Asset not found: {file_path}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving asset {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Error serving asset")

# Route to serve Core Live2D files
@live2d_router.get("/Core/{file_path:path}")
async def serve_live2d_core(file_path: str):
    """Serve Live2D Core engine files"""
    try:
        full_path = LIVE2D_STATIC_PATH / "Core" / file_path
        if full_path.exists() and full_path.is_file():
            return FileResponse(full_path)
        else:
            raise HTTPException(status_code=404, detail=f"Core file not found: {file_path}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving Core file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Error serving Core file")

# Route to serve Resources (models, textures, etc.)
@live2d_router.get("/Resources/{file_path:path}")
async def serve_live2d_resources(file_path: str):
    """Serve Live2D Resources (models, textures, backgrounds, etc.)"""
    try:
        full_path = LIVE2D_STATIC_PATH / "Resources" / file_path
        if full_path.exists() and full_path.is_file():
            return FileResponse(full_path)
        else:
            raise HTTPException(status_code=404, detail=f"Resource not found: {file_path}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving Resource {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Error serving Resource")


# Health check for Live2D system
@live2d_router.get("/health")
async def live2d_health_check():
    """Health check for Live2D integration system"""
    try:
        # Check if Live2D assets exist
        core_exists = (Path(__file__).parent / "Core" / "live2dcubismcore.min.js").exists()
        models_exist = LIVE2D_RESOURCES_PATH.exists()
        
        # Check Healthcare AI connection
        healthcare_ai_status = await healthcare_bridge.check_healthcare_ai_status()
        
        status = "healthy" if core_exists and models_exist and healthcare_ai_status else "degraded"
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "live2d_core": {"status": "available" if core_exists else "missing"},
                "live2d_models": {"status": "available" if models_exist else "missing"},
                "healthcare_ai": {"status": "connected" if healthcare_ai_status else "disconnected"},
                "websocket_connections": {"active": len(connection_manager.active_connections)}
            },
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Live2D health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Admin interface route
@live2d_router.get("/admin", response_class=HTMLResponse)
async def live2d_admin_interface():
    """Serve the Live2D admin interface"""
    try:
        admin_path = LIVE2D_STATIC_PATH / "admin.html"
        if admin_path.exists():
            logger.info(f"Serving Live2D admin interface from: {admin_path}")
            return FileResponse(admin_path)
        else:
            logger.warning(f"Live2D admin interface not found at: {admin_path}")
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Healthcare AI V2 - Live2D Admin</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body>
                <h1>Healthcare AI V2 - Live2D Admin</h1>
                <p>Admin interface is being set up.</p>
                <p><a href="/live2d">Back to Chat Interface</a></p>
            </body>
            </html>
            """)
    except Exception as e:
        logger.error(f"Error serving Live2D admin interface: {e}")
        raise HTTPException(status_code=500, detail="Live2D admin interface unavailable")

# Admin endpoints for Live2D management
@live2d_router.get("/admin/status")
async def get_admin_status():
    """Get Live2D system status for admin interface"""
    try:
        # Get model configuration
        models = await get_available_models()
        backgrounds = await get_available_backgrounds()
        
        # Get connection statistics
        connection_stats = {
            "active_connections": len(connection_manager.active_connections),
            "total_sessions": len(connection_manager.connection_metadata),
            "connections": list(connection_manager.connection_metadata.keys())
        }
        
        return {
            "status": "operational",
            "models": models,
            "backgrounds": backgrounds,
            "connections": connection_stats,
            "healthcare_ai_bridge": await healthcare_bridge.get_bridge_status(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting admin status: {e}")
        return {"status": "error", "error": str(e)}


# Initialize Healthcare AI Bridge on startup
@live2d_router.on_event("startup")
async def startup_live2d():
    """Initialize Live2D system on startup"""
    try:
        logger.info("🎭 Initializing Live2D integration system...")
        
        # Initialize healthcare AI bridge
        await healthcare_bridge.initialize()
        
        # Verify Live2D assets
        if not LIVE2D_STATIC_PATH.exists():
            logger.warning(f"Live2D static path not found: {LIVE2D_STATIC_PATH}")
        
        if not LIVE2D_RESOURCES_PATH.exists():
            logger.warning(f"Live2D resources path not found: {LIVE2D_RESOURCES_PATH}")
        
        logger.info("✅ Live2D integration system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Live2D system: {e}")


@live2d_router.on_event("shutdown")
async def shutdown_live2d():
    """Cleanup Live2D system on shutdown"""
    try:
        logger.info("🛑 Shutting down Live2D integration system...")
        
        # Disconnect all WebSocket connections
        for session_id in list(connection_manager.active_connections.keys()):
            connection_manager.disconnect(session_id)
        
        # Cleanup healthcare AI bridge
        await healthcare_bridge.cleanup()
        
        logger.info("✅ Live2D integration system shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during Live2D shutdown: {e}")


# Emotion and gesture mapping endpoints (for Live2D frontend)
@live2d_router.get("/emotions/{agent_type}")
async def get_agent_emotions(agent_type: str):
    """Get available emotions for specific agent type"""
    try:
        emotions = healthcare_bridge.get_agent_emotions(agent_type)
        return {"agent_type": agent_type, "emotions": emotions}
    except Exception as e:
        logger.error(f"Error getting emotions for {agent_type}: {e}")
        return {"agent_type": agent_type, "emotions": [], "error": str(e)}


@live2d_router.get("/gestures/{agent_type}")
async def get_agent_gestures(agent_type: str):
    """Get available gestures for specific agent type"""
    try:
        gestures = healthcare_bridge.get_agent_gestures(agent_type)
        return {"agent_type": agent_type, "gestures": gestures}
    except Exception as e:
        logger.error(f"Error getting gestures for {agent_type}: {e}")
        return {"agent_type": agent_type, "gestures": [], "error": str(e)}


@live2d_router.post("/swap-model")
async def swap_live2d_model(request: Dict[str, Any]):
    """Swap the current Live2D model"""
    try:
        model_name = request.get("model", "Hiyori")
        logger.info(f"Model swap requested: {model_name}")
        
        # For now, we'll just return a success response
        # In a full implementation, you'd update the model state
        return {
            "success": True,
            "message": f"Model changed to {model_name}",
            "current_model": model_name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error swapping model: {e}")
        return {
            "success": False,
            "message": f"Failed to swap model: {str(e)}",
            "current_model": "Hiyori"  # fallback
        }


# Export the router for inclusion in main FastAPI app
__all__ = ["live2d_router"]
