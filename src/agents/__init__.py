"""
Healthcare AI V2 - Agent System
===============================

Core AI agent system for Healthcare AI V2, providing specialized healthcare
assistance through intelligent agent routing and response generation.

This module implements:
- Abstract base agent interface
- Specialized healthcare agents (illness monitoring, mental health, safety)
- Agent orchestration and routing
- Context management and conversation history
- Emergency detection and professional alerts

Agents:
- BaseAgent: Abstract base class for all agents
- IllnessMonitorAgent: Physical health monitoring (慧心助手)
- MentalHealthAgent: Mental health support (小星星)
- SafetyGuardianAgent: Emergency response
- WellnessCoachAgent: Preventive health coaching

Architecture:
- Context-aware agent selection
- Conversation history management
- Cultural adaptation (Hong Kong specific)
- Professional alert integration
- Emergency override mechanisms
"""

from .base_agent import BaseAgent
from .illness_monitor import IllnessMonitorAgent
from .mental_health import MentalHealthAgent
from .safety_guardian import SafetyGuardianAgent
from .wellness_coach import WellnessCoachAgent
from .orchestrator import AgentOrchestrator
from .context_manager import ConversationContextManager

__all__ = [
    "BaseAgent",
    "IllnessMonitorAgent", 
    "MentalHealthAgent",
    "SafetyGuardianAgent",
    "WellnessCoachAgent",
    "AgentOrchestrator",
    "ConversationContextManager",
]
