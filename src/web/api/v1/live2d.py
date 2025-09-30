"""
Live2D REST API Endpoints - Healthcare AI V2
============================================

RESTful API endpoints specifically designed for Live2D frontend integration.
Provides comprehensive access to agent personalities, emotion mappings,
cultural gestures, system status, and healthcare-specific functionality.

Features:
- Agent personality and capability endpoints
- Emotion mapping and configuration endpoints
- Cultural gesture library access
- System status and health monitoring
- Healthcare data visualization endpoints
- Performance metrics and analytics
- Security and authentication integration
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.exceptions import NotFoundError, ValidationError, SecurityError
from src.core.logging import get_logger, log_api_request
from src.core.security import InputSanitizer
from src.database.connection import get_async_db
from src.web.auth.dependencies import get_current_user, get_optional_user
# from src.agents.emotion_mapper import EmotionMapper, emotion_mapper
# from src.agents.gesture_library import GestureLibrary, gesture_library
# from src.integrations.live2d_client import Live2DMessageFormatter, live2d_client
# from src.web.websockets.chat import live2d_chat_handler


logger = get_logger(__name__)
router = APIRouter(prefix="/live2d", tags=["live2d"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AgentPersonalityResponse(BaseModel):
    """Agent personality information for Live2D"""
    agent_type: str
    agent_name: str
    display_name_en: str
    display_name_zh: str
    personality_description: str
    specializations: List[str]
    available_emotions: List[str]
    available_gestures: List[str]
    voice_settings: Dict[str, Any]
    cultural_adaptations: Dict[str, Any]
    urgency_levels: List[str]
    confidence_threshold: float
    is_available: bool


class EmotionMappingResponse(BaseModel):
    """Emotion mapping information for Live2D"""
    emotion_id: str
    display_name: str
    display_name_zh: str
    category: str
    intensity: str
    agent_types: List[str]
    triggers: List[str]
    cultural_variants: Dict[str, str]
    description: str
    animation_notes: str


class GestureMappingResponse(BaseModel):
    """Gesture mapping information for Live2D"""
    gesture_id: str
    display_name: str
    display_name_zh: str
    category: str
    intensity: str
    cultural_context: List[str]
    agent_types: List[str]
    trigger_contexts: List[str]
    cantonese_expressions: List[str]
    traditional_meaning: str
    modern_adaptation: str
    description: str
    accessibility_notes: str
    animation_notes: str


class ChatRequest(BaseModel):
    """Chat request for Live2D integration"""
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    language: str = Field(default="en", pattern="^(en|zh-HK)$")
    agent_preference: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    
    @validator('message')
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Message cannot be empty')
        return v.strip()


class Live2DChatResponse(BaseModel):
    """Live2D-specific chat response"""
    message_id: str
    agent_type: str
    agent_name: str
    message: str
    emotion: str
    gesture: str
    urgency: str
    language: str
    confidence: float
    processing_time_ms: int
    
    # Live2D specific
    avatar_state: Dict[str, Any]
    voice_settings: Dict[str, Any]
    animation_cues: List[str]
    
    # Healthcare specific
    hk_facilities: List[Dict[str, Any]]
    emergency_info: Optional[Dict[str, Any]]
    
    # Metadata
    session_id: str
    timestamp: str


class SystemStatusResponse(BaseModel):
    """System status for Live2D integration"""
    status: str
    timestamp: str
    uptime_seconds: int
    available_agents: List[str]
    active_connections: int
    features_enabled: List[str]
    performance_metrics: Dict[str, Any]
    live2d_integration: Dict[str, Any]


class HealthDataVisualizationRequest(BaseModel):
    """Request for health data visualization"""
    data_type: str
    filters: Optional[Dict[str, Any]] = None
    visualization_type: str = "dashboard"
    language: str = "en"
    session_id: str


class EmotionAnalysisRequest(BaseModel):
    """Request for emotion analysis"""
    text: str = Field(..., min_length=1, max_length=1000)
    language: str = Field(default="en", pattern="^(en|zh-HK)$")
    context: Optional[Dict[str, Any]] = None


class GestureRecommendationRequest(BaseModel):
    """Request for gesture recommendations"""
    agent_type: str
    context: str = Field(..., min_length=1, max_length=500)
    language: str = Field(default="en", pattern="^(en|zh-HK)$")
    urgency: str = Field(default="medium", pattern="^(low|medium|high|emergency)$")
    user_profile: Optional[Dict[str, Any]] = None


# ============================================================================
# AGENT PERSONALITY ENDPOINTS
# ============================================================================

@router.get(
    "/agents",
    response_model=List[AgentPersonalityResponse],
    summary="Get all agents with Live2D personalities",
    description="Get comprehensive information about all healthcare AI agents for Live2D avatar mapping"
)
async def get_all_agents(
    request: Request,
    language: str = Query(default="en", regex="^(en|zh-HK)$"),
    include_unavailable: bool = Query(default=False)
) -> List[AgentPersonalityResponse]:
    """Get all agents with Live2D personality information"""
    start_time = datetime.now()
    
    try:
        # Get agent information from orchestrator
        if hasattr(live2d_chat_handler, 'agent_orchestrator') and live2d_chat_handler.agent_orchestrator:
            available_agents = live2d_chat_handler.agent_orchestrator.get_available_agents()
        else:
            # Fallback to static agent list
            available_agents = ["illness_monitor", "mental_health", "safety_guardian", "wellness_coach"]
        
        agent_personalities = []
        
        for agent_type in available_agents:
            # Get available emotions for agent
            available_emotions = [
                emotion.emotion_id for emotion in emotion_mapper.get_available_emotions(agent_type)
            ]
            
            # Get available gestures for agent
            available_gestures = [
                gesture.gesture_id for gesture in gesture_library.get_gestures_by_agent(agent_type)
            ]
            
            # Get voice settings
            voice_settings = live2d_chat_handler.message_formatter.voice_settings.get(
                agent_type, 
                live2d_chat_handler.message_formatter.voice_settings["illness_monitor"]
            )
            
            # Create personality response
            personality = AgentPersonalityResponse(
                agent_type=agent_type,
                agent_name=_get_agent_name(agent_type, "en"),
                display_name_en=_get_agent_name(agent_type, "en"),
                display_name_zh=_get_agent_name(agent_type, "zh-HK"),
                personality_description=_get_agent_description(agent_type, language),
                specializations=_get_agent_specializations(agent_type),
                available_emotions=available_emotions,
                available_gestures=available_gestures,
                voice_settings=voice_settings,
                cultural_adaptations=_get_cultural_adaptations(agent_type),
                urgency_levels=["low", "medium", "high", "emergency"],
                confidence_threshold=0.6,
                is_available=True
            )
            
            agent_personalities.append(personality)
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return agent_personalities
        
    except Exception as e:
        logger.error(f"Error getting agent personalities: {e}")
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
            detail="Error retrieving agent personalities"
        )


@router.get(
    "/agents/{agent_type}",
    response_model=AgentPersonalityResponse,
    summary="Get specific agent personality",
    description="Get detailed Live2D personality information for a specific agent"
)
async def get_agent_personality(
    request: Request,
    agent_type: str,
    language: str = Query(default="en", regex="^(en|zh-HK)$"),
    db: AsyncSession = Depends(get_async_db)
) -> AgentPersonalityResponse:
    """Get specific agent personality information"""
    start_time = datetime.now()
    
    try:
        # Validate agent type
        valid_agents = ["illness_monitor", "mental_health", "safety_guardian", "wellness_coach"]
        if agent_type not in valid_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent type '{agent_type}' not found"
            )
        
        # Get agent emotions and gestures
        available_emotions = [
            emotion.emotion_id for emotion in emotion_mapper.get_available_emotions(agent_type)
        ]
        
        available_gestures = [
            gesture.gesture_id for gesture in gesture_library.get_gestures_by_agent(agent_type)
        ]
        
        # Get voice settings
        voice_settings = live2d_chat_handler.message_formatter.voice_settings.get(
            agent_type,
            live2d_chat_handler.message_formatter.voice_settings["illness_monitor"]
        )
        
        personality = AgentPersonalityResponse(
            agent_type=agent_type,
            agent_name=_get_agent_name(agent_type, "en"),
            display_name_en=_get_agent_name(agent_type, "en"),
            display_name_zh=_get_agent_name(agent_type, "zh-HK"),
            personality_description=_get_agent_description(agent_type, language),
            specializations=_get_agent_specializations(agent_type),
            available_emotions=available_emotions,
            available_gestures=available_gestures,
            voice_settings=voice_settings,
            cultural_adaptations=_get_cultural_adaptations(agent_type),
            urgency_levels=["low", "medium", "high", "emergency"],
            confidence_threshold=0.6,
            is_available=True
        )
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return personality
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent personality {agent_type}: {e}")
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
            detail=f"Error retrieving agent personality: {agent_type}"
        )


# ============================================================================
# EMOTION MAPPING ENDPOINTS
# ============================================================================

@router.get(
    "/emotions",
    response_model=List[EmotionMappingResponse],
    summary="Get all emotion mappings",
    description="Get all available emotion mappings for Live2D avatars"
)
async def get_all_emotions(
    request: Request,
    agent_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    language: str = Query(default="en", regex="^(en|zh-HK)$"),
    db: AsyncSession = Depends(get_async_db)
) -> List[EmotionMappingResponse]:
    """Get all emotion mappings with optional filtering"""
    start_time = datetime.now()
    
    try:
        # Get emotions (filtered if requested)
        if agent_type:
            emotions = emotion_mapper.get_available_emotions(agent_type)
        else:
            emotions = emotion_mapper.get_available_emotions()
        
        # Filter by category if specified
        if category:
            emotions = [e for e in emotions if e.category.value == category]
        
        emotion_responses = []
        for emotion in emotions:
            emotion_response = EmotionMappingResponse(
                emotion_id=emotion.emotion_id,
                display_name=emotion.display_name,
                display_name_zh=emotion.cultural_variants.get("zh-HK", emotion.display_name),
                category=emotion.category.value,
                intensity=emotion.intensity.value,
                agent_types=emotion.agent_types,
                triggers=emotion.triggers,
                cultural_variants=emotion.cultural_variants,
                description=emotion.description,
                animation_notes=f"Emotion animation for Live2D: {emotion.display_name}"
            )
            emotion_responses.append(emotion_response)
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return emotion_responses
        
    except Exception as e:
        logger.error(f"Error getting emotion mappings: {e}")
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
            detail="Error retrieving emotion mappings"
        )


@router.get(
    "/emotions/{agent_type}",
    response_model=List[EmotionMappingResponse],
    summary="Get emotions for specific agent",
    description="Get emotion mappings available for a specific agent type"
)
async def get_agent_emotions(
    request: Request,
    agent_type: str,
    urgency: Optional[str] = Query(None, regex="^(low|medium|high|emergency)$"),
    db: AsyncSession = Depends(get_async_db)
) -> List[EmotionMappingResponse]:
    """Get emotions for specific agent type"""
    start_time = datetime.now()
    
    try:
        # Validate agent type
        valid_agents = ["illness_monitor", "mental_health", "safety_guardian", "wellness_coach"]
        if agent_type not in valid_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent type '{agent_type}' not found"
            )
        
        # Get emotions for agent
        emotions = emotion_mapper.get_available_emotions(agent_type)
        
        emotion_responses = []
        for emotion in emotions:
            # Include recommended emotion for urgency if specified
            recommended = False
            if urgency:
                recommended_emotion = emotion_mapper.get_emotion_for_urgency(agent_type, urgency)
                recommended = (emotion.emotion_id == recommended_emotion)
            
            emotion_response = EmotionMappingResponse(
                emotion_id=emotion.emotion_id,
                display_name=emotion.display_name,
                display_name_zh=emotion.cultural_variants.get("zh-HK", emotion.display_name),
                category=emotion.category.value,
                intensity=emotion.intensity.value,
                agent_types=emotion.agent_types,
                triggers=emotion.triggers,
                cultural_variants=emotion.cultural_variants,
                description=emotion.description,
                animation_notes=f"Recommended for {urgency}" if recommended else emotion.description
            )
            emotion_responses.append(emotion_response)
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return emotion_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting emotions for agent {agent_type}: {e}")
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
            detail=f"Error retrieving emotions for agent: {agent_type}"
        )


@router.post(
    "/emotions/analyze",
    response_model=Dict[str, Any],
    summary="Analyze text for emotion mapping",
    description="Analyze text content to determine appropriate emotion mapping"
)
async def analyze_emotion(
    request: Request,
    emotion_request: EmotionAnalysisRequest,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Analyze text for emotion mapping"""
    start_time = datetime.now()
    
    try:
        # Import sentiment analysis function
        from src.agents.emotion_mapper import analyze_response_sentiment
        
        # Analyze sentiment
        sentiment, confidence = analyze_response_sentiment(
            emotion_request.text, 
            emotion_request.language
        )
        
        # Get recommended emotions based on sentiment
        recommended_emotions = []
        if sentiment == "positive":
            recommended_emotions = ["encouraging_youthful", "celebratory_joyful", "energetic_positive"]
        elif sentiment == "negative":
            recommended_emotions = ["gentle_supportive", "concerned_medical", "reassuring_medical"]
        else:
            recommended_emotions = ["professional_caring", "neutral", "listening_attentive"]
        
        analysis_result = {
            "text": emotion_request.text,
            "language": emotion_request.language,
            "sentiment": sentiment,
            "confidence": confidence,
            "recommended_emotions": recommended_emotions,
            "analysis_timestamp": datetime.now().isoformat(),
            "context_factors": {
                "text_length": len(emotion_request.text),
                "language_detected": emotion_request.language,
                "keywords_found": []  # Could be enhanced with keyword extraction
            }
        }
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error analyzing emotion: {e}")
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
            detail="Error analyzing emotion"
        )


