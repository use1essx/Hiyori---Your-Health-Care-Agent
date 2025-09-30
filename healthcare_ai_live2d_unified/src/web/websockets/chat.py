"""
Live2D WebSocket Chat Handler - Healthcare AI V2
================================================

Real-time WebSocket communication handler specifically designed for Live2D frontend integration.
Provides bidirectional communication with typing indicators, emotion mapping, cultural gestures,
and seamless integration with the Healthcare AI agent system.

Features:
- Real-time chat with typing indicators
- Agent personality → Live2D avatar emotion mapping
- Hong Kong cultural gesture library
- Bilingual support (English + Traditional Chinese)
- Session persistence and connection recovery
- Security and rate limiting
- Performance optimization for real-time interaction
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.exceptions import ValidationError as CoreValidationError, SecurityError
from src.core.logging import get_logger
from src.core.security import InputSanitizer, RateLimiter
from src.database.connection import get_async_db
from src.web.auth.handlers import AuthHandler
from src.agents.orchestrator import AgentOrchestrator
from src.agents.base_agent import AgentContext
from src.agents.emotion_mapper import EmotionMapper
from src.agents.gesture_library import GestureLibrary
from src.integrations.live2d_client import Live2DMessageFormatter


logger = get_logger(__name__)


# ============================================================================
# MESSAGE MODELS AND TYPES
# ============================================================================

class MessageType(str, Enum):
    """WebSocket message types"""
    # Incoming from Live2D frontend
    USER_MESSAGE = "user_message"
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"
    AUTH = "auth"
    PING = "ping"
    DISCONNECT = "disconnect"
    
    # Outgoing to Live2D frontend
    AGENT_RESPONSE = "agent_response"
    AGENT_THINKING = "agent_thinking"
    SYSTEM_STATUS = "system_status"
    TYPING_INDICATOR = "typing_indicator"
    ERROR = "error"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"
    PONG = "pong"
    WELCOME = "welcome"
    EMERGENCY_ALERT = "emergency_alert"


class ConnectionStatus(str, Enum):
    """WebSocket connection status"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class UserMessage:
    """Incoming user message from Live2D frontend"""
    type: str
    message: str
    language: str = "en"
    user_id: Optional[str] = None
    session_id: str = ""
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserMessage":
        """Create UserMessage from dictionary"""
        return cls(
            type=data.get("type", ""),
            message=data.get("message", ""),
            language=data.get("language", "en"),
            user_id=data.get("user_id"),
            session_id=data.get("session_id", ""),
            context=data.get("context"),
            timestamp=data.get("timestamp")
        )


@dataclass
class AgentResponse:
    """Outgoing agent response to Live2D frontend"""
    type: str = MessageType.AGENT_RESPONSE
    message: str = ""
    agent_type: str = ""
    agent_name: str = ""
    emotion: str = "neutral"
    gesture: str = "default"
    urgency: str = "low"
    language: str = "en"
    hk_facilities: List[Dict[str, Any]] = None
    session_id: str = ""
    timestamp: str = ""
    confidence: float = 0.0
    processing_time_ms: int = 0
    conversation_id: Optional[int] = None
    
    def __post_init__(self):
        """Set defaults"""
        if self.hk_facilities is None:
            self.hk_facilities = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ============================================================================
# CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    """
    WebSocket connection manager for Live2D chat sessions
    
    Handles:
    - Connection lifecycle management
    - Message broadcasting
    - Rate limiting per connection
    - Session persistence
    - Connection recovery
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.message_queues: Dict[str, List[Dict[str, Any]]] = {}
        self.logger = get_logger(f"{__name__}.ConnectionManager")
        
        # Rate limiting configuration
        self.max_messages_per_minute = 60
        self.max_connections_per_ip = 10
        self.connection_timeout_minutes = 30
        
    async def connect(self, websocket: WebSocket, session_id: str, client_ip: str) -> bool:
        """
        Accept new WebSocket connection
        
        Args:
            websocket: WebSocket instance
            session_id: Unique session identifier
            client_ip: Client IP address
            
        Returns:
            True if connection accepted, False if rejected
        """
        try:
            # Check connection limits per IP
            ip_connections = sum(
                1 for metadata in self.connection_metadata.values()
                if metadata.get("client_ip") == client_ip
            )
            
            if ip_connections >= self.max_connections_per_ip:
                self.logger.warning(f"Connection limit exceeded for IP {client_ip}")
                await websocket.close(code=1008, reason="Connection limit exceeded")
                return False
            
            # Accept connection
            await websocket.accept()
            
            # Store connection
            self.active_connections[session_id] = websocket
            self.connection_metadata[session_id] = {
                "client_ip": client_ip,
                "connected_at": datetime.now(),
                "status": ConnectionStatus.CONNECTED,
                "message_count": 0,
                "last_activity": datetime.now(),
                "user_id": None,
                "language": "en",
                "agent_context": {}
            }
            
            # Initialize rate limiter
            self.rate_limiters[session_id] = RateLimiter(
                max_requests=self.max_messages_per_minute,
                window_seconds=60
            )
            
            # Initialize message queue
            self.message_queues[session_id] = []
            
            self.logger.info(f"WebSocket connection established: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error accepting WebSocket connection: {e}")
            return False
    
    async def disconnect(self, session_id: str, reason: str = "Normal closure"):
        """
        Disconnect WebSocket connection
        
        Args:
            session_id: Session to disconnect
            reason: Disconnect reason
        """
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.close(code=1000, reason=reason)
            except Exception as e:
                self.logger.error(f"Error closing WebSocket {session_id}: {e}")
            
            # Clean up
            self.active_connections.pop(session_id, None)
            self.connection_metadata.pop(session_id, None)
            self.rate_limiters.pop(session_id, None)
            self.message_queues.pop(session_id, None)
            
            self.logger.info(f"WebSocket disconnected: {session_id} - {reason}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to specific session
        
        Args:
            session_id: Target session
            message: Message to send
            
        Returns:
            True if sent successfully
        """
        if session_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[session_id]
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
            
            # Update activity
            if session_id in self.connection_metadata:
                self.connection_metadata[session_id]["last_activity"] = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message to {session_id}: {e}")
            await self.disconnect(session_id, "Send error")
            return False
    
    async def broadcast_message(self, message: Dict[str, Any], exclude_sessions: Set[str] = None):
        """
        Broadcast message to all active connections
        
        Args:
            message: Message to broadcast
            exclude_sessions: Sessions to exclude from broadcast
        """
        if exclude_sessions is None:
            exclude_sessions = set()
        
        failed_connections = []
        
        for session_id in self.active_connections:
            if session_id not in exclude_sessions:
                success = await self.send_message(session_id, message)
                if not success:
                    failed_connections.append(session_id)
        
        # Clean up failed connections
        for session_id in failed_connections:
            await self.disconnect(session_id, "Broadcast failure")
    
    def check_rate_limit(self, session_id: str) -> bool:
        """
        Check if session is within rate limits
        
        Args:
            session_id: Session to check
            
        Returns:
            True if within limits
        """
        if session_id not in self.rate_limiters:
            return False
        
        return self.rate_limiters[session_id].is_allowed()
    
    def update_activity(self, session_id: str):
        """Update last activity for session"""
        if session_id in self.connection_metadata:
            metadata = self.connection_metadata[session_id]
            metadata["last_activity"] = datetime.now()
            metadata["message_count"] += 1
    
    def authenticate_session(self, session_id: str, user_id: str, user_data: Dict[str, Any]):
        """
        Mark session as authenticated
        
        Args:
            session_id: Session to authenticate
            user_id: User identifier
            user_data: User information
        """
        if session_id in self.connection_metadata:
            metadata = self.connection_metadata[session_id]
            metadata["status"] = ConnectionStatus.AUTHENTICATED
            metadata["user_id"] = user_id
            metadata["user_data"] = user_data
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata"""
        return self.connection_metadata.get(session_id)
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.active_connections.keys())
    
    async def cleanup_inactive_connections(self):
        """Clean up inactive connections"""
        cutoff_time = datetime.now() - timedelta(minutes=self.connection_timeout_minutes)
        inactive_sessions = []
        
        for session_id, metadata in self.connection_metadata.items():
            if metadata["last_activity"] < cutoff_time:
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            await self.disconnect(session_id, "Inactive timeout")
        
        if inactive_sessions:
            self.logger.info(f"Cleaned up {len(inactive_sessions)} inactive connections")


