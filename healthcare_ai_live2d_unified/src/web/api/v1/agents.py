"""
Agent System API Endpoints

This module provides endpoints for the multi-agent AI system including:
- Agent information and capabilities
- Chat interaction endpoints
- Agent performance metrics
- Agent routing information
- Conversation history management

NOTE: This is the structure/interface layer. The actual agent implementations
will be added in Phase 3 (Day 3) of development.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError, ValidationError, AgentError
from src.core.logging import get_logger, log_api_request, log_agent_interaction
from src.core.security import InputSanitizer
from src.database.connection import get_async_db
from src.database.models_comprehensive import User, Conversation
from src.database.repositories.user_repository import UserRepository
from src.web.auth.dependencies import get_current_user, get_optional_user, require_role


logger = get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AgentInfo(BaseModel):
    """Agent information model"""
    type: str = Field(..., description="Agent type identifier")
    name: str = Field(..., description="Agent display name")
    description: str = Field(..., description="Agent description and capabilities")
    specializations: List[str] = Field(..., description="Agent specialization areas")
    supported_languages: List[str] = Field(..., description="Supported languages")
    urgency_levels: List[str] = Field(..., description="Urgency levels this agent handles")
    average_response_time_ms: int = Field(..., description="Average response time in milliseconds")
    confidence_threshold: float = Field(..., description="Minimum confidence threshold")
    is_available: bool = Field(..., description="Whether agent is currently available")


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    language: Optional[str] = Field("en", pattern="^(en|zh-HK|zh-CN)$", description="Preferred language")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context information")
    agent_type: Optional[str] = Field(None, description="Preferred agent type")


class ChatResponse(BaseModel):
    """Chat response model"""
    message: str = Field(..., description="Agent response message")
    agent_type: str = Field(..., description="Agent that handled the request")
    agent_name: str = Field(..., description="Agent display name")
    confidence: float = Field(..., description="Agent confidence score")
    urgency_level: str = Field(..., description="Detected urgency level")
    language: str = Field(..., description="Response language")
    session_id: str = Field(..., description="Conversation session ID")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    hk_data_used: List[Dict[str, Any]] = Field(..., description="HK data references used")
    routing_info: Dict[str, Any] = Field(..., description="Agent routing decision information")
    conversation_id: int = Field(..., description="Database conversation ID")


class ConversationHistoryItem(BaseModel):
    """Conversation history item model"""
    id: int
    timestamp: datetime
    user_message: str
    agent_response: str
    agent_type: str
    agent_name: str
    confidence: float
    urgency_level: str
    language: str
    user_satisfaction: Optional[int] = None
    processing_time_ms: int
    hk_data_used: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class ConversationHistoryResponse(BaseModel):
    """Conversation history response model"""
    conversations: List[ConversationHistoryItem]
    total: int
    session_id: str
    page: int
    page_size: int


class AgentPerformanceMetrics(BaseModel):
    """Agent performance metrics model"""
    agent_type: str
    period_start: datetime
    period_end: datetime
    total_conversations: int
    average_confidence: float
    average_satisfaction: float
    average_response_time_ms: int
    success_rate: float
    urgency_accuracy_rate: float
    domain_performance: Dict[str, Any]
    language_performance: Dict[str, Any]


class RoutingDecisionInfo(BaseModel):
    """Agent routing decision information"""
    selected_agent: str
    confidence: float
    agent_scores: Dict[str, float]
    routing_factors: Dict[str, Any]
    alternative_agents: List[str]
    routing_time_ms: int


class AgentCapabilitiesResponse(BaseModel):
    """Agent capabilities and status response"""
    available_agents: List[AgentInfo]
    system_status: str
    routing_enabled: bool
    cultural_adaptation: bool
    supported_languages: List[str]
    emergency_detection: bool


# ============================================================================
# AGENT INFORMATION ENDPOINTS
# ============================================================================

@router.get(
    "/info",
    response_model=AgentCapabilitiesResponse,
    summary="Get agent system information",
    description="Get information about available agents and system capabilities",
    responses={
        200: {"description": "Agent information retrieved successfully"},
        500: {"description": "System error"}
    }
)
  # 60 calls per minute
async def get_agent_info(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> AgentCapabilitiesResponse:
    """Get information about available agents and capabilities"""
    start_time = datetime.now()
    
    try:
        # TODO: This will be implemented in Phase 3 with actual agent system
        # For now, return static information about planned agents
        
        available_agents = [
            AgentInfo(
                type="illness_monitor",
                name="慧心助手",
                description="Physical health expert specializing in symptoms, chronic disease management, and HK hospital routing",
                specializations=["physical_health", "symptoms", "chronic_disease", "medication", "hospital_routing"],
                supported_languages=["en", "zh-HK", "zh-CN"],
                urgency_levels=["low", "medium", "high", "emergency"],
                average_response_time_ms=2500,
                confidence_threshold=0.7,
                is_available=True
            ),
            AgentInfo(
                type="mental_health",
                name="小星星",
                description="Mental health expert providing emotional support, counseling, and crisis intervention",
                specializations=["mental_health", "emotional_support", "counseling", "crisis_intervention"],
                supported_languages=["en", "zh-HK", "zh-CN"],
                urgency_levels=["low", "medium", "high", "emergency"],
                average_response_time_ms=3000,
                confidence_threshold=0.6,
                is_available=True
            ),
            AgentInfo(
                type="safety_guardian",
                name="Emergency Expert",
                description="Emergency response specialist for critical situations and first aid guidance",
                specializations=["emergency_response", "first_aid", "crisis_management", "emergency_routing"],
                supported_languages=["en", "zh-HK", "zh-CN"],
                urgency_levels=["high", "emergency"],
                average_response_time_ms=1500,
                confidence_threshold=0.9,
                is_available=True
            ),
            AgentInfo(
                type="wellness_coach",
                name="Preventive Care Expert",
                description="Health promotion specialist focusing on preventive care and lifestyle guidance",
                specializations=["preventive_care", "lifestyle", "wellness", "health_promotion"],
                supported_languages=["en", "zh-HK", "zh-CN"],
                urgency_levels=["low", "medium"],
                average_response_time_ms=2000,
                confidence_threshold=0.6,
                is_available=True
            )
        ]
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return AgentCapabilitiesResponse(
            available_agents=available_agents,
            system_status="operational",
            routing_enabled=True,
            cultural_adaptation=True,
            supported_languages=["en", "zh-HK", "zh-CN"],
            emergency_detection=True
        )
        
    except Exception as e:
        logger.error(f"Error retrieving agent information: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=500,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving agent information"
        )


@router.get(
    "/{agent_type}/info",
    response_model=AgentInfo,
    summary="Get specific agent information",
    description="Get detailed information about a specific agent",
    responses={
        200: {"description": "Agent information retrieved successfully"},
        404: {"description": "Agent not found"},
        500: {"description": "System error"}
    }
)

async def get_specific_agent_info(
    request: Request,
    agent_type: str,
    db: AsyncSession = Depends(get_async_db)
) -> AgentInfo:
    """Get information about a specific agent"""
    start_time = datetime.now()
    
    try:
        # TODO: This will be implemented in Phase 3 with actual agent system
        # For now, return static information based on agent type
        
        agent_info_map = {
            "illness_monitor": AgentInfo(
                type="illness_monitor",
                name="慧心助手",
                description="Physical health expert specializing in symptoms, chronic disease management, and HK hospital routing",
                specializations=["physical_health", "symptoms", "chronic_disease", "medication", "hospital_routing"],
                supported_languages=["en", "zh-HK", "zh-CN"],
                urgency_levels=["low", "medium", "high", "emergency"],
                average_response_time_ms=2500,
                confidence_threshold=0.7,
                is_available=True
            ),
            "mental_health": AgentInfo(
                type="mental_health",
                name="小星星",
                description="Mental health expert providing emotional support, counseling, and crisis intervention",
                specializations=["mental_health", "emotional_support", "counseling", "crisis_intervention"],
                supported_languages=["en", "zh-HK", "zh-CN"],
                urgency_levels=["low", "medium", "high", "emergency"],
                average_response_time_ms=3000,
                confidence_threshold=0.6,
                is_available=True
            ),
            "safety_guardian": AgentInfo(
                type="safety_guardian",
                name="Emergency Expert",
                description="Emergency response specialist for critical situations and first aid guidance",
                specializations=["emergency_response", "first_aid", "crisis_management", "emergency_routing"],
                supported_languages=["en", "zh-HK", "zh-CN"],
                urgency_levels=["high", "emergency"],
                average_response_time_ms=1500,
                confidence_threshold=0.9,
                is_available=True
            ),
            "wellness_coach": AgentInfo(
                type="wellness_coach",
                name="Preventive Care Expert",
                description="Health promotion specialist focusing on preventive care and lifestyle guidance",
                specializations=["preventive_care", "lifestyle", "wellness", "health_promotion"],
                supported_languages=["en", "zh-HK", "zh-CN"],
                urgency_levels=["low", "medium"],
                average_response_time_ms=2000,
                confidence_threshold=0.6,
                is_available=True
            )
        }
        
        if agent_type not in agent_info_map:
            raise NotFoundError(f"Agent type '{agent_type}' not found")
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return agent_info_map[agent_type]
        
    except Exception as e:
        logger.error(f"Error retrieving agent {agent_type} information: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=404 if isinstance(e, NotFoundError) else 500,
            response_time_ms=processing_time,
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
            detail="Error retrieving agent information"
        )


# ============================================================================
# CHAT INTERACTION ENDPOINTS
# ============================================================================

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with AI agents",
    description="Send a message to the AI agent system for processing and response",
    responses={
        200: {"description": "Chat response generated successfully"},
        400: {"description": "Invalid input data"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "System error"}
    }
)
  # 20 chat messages per minute
async def chat_with_agents(
    request: Request,
    chat_request: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_async_db)
) -> ChatResponse:
    """Send a message to the AI agent system"""
    start_time = datetime.now()
    
    try:
        # Sanitize user input
        sanitizer = InputSanitizer()
        safe_message = sanitizer.sanitize_string(chat_request.message, max_length=4000)
        
        if len(safe_message.strip()) == 0:
            raise ValidationError("Message cannot be empty")
        
        # 🚀 PROPER AI AGENT SYSTEM WITH ORCHESTRATOR
        
        # Generate session ID if not provided
        session_id = chat_request.session_id or f"live2d_{int(datetime.now().timestamp())}"
        
        # Initialize AI services and orchestrator
        from src.ai.ai_service import get_ai_service
        from src.agents.orchestrator import AgentOrchestrator
        from src.agents.context_manager import ConversationContextManager
        
        try:
            ai_service = await get_ai_service()
            orchestrator = AgentOrchestrator(ai_service)
            context_manager = ConversationContextManager()
            
            # Create context for the conversation
            user_id = str(current_user.id) if current_user else f"anonymous_{hash(str(request.client.host)) % 10000:04d}"
            
            context = context_manager.create_context(
                user_id=user_id,
                session_id=session_id,
                user_input=safe_message,
                additional_context={
                    "language": chat_request.language or "en",
                    "connection_type": "rest_api",
                    "user_agent": request.headers.get("user-agent", "unknown")
                }
            )
            
            # Route to appropriate agent using sophisticated orchestrator
            selected_agent, routing_result = await orchestrator.route_request(
                user_input=safe_message,
                context=context,
                preferred_agent=chat_request.agent_type
            )
            
            # Generate response using the selected agent
            agent_response = await selected_agent.generate_response(safe_message, context)
            
            # Extract response data
            selected_agent_type = routing_result.selected_agent
            agent_name = selected_agent.agent_id
            confidence = routing_result.confidence
            urgency = "emergency" if routing_result.emergency_override else ("high" if confidence > 0.8 else ("medium" if confidence > 0.6 else "low"))
            response_content = agent_response.content
            
            # Update conversation history with agent response
            user_id = str(current_user.id) if current_user else f"anonymous_{hash(str(request.client.host)) % 10000:04d}"
            conversation_memory = context_manager.get_or_create_conversation_memory(user_id, session_id)
            context_manager.update_conversation_history(
                conversation_memory, 
                response_content, 
                "assistant",
                agent_id=selected_agent_type
            )
            
        except Exception as ai_error:
            # Fallback to wellness coach if AI system fails
            logger.warning(f"AI system error, falling back to wellness coach: {ai_error}")
            selected_agent_type = "wellness_coach"
            agent_name = "Preventive Care Expert"
            confidence = 0.70
            urgency = "low"
            response_content = f"🌟 Welcome to Healthcare AI V2! I'm here to help with your health questions. How can I assist you today? (Note: Our AI system is temporarily using fallback mode)"
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Create conversation record for database
        conversation_data = {
            "session_id": session_id,
            "user_input": safe_message,
            "agent_response": response_content,
            "agent_type": selected_agent_type,
            "agent_confidence": confidence,
            "urgency_level": urgency,
            "language": chat_request.language or "en",
            "processing_time_ms": processing_time,
            "user_id": current_user.id if current_user else None,
            "hk_data_used": [],
            "conversation_context": []
        }
        
        # Store conversation in database if database connection available
        try:
            # This will create a conversation record
            # conversation = await store_conversation(db, conversation_data)
            pass  # For now, just log
        except Exception as db_error:
            # Don't fail the entire request if DB storage fails
            logger.warning(f"Failed to store conversation in database: {db_error}")
        
        # Log agent interaction
        log_agent_interaction(
            agent_type=selected_agent_type,
            user_input=safe_message,
            agent_response=response_content,
            confidence=confidence,
            urgency_level=urgency,
            processing_time_ms=processing_time,
            user_id=current_user.id if current_user else None,
            session_id=session_id
        )
        
        # Log successful request
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id if current_user else None,
            ip_address=request.client.host if request.client else None
        )
        
        # Return successful response
        return ChatResponse(
            message=response_content,
            agent_type=selected_agent_type,
            agent_name=agent_name,
            confidence=confidence,
            urgency_level=urgency,
            language=chat_request.language or "en",
            session_id=session_id,
            processing_time_ms=processing_time,
            hk_data_used=[],
            routing_info={
                "selected_agent": selected_agent_type,
                "confidence": confidence,
                "routing_factors": getattr(routing_result, 'reasons', ["ai_agent_routing"]) if 'routing_result' in locals() else ["fallback_mode"],
                "alternative_agents": getattr(routing_result, 'alternative_agents', ["illness_monitor", "mental_health", "safety_guardian", "wellness_coach"]) if 'routing_result' in locals() else ["illness_monitor", "mental_health", "safety_guardian", "wellness_coach"]
            },
            conversation_id=0  # Placeholder - would be from database
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=500,
            response_time_ms=processing_time,
            user_id=current_user.id if current_user else None,
            ip_address=request.client.host if request.client else None,
            error=str(e)
        )
        
        if isinstance(e, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat request"
        )


# ============================================================================
# CONVERSATION HISTORY ENDPOINTS
# ============================================================================

@router.get(
    "/conversations",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history",
    description="Get conversation history for authenticated user",
    responses={
        200: {"description": "Conversation history retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "System error"}
    }
)

async def get_conversation_history(
    request: Request,
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
) -> ConversationHistoryResponse:
    """Get conversation history for authenticated user"""
    start_time = datetime.now()
    
    try:
        # TODO: This will be implemented with actual conversation repository
        # For now, return empty history
        
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
        
        return ConversationHistoryResponse(
            conversations=[],
            total=0,
            session_id=session_id or "all",
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
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
            detail="Error retrieving conversation history"
        )


# ============================================================================
# PERFORMANCE METRICS ENDPOINTS
# ============================================================================

@router.get(
    "/performance",
    response_model=List[AgentPerformanceMetrics],
    dependencies=[Depends(require_role("admin"))],
    summary="Get agent performance metrics (Admin)",
    description="Get performance metrics for all agents",
    responses={
        200: {"description": "Performance metrics retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        500: {"description": "System error"}
    }
)

async def get_agent_performance(
    request: Request,
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_async_db)
) -> List[AgentPerformanceMetrics]:
    """Get agent performance metrics (admin only)"""
    start_time = datetime.now()
    
    try:
        # TODO: This will be implemented with actual performance tracking
        # For now, return placeholder metrics
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        placeholder_metrics = [
            AgentPerformanceMetrics(
                agent_type="illness_monitor",
                period_start=start_date,
                period_end=end_date,
                total_conversations=0,
                average_confidence=0.0,
                average_satisfaction=0.0,
                average_response_time_ms=0,
                success_rate=0.0,
                urgency_accuracy_rate=0.0,
                domain_performance={},
                language_performance={}
            ),
            AgentPerformanceMetrics(
                agent_type="mental_health",
                period_start=start_date,
                period_end=end_date,
                total_conversations=0,
                average_confidence=0.0,
                average_satisfaction=0.0,
                average_response_time_ms=0,
                success_rate=0.0,
                urgency_accuracy_rate=0.0,
                domain_performance={},
                language_performance={}
            )
        ]
        
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
        
        return placeholder_metrics
        
    except Exception as e:
        logger.error(f"Error retrieving agent performance metrics: {e}")
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
            detail="Error retrieving agent performance metrics"
        )


# ============================================================================
# 🔥 REAL-TIME WEBSOCKET CHAT ENDPOINT
# ============================================================================

@router.websocket("/chat/ws")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    🚀 Real-time WebSocket chat with Healthcare AI agents
    
    Features:
    - Real-time bidirectional communication
    - Live agent responses
    - Typing indicators
    - Emergency escalation alerts
    - Session persistence
    - Anonymous and authenticated chat support
    """
    await websocket.accept()
    
    # Initialize session data
    session_data = {
        "session_id": f"ws_{int(datetime.now().timestamp())}_{hash(str(websocket.client)) % 10000:04d}",
        "user_id": None,
        "connection_time": datetime.now(),
        "message_count": 0,
        "last_agent": None
    }
    
    logger.info(f"WebSocket connection established: {session_data['session_id']}")
    
    try:
        # Send welcome message
        welcome_message = {
            "type": "system",
            "message": "🏥 Welcome to Healthcare AI V2! I'm here to help with your health questions.",
            "session_id": session_data["session_id"],
            "timestamp": datetime.now().isoformat(),
            "agents_available": ["illness_monitor", "mental_health", "safety_guardian", "wellness_coach"]
        }
        await websocket.send_json(welcome_message)
        
        # Initialize AI services
        from src.ai.ai_service import get_ai_service
        from src.agents.orchestrator import AgentOrchestrator
        from src.agents.context_manager import ConversationContextManager
        
        ai_service = await get_ai_service()
        orchestrator = AgentOrchestrator(ai_service)
        context_manager = ConversationContextManager()
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            session_data["message_count"] += 1
            
            if data.get("type") == "chat":
                user_message = data.get("message", "").strip()
                
                if not user_message:
                    await websocket.send_json({
                        "type": "error", 
                        "message": "Empty message received",
                        "timestamp": datetime.now().isoformat()
                    })
                    continue
                
                # Send typing indicator
                await websocket.send_json({
                    "type": "typing",
                    "agent": "AI is thinking...",
                    "timestamp": datetime.now().isoformat()
                })
                
                try:
                    # Process with agent system
                    user_id = session_data["user_id"] or f"ws_anonymous_{hash(str(websocket.client)) % 10000:04d}"
                    
                    # Create context
                    context = context_manager.create_context(
                        user_id=user_id,
                        session_id=session_data["session_id"],
                        user_input=user_message,
                        additional_context={
                            "connection_type": "websocket",
                            "message_count": session_data["message_count"],
                            "last_agent": session_data["last_agent"]
                        }
                    )
                    
                    # Route to agent
                    selected_agent, routing_result = await orchestrator.route_request(
                        user_input=user_message,
                        context=context
                    )
                    
                    # Generate response
                    agent_response = await selected_agent.generate_response(user_message, context)
                    
                    # Update session data
                    session_data["last_agent"] = routing_result.selected_agent
                    
                    # Send response
                    response_data = {
                        "type": "agent_response",
                        "message": agent_response.content,
                        "agent_type": routing_result.selected_agent,
                        "agent_name": selected_agent.agent_id,
                        "confidence": routing_result.confidence,
                        "urgency_level": routing_result.urgency_level,
                        "session_id": session_data["session_id"],
                        "timestamp": datetime.now().isoformat(),
                        "suggested_actions": agent_response.suggested_actions if hasattr(agent_response, 'suggested_actions') else [],
                        "professional_alert": agent_response.professional_alert_needed if hasattr(agent_response, 'professional_alert_needed') else False
                    }
                    
                    await websocket.send_json(response_data)
                    
                    # Send emergency alert if needed
                    if hasattr(agent_response, 'professional_alert_needed') and agent_response.professional_alert_needed:
                        await websocket.send_json({
                            "type": "emergency_alert",
                            "message": "⚠️ This situation may require immediate professional attention. Please consider contacting emergency services (999) or a healthcare provider.",
                            "alert_details": agent_response.alert_details if hasattr(agent_response, 'alert_details') else {},
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    # Log interaction
                    log_agent_interaction(
                        agent_type=routing_result.selected_agent,
                        user_input=user_message,
                        agent_response=agent_response.content,
                        confidence=routing_result.confidence,
                        urgency_level=routing_result.urgency_level,
                        processing_time_ms=0,  # WebSocket doesn't track this easily
                        session_id=session_data["session_id"]
                    )
                    
                except Exception as e:
                    logger.error(f"WebSocket agent processing error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "I'm experiencing technical difficulties. Please try again or contact support if this persists.",
                        "error_code": "AGENT_ERROR",
                        "timestamp": datetime.now().isoformat()
                    })
            
            elif data.get("type") == "ping":
                # Respond to keepalive pings
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            
            elif data.get("type") == "auth":
                # Handle authentication (optional)
                auth_token = data.get("token")
                if auth_token:
                    try:
                        # Validate token and get user
                        from src.web.auth.handlers import token_validator
                        from src.database.repositories.user_repository import UserRepository
                        
                        payload = token_validator.decode_token(auth_token)
                        user_repo = UserRepository()
                        user = await user_repo.get_by_id(int(payload.get("sub")))
                        
                        if user and user.is_active:
                            session_data["user_id"] = str(user.id)
                            await websocket.send_json({
                                "type": "auth_success",
                                "user_id": user.id,
                                "username": user.username,
                                "timestamp": datetime.now().isoformat()
                            })
                        else:
                            await websocket.send_json({
                                "type": "auth_failed",
                                "message": "Invalid authentication",
                                "timestamp": datetime.now().isoformat()
                            })
                    except Exception as e:
                        logger.error(f"WebSocket auth error: {e}")
                        await websocket.send_json({
                            "type": "auth_failed",
                            "message": "Authentication failed",
                            "timestamp": datetime.now().isoformat()
                        })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_data['session_id']}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Connection error occurred",
                "error_code": "CONNECTION_ERROR",
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass  # Connection might already be closed