# ============================================================================
# GESTURE MAPPING ENDPOINTS
# ============================================================================

@router.get(
    "/gestures",
    response_model=List[GestureMappingResponse],
    summary="Get all cultural gestures",
    description="Get all available cultural gestures for Live2D avatars"
)
async def get_all_gestures(
    request: Request,
    agent_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cultural_context: Optional[str] = Query(None),
    language: str = Query(default="en", regex="^(en|zh-HK)$"),
    db: AsyncSession = Depends(get_async_db)
) -> List[GestureMappingResponse]:
    """Get all cultural gestures with optional filtering"""
    start_time = datetime.now()
    
    try:
        # Get all gestures
        all_gestures = list(gesture_library.gesture_library.values())
        
        # Apply filters
        if agent_type:
            all_gestures = [g for g in all_gestures if agent_type in g.agent_types]
        
        if category:
            all_gestures = [g for g in all_gestures if g.category.value == category]
        
        if cultural_context:
            all_gestures = [
                g for g in all_gestures 
                if any(ctx.value == cultural_context for ctx in g.cultural_context)
            ]
        
        gesture_responses = []
        for gesture in all_gestures:
            gesture_response = GestureMappingResponse(
                gesture_id=gesture.gesture_id,
                display_name=gesture.display_name,
                display_name_zh=gesture.display_name,  # Already in Chinese
                category=gesture.category.value,
                intensity=gesture.intensity.value,
                cultural_context=[ctx.value for ctx in gesture.cultural_context],
                agent_types=gesture.agent_types,
                trigger_contexts=gesture.trigger_contexts,
                cantonese_expressions=gesture.cantonese_expressions,
                traditional_meaning=gesture.traditional_meaning,
                modern_adaptation=gesture.modern_adaptation,
                description=gesture.description,
                accessibility_notes=gesture.accessibility_notes,
                animation_notes=gesture.animation_notes
            )
            gesture_responses.append(gesture_response)
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return gesture_responses
        
    except Exception as e:
        logger.error(f"Error getting gesture mappings: {e}")
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
            detail="Error retrieving gesture mappings"
        )


@router.post(
    "/gestures/recommend",
    response_model=List[str],
    summary="Get gesture recommendations",
    description="Get recommended gestures based on context and agent type"
)
async def recommend_gestures(
    request: Request,
    gesture_request: GestureRecommendationRequest,
    db: AsyncSession = Depends(get_async_db)
) -> List[str]:
    """Get gesture recommendations for context"""
    start_time = datetime.now()
    
    try:
        # Get recommended gesture
        recommended_gesture = gesture_library.get_cultural_gesture(
            agent_type=gesture_request.agent_type,
            context=gesture_request.context,
            language=gesture_request.language,
            urgency=gesture_request.urgency,
            user_age_group=gesture_request.user_profile.get("age_group") if gesture_request.user_profile else None,
            cultural_preference="modern_hk"
        )
        
        # Get alternative gestures
        alternative_gestures = []
        agent_gestures = gesture_library.get_gestures_by_agent(gesture_request.agent_type)
        
        for gesture in agent_gestures[:5]:  # Top 5 alternatives
            if gesture.gesture_id != recommended_gesture:
                alternative_gestures.append(gesture.gesture_id)
        
        # Combine primary recommendation with alternatives
        recommendations = [recommended_gesture] + alternative_gestures[:4]
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error recommending gestures: {e}")
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
            detail="Error recommending gestures"
        )


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================

@router.post(
    "/chat",
    response_model=Live2DChatResponse,
    summary="Live2D chat endpoint",
    description="Chat with healthcare AI agents with Live2D-specific formatting"
)
async def live2d_chat(
    request: Request,
    chat_request: ChatRequest,
    current_user=Depends(get_optional_user),
    db: AsyncSession = Depends(get_async_db)
) -> Live2DChatResponse:
    """Process chat request with Live2D-specific response formatting"""
    start_time = datetime.now()
    
    try:
        # Initialize agents if needed
        if not live2d_chat_handler.agent_orchestrator:
            await live2d_chat_handler.initialize_agents()
        
        # Sanitize input
        sanitizer = InputSanitizer()
        safe_message = sanitizer.sanitize_string(chat_request.message, max_length=4000)
        
        # Generate session ID if not provided
        session_id = chat_request.session_id or f"rest_{int(datetime.now().timestamp())}"
        
        # Create user context
        user_context = chat_request.user_context or {}
        if current_user:
            user_context.update({
                "user_id": str(current_user.id),
                "authenticated": True
            })
        
        # Process with agent system (similar to WebSocket handler)
        if live2d_chat_handler.agent_orchestrator:
            # Create agent context
            from src.agents.base_agent import AgentContext
            
            context = AgentContext(
                user_id=user_context.get("user_id", f"rest_anonymous_{hash(str(request.client.host)) % 10000:04d}"),
                session_id=session_id,
                conversation_history=[],
                user_profile=user_context,
                cultural_context={
                    "region": "hong_kong",
                    "language": chat_request.language,
                    "connection_type": "rest_api"
                },
                language_preference=chat_request.language,
                timestamp=datetime.now()
            )
            
            # Route to agent
            selected_agent, routing_result = await live2d_chat_handler.agent_orchestrator.route_request(
                user_input=safe_message,
                context=context,
                preferred_agent=chat_request.agent_preference
            )
            
            # Generate response
            agent_response = await selected_agent.generate_response(safe_message, context)
            
            # Format for Live2D
            live2d_response = live2d_chat_handler.message_formatter.format_agent_response(
                {
                    "agent_type": routing_result.selected_agent,
                    "agent_name": selected_agent.agent_id,
                    "message": agent_response.content,
                    "urgency_level": routing_result.urgency_level,
                    "confidence": routing_result.confidence,
                    "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                    "hk_data_used": []
                },
                session_id,
                chat_request.language,
                user_context
            )
            
            # Convert to response model
            response = Live2DChatResponse(
                message_id=live2d_response.message_id,
                agent_type=live2d_response.agent_type,
                agent_name=live2d_response.agent_name,
                message=live2d_response.message,
                emotion=live2d_response.emotion,
                gesture=live2d_response.gesture,
                urgency=live2d_response.urgency,
                language=live2d_response.language,
                confidence=live2d_response.confidence,
                processing_time_ms=live2d_response.processing_time_ms,
                avatar_state=live2d_response.avatar_state.__dict__ if live2d_response.avatar_state else {},
                voice_settings=live2d_response.voice_settings or {},
                animation_cues=live2d_response.animation_cues,
                hk_facilities=live2d_response.hk_facilities,
                emergency_info=live2d_response.emergency_info,
                session_id=live2d_response.session_id,
                timestamp=live2d_response.timestamp
            )
        
        else:
            # Fallback response
            response = Live2DChatResponse(
                message_id=f"fallback_{int(datetime.now().timestamp())}",
                agent_type="wellness_coach",
                agent_name="Healthcare Assistant",
                message="I'm experiencing some technical difficulties. Please try again or contact support.",
                emotion="professional_caring",
                gesture="reassuring_nod",
                urgency="low",
                language=chat_request.language,
                confidence=0.5,
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                avatar_state={},
                voice_settings={},
                animation_cues=[],
                hk_facilities=[],
                emergency_info=None,
                session_id=session_id,
                timestamp=datetime.now().isoformat()
            )
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            user_id=current_user.id if current_user else None,
            ip_address=request.client.host if request.client else None
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing Live2D chat: {e}")
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
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat request"
        )


# ============================================================================
# SYSTEM STATUS ENDPOINTS
# ============================================================================

@router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="Get Live2D integration status",
    description="Get comprehensive system status for Live2D integration"
)
async def get_system_status(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> SystemStatusResponse:
    """Get system status for Live2D integration"""
    start_time = datetime.now()
    
    try:
        # Get WebSocket connection stats
        ws_stats = live2d_chat_handler.get_connection_stats()
        
        # Get emotion mapper stats
        emotion_stats = emotion_mapper.get_cache_stats()
        
        # Get gesture library stats
        gesture_stats = gesture_library.get_usage_statistics()
        
        # Get Live2D client stats
        client_stats = live2d_client.get_connection_stats()
        
        status_response = SystemStatusResponse(
            status="operational",
            timestamp=datetime.now().isoformat(),
            uptime_seconds=int((datetime.now() - start_time).total_seconds()),
            available_agents=["illness_monitor", "mental_health", "safety_guardian", "wellness_coach"],
            active_connections=ws_stats.get("active_connections", 0),
            features_enabled=[
                "real_time_chat",
                "emotion_mapping",
                "cultural_gestures",
                "hk_data_integration",
                "emergency_detection",
                "bilingual_support"
            ],
            performance_metrics={
                "total_connections": ws_stats.get("total_connections", 0),
                "total_messages": ws_stats.get("total_messages_processed", 0),
                "average_response_time_ms": ws_stats.get("average_response_time_ms", 0),
                "emotion_cache_size": emotion_stats.get("cache_size", 0),
                "gesture_cache_size": gesture_stats.get("cache_size", 0),
                "live2d_client_success_rate": client_stats.get("success_rate", 0.0)
            },
            live2d_integration={
                "emotion_system_active": True,
                "gesture_library_loaded": True,
                "voice_synthesis_ready": True,
                "avatar_states_synced": True,
                "frontend_connected": client_stats.get("is_connected", False),
                "total_emotions": emotion_stats.get("total_emotions", 0),
                "total_gestures": gesture_stats.get("total_gestures", 0),
                "cultural_adaptations": ["traditional_chinese", "modern_hk", "cantonese_expressions"]
            }
        )
        
        # Log successful request
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        log_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=200,
            response_time_ms=processing_time,
            ip_address=request.client.host if request.client else None
        )
        
        return status_response
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
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
            detail="Error retrieving system status"
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _get_agent_name(agent_type: str, language: str) -> str:
    """Get agent name in specified language"""
    names = {
        "illness_monitor": {"en": "Health Assistant", "zh-HK": "慧心助手"},
        "mental_health": {"en": "Little Star", "zh-HK": "小星星"},
        "safety_guardian": {"en": "Emergency Expert", "zh-HK": "緊急專家"},
        "wellness_coach": {"en": "Wellness Coach", "zh-HK": "健康教練"}
    }
    return names.get(agent_type, {}).get(language, "Healthcare Assistant")


def _get_agent_description(agent_type: str, language: str) -> str:
    """Get agent description in specified language"""
    descriptions = {
        "illness_monitor": {
            "en": "Professional health assistant specializing in physical symptoms, chronic disease management, and Hong Kong hospital routing.",
            "zh-HK": "專業健康助手，專門處理身體症狀、慢性疾病管理和香港醫院指引。"
        },
        "mental_health": {
            "en": "Supportive mental health companion providing emotional support, counseling, and crisis intervention with a youthful, caring personality.",
            "zh-HK": "支持性心理健康伴侶，提供情感支持、輔導和危機干預，具有年輕、關懷的個性。"
        },
        "safety_guardian": {
            "en": "Emergency response specialist providing immediate guidance for critical situations and first aid instructions.",
            "zh-HK": "緊急應變專家，為危急情況提供即時指導和急救指示。"
        },
        "wellness_coach": {
            "en": "Energetic wellness coach focused on health promotion, preventive care, and lifestyle guidance.",
            "zh-HK": "充滿活力的健康教練，專注於健康促進、預防護理和生活方式指導。"
        }
    }
    return descriptions.get(agent_type, {}).get(language, "Healthcare AI Assistant")


def _get_agent_specializations(agent_type: str) -> List[str]:
    """Get agent specializations"""
    specializations = {
        "illness_monitor": ["physical_health", "symptoms", "chronic_disease", "medication", "hospital_routing"],
        "mental_health": ["mental_health", "emotional_support", "counseling", "crisis_intervention", "youth_support"],
        "safety_guardian": ["emergency_response", "first_aid", "crisis_management", "safety_protocols"],
        "wellness_coach": ["preventive_care", "lifestyle", "wellness", "health_promotion", "exercise_guidance"]
    }
    return specializations.get(agent_type, ["general_healthcare"])


def _get_cultural_adaptations(agent_type: str) -> Dict[str, Any]:
    """Get cultural adaptations for agent"""
    return {
        "hong_kong_context": True,
        "traditional_chinese_support": True,
        "cantonese_expressions": True,
        "cultural_gestures": True,
        "local_healthcare_knowledge": True,
        "respectful_communication": True
    }