# ============================================================================
# LIVE2D WEBSOCKET HANDLER
# ============================================================================

class Live2DChatHandler:
    """
    Main WebSocket handler for Live2D chat integration
    
    Coordinates:
    - WebSocket connection management
    - Message processing and validation
    - Agent orchestration and response generation
    - Emotion and gesture mapping
    - Security and rate limiting
    """
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.auth_handler = AuthHandler()
        self.input_sanitizer = InputSanitizer()
        self.emotion_mapper = EmotionMapper()
        self.gesture_library = GestureLibrary()
        self.message_formatter = Live2DMessageFormatter()
        self.logger = get_logger(f"{__name__}.Live2DChatHandler")
        
        # Initialize agent orchestrator (will be set when AI service is available)
        self.agent_orchestrator: Optional[AgentOrchestrator] = None
        
        # Performance metrics
        self.total_connections = 0
        self.total_messages_processed = 0
        self.average_response_time_ms = 0
    
    async def initialize_agents(self):
        """Initialize agent orchestrator with AI service"""
        try:
            # Import here to avoid circular imports
            from src.ai.ai_service import get_ai_service
            
            ai_service = await get_ai_service()
            self.agent_orchestrator = AgentOrchestrator(ai_service)
            self.logger.info("Agent orchestrator initialized for Live2D WebSocket")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent orchestrator: {e}")
            # Continue without agent system - will use fallback responses
    
    async def handle_connection(self, websocket: WebSocket, client_ip: str) -> str:
        """
        Handle new WebSocket connection
        
        Args:
            websocket: WebSocket instance
            client_ip: Client IP address
            
        Returns:
            Session ID if connection successful
        """
        # Generate unique session ID
        session_id = f"live2d_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # Accept connection
        success = await self.connection_manager.connect(websocket, session_id, client_ip)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Connection limit exceeded"
            )
        
        self.total_connections += 1
        
        # Send welcome message
        await self._send_welcome_message(session_id)
        
        return session_id
    
    async def process_message(self, session_id: str, raw_message: str) -> bool:
        """
        Process incoming WebSocket message
        
        Args:
            session_id: Session identifier
            raw_message: Raw message from client
            
        Returns:
            True if processed successfully
        """
        start_time = time.time()
        
        try:
            # Check rate limiting
            if not self.connection_manager.check_rate_limit(session_id):
                await self._send_error_message(
                    session_id, 
                    "Rate limit exceeded. Please slow down your messages.",
                    "RATE_LIMIT_EXCEEDED"
                )
                return False
            
            # Parse message
            try:
                message_data = json.loads(raw_message)
            except json.JSONDecodeError:
                await self._send_error_message(
                    session_id,
                    "Invalid JSON format",
                    "INVALID_JSON"
                )
                return False
            
            # Validate message structure
            message_type = message_data.get("type", "")
            if not message_type:
                await self._send_error_message(
                    session_id,
                    "Message type is required",
                    "MISSING_TYPE"
                )
                return False
            
            # Update activity
            self.connection_manager.update_activity(session_id)
            
            # Route message based on type
            success = await self._route_message(session_id, message_type, message_data)
            
            # Update metrics
            processing_time = int((time.time() - start_time) * 1000)
            self.total_messages_processed += 1
            self.average_response_time_ms = (
                (self.average_response_time_ms * (self.total_messages_processed - 1) + processing_time)
                / self.total_messages_processed
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error processing message for {session_id}: {e}")
            await self._send_error_message(
                session_id,
                "Internal server error occurred",
                "INTERNAL_ERROR"
            )
            return False
    
    async def _route_message(self, session_id: str, message_type: str, message_data: Dict[str, Any]) -> bool:
        """
        Route message to appropriate handler
        
        Args:
            session_id: Session identifier
            message_type: Type of message
            message_data: Message data
            
        Returns:
            True if routed successfully
        """
        try:
            if message_type == MessageType.USER_MESSAGE:
                return await self._handle_user_message(session_id, message_data)
            
            elif message_type == MessageType.TYPING_START:
                return await self._handle_typing_start(session_id, message_data)
            
            elif message_type == MessageType.TYPING_STOP:
                return await self._handle_typing_stop(session_id, message_data)
            
            elif message_type == MessageType.AUTH:
                return await self._handle_auth(session_id, message_data)
            
            elif message_type == MessageType.PING:
                return await self._handle_ping(session_id, message_data)
            
            elif message_type == MessageType.DISCONNECT:
                return await self._handle_disconnect(session_id, message_data)
            
            else:
                await self._send_error_message(
                    session_id,
                    f"Unknown message type: {message_type}",
                    "UNKNOWN_MESSAGE_TYPE"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error routing message {message_type}: {e}")
            return False
    
    async def _handle_user_message(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Handle user chat message
        
        Args:
            session_id: Session identifier
            message_data: Message data
            
        Returns:
            True if handled successfully
        """
        try:
            # Parse user message
            user_message = UserMessage.from_dict(message_data)
            user_message.session_id = session_id
            
            # Validate and sanitize message
            if not user_message.message or len(user_message.message.strip()) == 0:
                await self._send_error_message(
                    session_id,
                    "Message cannot be empty",
                    "EMPTY_MESSAGE"
                )
                return False
            
            # Sanitize input
            safe_message = self.input_sanitizer.sanitize_string(user_message.message, max_length=4000)
            
            if len(safe_message.strip()) == 0:
                await self._send_error_message(
                    session_id,
                    "Message contains only invalid characters",
                    "INVALID_MESSAGE"
                )
                return False
            
            user_message.message = safe_message
            
            # Send thinking indicator
            await self._send_thinking_indicator(session_id, "AI is processing your message...")
            
            # Process with agent system
            response = await self._process_with_agents(session_id, user_message)
            
            # Send response
            await self.connection_manager.send_message(session_id, asdict(response))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling user message: {e}")
            await self._send_error_message(
                session_id,
                "Failed to process your message",
                "PROCESSING_ERROR"
            )
            return False
    
    async def _process_with_agents(self, session_id: str, user_message: UserMessage) -> AgentResponse:
        """
        Process user message with agent system
        
        Args:
            session_id: Session identifier
            user_message: User message to process
            
        Returns:
            Agent response
        """
        try:
            if not self.agent_orchestrator:
                # Fallback response if agent system not available
                return self._create_fallback_response(session_id, user_message)
            
            # Get session info
            session_info = self.connection_manager.get_session_info(session_id)
            if not session_info:
                return self._create_fallback_response(session_id, user_message)
            
            # Create agent context
            context = AgentContext(
                user_id=session_info.get("user_id", f"anonymous_{session_id}"),
                session_id=session_id,
                conversation_history=session_info.get("conversation_history", []),
                user_profile=session_info.get("user_data", {}),
                cultural_context={
                    "region": "hong_kong",
                    "language": user_message.language,
                    "connection_type": "live2d_websocket"
                },
                language_preference=user_message.language,
                timestamp=datetime.now()
            )
            
            # Route to appropriate agent
            selected_agent, routing_result = await self.agent_orchestrator.route_request(
                user_input=user_message.message,
                context=context
            )
            
            # Generate agent response
            agent_response = await selected_agent.generate_response(user_message.message, context)
            
            # Map agent response to Live2D format
            emotion = self.emotion_mapper.map_agent_to_emotion(
                agent_type=routing_result.selected_agent,
                response=agent_response.content,
                urgency=routing_result.urgency_level,
                confidence=routing_result.confidence
            )
            
            gesture = self.gesture_library.get_cultural_gesture(
                agent_type=routing_result.selected_agent,
                context=user_message.message,
                language=user_message.language
            )
            
            # Create Live2D response
            live2d_response = AgentResponse(
                type=MessageType.AGENT_RESPONSE,
                message=agent_response.content,
                agent_type=routing_result.selected_agent,
                agent_name=selected_agent.get_activation_message(context),
                emotion=emotion,
                gesture=gesture,
                urgency=routing_result.urgency_level,
                language=user_message.language,
                session_id=session_id,
                confidence=routing_result.confidence,
                processing_time_ms=getattr(agent_response, 'processing_time_ms', 0)
            )
            
            # Update conversation history
            self._update_conversation_history(session_id, user_message, live2d_response)
            
            return live2d_response
            
        except Exception as e:
            self.logger.error(f"Error processing with agents: {e}")
            return self._create_fallback_response(session_id, user_message)
    
    def _create_fallback_response(self, session_id: str, user_message: UserMessage) -> AgentResponse:
        """
        Create fallback response when agent system is unavailable
        
        Args:
            session_id: Session identifier
            user_message: Original user message
            
        Returns:
            Fallback agent response
        """
        # Simple keyword-based fallback
        message_lower = user_message.message.lower()
        
        if any(word in message_lower for word in ["emergency", "urgent", "help", "救命", "緊急"]):
            response_text = "🚨 If this is a medical emergency, please call 999 immediately. I'm experiencing technical difficulties but emergency services are always available."
            emotion = "urgent"
            gesture = "emergency_stance"
            urgency = "emergency"
            agent_type = "safety_guardian"
        elif any(word in message_lower for word in ["sad", "depressed", "anxious", "傷心", "焦慮"]):
            response_text = "💜 I understand you're going through a difficult time. While I'm experiencing some technical issues, please know that support is available. Consider reaching out to a counselor or trusted friend."
            emotion = "gentle_supportive"
            gesture = "comforting_gesture"
            urgency = "medium"
            agent_type = "mental_health"
        else:
            response_text = "I'm experiencing some technical difficulties at the moment, but I'm here to help. Could you please try asking your question again, or contact our support team if the issue persists?"
            emotion = "professional_caring"
            gesture = "reassuring_nod"
            urgency = "low"
            agent_type = "wellness_coach"
        
        return AgentResponse(
            type=MessageType.AGENT_RESPONSE,
            message=response_text,
            agent_type=agent_type,
            agent_name="Healthcare AI Assistant",
            emotion=emotion,
            gesture=gesture,
            urgency=urgency,
            language=user_message.language,
            session_id=session_id,
            confidence=0.5
        )
    
    def _update_conversation_history(self, session_id: str, user_message: UserMessage, response: AgentResponse):
        """
        Update conversation history for session
        
        Args:
            session_id: Session identifier
            user_message: User message
            response: Agent response
        """
        session_info = self.connection_manager.get_session_info(session_id)
        if not session_info:
            return
        
        if "conversation_history" not in session_info:
            session_info["conversation_history"] = []
        
        # Add to conversation history
        conversation_item = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message.message,
            "agent_response": response.message,
            "agent_type": response.agent_type,
            "language": user_message.language,
            "emotion": response.emotion,
            "gesture": response.gesture
        }
        
        session_info["conversation_history"].append(conversation_item)
        
        # Keep only last 50 exchanges
        if len(session_info["conversation_history"]) > 50:
            session_info["conversation_history"] = session_info["conversation_history"][-50:]
    
    async def _handle_typing_start(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """Handle typing start indicator"""
        # Currently just log - could be extended for typing analysis
        return True
    
    async def _handle_typing_stop(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """Handle typing stop indicator"""
        # Currently just log - could be extended for typing analysis
        return True
    
    async def _handle_auth(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Handle authentication request
        
        Args:
            session_id: Session identifier
            message_data: Auth message data
            
        Returns:
            True if auth handled successfully
        """
        try:
            auth_token = message_data.get("token")
            if not auth_token:
                await self._send_auth_failed(session_id, "No authentication token provided")
                return False
            
            # Validate token
            try:
                # Decode and validate JWT token
                payload = self.auth_handler.verify_token(auth_token)
                if not payload:
                    await self._send_auth_failed(session_id, "Invalid authentication token")
                    return False
                
                user_id = payload.get("sub")
                if not user_id:
                    await self._send_auth_failed(session_id, "Invalid token payload")
                    return False
                
                # Get user information (would typically fetch from database)
                user_data = {
                    "id": user_id,
                    "authenticated_at": datetime.now().isoformat()
                }
                
                # Mark session as authenticated
                self.connection_manager.authenticate_session(session_id, user_id, user_data)
                
                # Send success response
                await self.connection_manager.send_message(session_id, {
                    "type": MessageType.AUTH_SUCCESS,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                })
                
                return True
                
            except Exception as e:
                self.logger.error(f"Token validation error: {e}")
                await self._send_auth_failed(session_id, "Authentication failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Auth handling error: {e}")
            await self._send_auth_failed(session_id, "Authentication error")
            return False
    
    async def _handle_ping(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """Handle ping message"""
        await self.connection_manager.send_message(session_id, {
            "type": MessageType.PONG,
            "timestamp": datetime.now().isoformat()
        })
        return True
    
    async def _handle_disconnect(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """Handle disconnect request"""
        await self.connection_manager.disconnect(session_id, "Client disconnect")
        return True
    
    async def _send_welcome_message(self, session_id: str):
        """Send welcome message to new connection"""
        welcome_message = {
            "type": MessageType.WELCOME,
            "message": "🏥 Welcome to Healthcare AI V2! I'm here to help with your health questions.",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "available_agents": ["illness_monitor", "mental_health", "safety_guardian", "wellness_coach"],
            "supported_languages": ["en", "zh-HK"],
            "features": [
                "real_time_chat",
                "emotion_mapping",
                "cultural_gestures",
                "emergency_detection",
                "hk_data_integration"
            ]
        }
        await self.connection_manager.send_message(session_id, welcome_message)
    
    async def _send_thinking_indicator(self, session_id: str, message: str = "AI is thinking..."):
        """Send thinking indicator"""
        thinking_message = {
            "type": MessageType.AGENT_THINKING,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        await self.connection_manager.send_message(session_id, thinking_message)
    
    async def _send_error_message(self, session_id: str, message: str, error_code: str = "UNKNOWN_ERROR"):
        """Send error message"""
        error_message = {
            "type": MessageType.ERROR,
            "message": message,
            "error_code": error_code,
            "timestamp": datetime.now().isoformat()
        }
        await self.connection_manager.send_message(session_id, error_message)
    
    async def _send_auth_failed(self, session_id: str, reason: str):
        """Send authentication failed message"""
        auth_failed_message = {
            "type": MessageType.AUTH_FAILED,
            "message": reason,
            "timestamp": datetime.now().isoformat()
        }
        await self.connection_manager.send_message(session_id, auth_failed_message)
    
    async def disconnect_session(self, session_id: str, reason: str = "Normal closure"):
        """Disconnect specific session"""
        await self.connection_manager.disconnect(session_id, reason)
    
    async def broadcast_status_update(self, status_data: Dict[str, Any]):
        """Broadcast system status update to all connections"""
        status_message = {
            "type": MessageType.SYSTEM_STATUS,
            "timestamp": datetime.now().isoformat(),
            **status_data
        }
        await self.connection_manager.broadcast_message(status_message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": self.total_connections,
            "active_connections": len(self.connection_manager.get_active_sessions()),
            "total_messages_processed": self.total_messages_processed,
            "average_response_time_ms": self.average_response_time_ms,
            "connection_metadata": {
                session_id: {
                    "status": metadata["status"],
                    "connected_at": metadata["connected_at"].isoformat(),
                    "message_count": metadata["message_count"],
                    "user_id": metadata.get("user_id")
                }
                for session_id, metadata in self.connection_manager.connection_metadata.items()
            }
        }


# ============================================================================
# GLOBAL HANDLER INSTANCE
# ============================================================================

# Global handler instance (singleton pattern)
live2d_chat_handler = Live2DChatHandler()


# ============================================================================
# CLEANUP TASK
# ============================================================================

async def cleanup_inactive_connections():
    """Background task to clean up inactive connections"""
    while True:
        try:
            await live2d_chat_handler.connection_manager.cleanup_inactive_connections()
            await asyncio.sleep(300)  # Run every 5 minutes
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying
