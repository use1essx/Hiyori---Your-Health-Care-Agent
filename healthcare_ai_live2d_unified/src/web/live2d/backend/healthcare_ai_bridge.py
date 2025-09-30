#!/usr/bin/env python3
"""
Healthcare AI V2 Bridge for Live2D Integration
Connects the existing Live2D frontend to Healthcare AI V2 backend
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthcareAIBridge:
    """
    Bridge class that connects Live2D frontend to Healthcare AI V2 backend
    """
    
    def __init__(self, healthcare_api_url: str = None):
        # Use environment variable or default to container network
        import os
        if healthcare_api_url is None:
            # In Docker: use container name for service discovery
            healthcare_api_url = os.getenv('HEALTHCARE_AI_URL', 'http://healthcare_ai:8000')
        self.healthcare_api_url = healthcare_api_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Live2D Agent Personality Mappings - MOVED TO INIT
        self._init_agent_personalities()
    
    async def initialize(self):
        """Initialize the healthcare AI bridge"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Test connection to healthcare AI
            health_status = await self.check_healthcare_ai_status()
            if health_status:
                logger.info("Healthcare AI bridge initialized successfully")
            else:
                logger.warning("Healthcare AI backend not available during initialization")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize healthcare AI bridge: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup the healthcare AI bridge"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
            logger.info("Healthcare AI bridge cleaned up")
        except Exception as e:
            logger.error(f"Error during bridge cleanup: {e}")
    
    def _init_agent_personalities(self):
        """Initialize agent personalities mapping"""
        # Live2D Agent Personality Mappings
        self.agent_personalities = {
            "illness_monitor": {
                "name": "慧心助手",
                "name_en": "Medical Assistant",
                "model_preference": "Hiyori",
                "default_emotion": "professional_caring",
                "emotions": {
                    "low": "neutral_professional",
                    "medium": "concerned_attentive", 
                    "high": "urgent_focused",
                    "critical": "emergency_alert"
                },
                "gestures": {
                    "greeting": "bow_respectful",
                    "explaining": "medical_consultation", 
                    "concerned": "concerned_sympathetic",
                    "urgent": "medical_emergency"
                },
                "voice_settings": {
                    "tone": "calm_professional",
                    "speed": "normal",
                    "language_preference": "cantonese_english_mix"
                }
            },
            "wellness_coach": {
                "name": "健康導師",
                "name_en": "Wellness Coach",
                "model_preference": "Natori",
                "default_emotion": "encouraging_positive",
                "emotions": {
                    "low": "gentle_encouraging",
                    "medium": "motivational_supportive",
                    "high": "energetic_enthusiastic", 
                    "critical": "serious_supportive"
                },
                "gestures": {
                    "greeting": "wave_friendly",
                    "explaining": "pointing_educational",
                    "encouraging": "thumbs_up_positive",
                    "celebrating": "clap_celebration"
                },
                "voice_settings": {
                    "tone": "warm_encouraging",
                    "speed": "slightly_slower",
                    "language_preference": "english_primary"
                }
            },
            "mental_health": {
                "name": "心靈輔導師", 
                "name_en": "Mental Health Counselor",
                "model_preference": "Hiyori",
                "default_emotion": "gentle_compassionate",
                "emotions": {
                    "low": "calm_listening",
                    "medium": "empathetic_understanding",
                    "high": "concerned_caring",
                    "critical": "crisis_supportive"
                },
                "gestures": {
                    "greeting": "gentle_nod",
                    "listening": "active_listening",
                    "comforting": "gentle_reassurance",
                    "serious": "serious_concern"
                },
                "voice_settings": {
                    "tone": "soft_caring",
                    "speed": "slower_deliberate", 
                    "language_preference": "native_comfortable"
                }
            },
            "safety_guardian": {
                "name": "安全守護者",
                "name_en": "Safety Guardian", 
                "model_preference": "Mark",
                "default_emotion": "alert_protective",
                "emotions": {
                    "low": "watchful_attentive",
                    "medium": "concerned_alert",
                    "high": "urgent_serious",
                    "critical": "emergency_action"
                },
                "gestures": {
                    "greeting": "alert_acknowledgment",
                    "warning": "urgent_pointing",
                    "emergency": "emergency_directive",
                    "protective": "shielding_gesture"
                },
                "voice_settings": {
                    "tone": "clear_authoritative",
                    "speed": "normal_clear",
                    "language_preference": "clear_direct"
                }
            }
        }
        
        # Hong Kong specific gestures and cultural elements
        self.hk_gestures = {
            "greeting_morning": "morning_bow_respect",
            "greeting_evening": "evening_acknowledgment", 
            "medical_respect": "medical_professional_bow",
            "family_concern": "family_oriented_gesture",
            "traditional_respect": "traditional_courtesy",
            "modern_approach": "contemporary_professional",
            "cantonese_emphasis": "linguistic_cultural_bridge",
            "health_wisdom": "traditional_modern_balance"
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - properly close session"""
        if self.session:
            await self.session.close()
            self.session = None
        self.agent_personalities = {
            "illness_monitor": {
                "name": "慧心助手",
                "name_en": "Medical Assistant",
                "model_preference": "Hiyori",  # Professional, caring
                "default_emotion": "professional_caring",
                "emotions": {
                    "low": "gentle_professional",
                    "medium": "concerned_professional", 
                    "high": "urgent_medical",
                    "emergency": "emergency_alert"
                },
                "gestures": {
                    "greeting": "respectful_bow",
                    "explaining": "medical_consultation",
                    "concerned": "concern_expression",
                    "reassuring": "reassuring_nod"
                },
                "voice_settings": {
                    "tone": "warm_professional",
                    "speed": 0.9,
                    "pitch": 0.8
                }
            },
            "mental_health": {
                "name": "小星星",
                "name_en": "Little Star",
                "model_preference": "Haru",  # Gentle, supportive
                "default_emotion": "gentle_supportive",
                "emotions": {
                    "low": "encouraging_smile",
                    "medium": "listening_attentive",
                    "high": "comforting_warm",
                    "emergency": "urgent_support"
                },
                "gestures": {
                    "greeting": "heart_hands",
                    "listening": "listening_pose",
                    "encouraging": "encouraging_smile",
                    "comforting": "comforting_gesture"
                },
                "voice_settings": {
                    "tone": "soft_caring",
                    "speed": 0.8,
                    "pitch": 1.0
                }
            },
            "safety_guardian": {
                "name": "緊急專家", 
                "name_en": "Emergency Expert",
                "model_preference": "Mao",  # Alert, authoritative
                "default_emotion": "alert_focused",
                "emotions": {
                    "low": "alert_ready",
                    "medium": "urgent_instruction",
                    "high": "emergency_command",
                    "emergency": "critical_emergency"
                },
                "gestures": {
                    "greeting": "emergency_stance",
                    "instructing": "urgent_pointing",
                    "stopping": "stop_gesture",
                    "demonstrating": "first_aid_demo"
                },
                "voice_settings": {
                    "tone": "clear_authoritative",
                    "speed": 1.0,
                    "pitch": 0.7
                }
            },
            "wellness_coach": {
                "name": "健康教練",
                "name_en": "Wellness Coach", 
                "model_preference": "Natori",  # Energetic, motivational
                "default_emotion": "energetic_positive",
                "emotions": {
                    "low": "motivating_gentle",
                    "medium": "encouraging_active",
                    "high": "celebrating_victory",
                    "emergency": "urgent_motivation"
                },
                "gestures": {
                    "greeting": "thumbs_up",
                    "motivating": "motivational_pose",
                    "celebrating": "celebration",
                    "demonstrating": "exercise_demo"
                },
                "voice_settings": {
                    "tone": "upbeat_energetic",
                    "speed": 1.1,
                    "pitch": 1.2
                }
            }
        }
        
        # Hong Kong Cultural Gestures
        self.hk_gestures = {
            "respectful_bow": "Slight bow for formal medical consultation",
            "tea_offering_gesture": "Offering comfort like serving tea",
            "dim_sum_sharing": "Friendly, community-oriented gesture",
            "local_recommendation": "Enthusiastic local suggestion",
            "cantonese_emphasis": "Animated Cantonese-style expression",
            "traditional_greeting": "Formal Hong Kong greeting",
            "cha_chaan_teng_point": "Casual, familiar direction"
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def get_healthcare_response(
        self, 
        user_message: str, 
        language: str = "auto",
        session_id: Optional[str] = None,
        user_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Get response from Healthcare AI V2 backend using subprocess curl (simpler approach)
        """
        try:
            # Prepare request payload with user context
            payload = {
                "message": user_message,
                "language": language,
                "session_id": session_id,
                "context": {
                    "client_type": "live2d",
                    "interface": "chat",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Add user context if available
            if user_context:
                payload["user_context"] = user_context
            
            # Call Healthcare AI V2 chat endpoint using subprocess
            url = f"{self.healthcare_api_url}/api/v1/agents/chat"
            logger.info(f"🎯 Simple POST request to: {url}")
            
            import subprocess
            import json
            
            # Convert payload to JSON string
            payload_json = json.dumps(payload)
            
            # Use curl subprocess to avoid aiohttp session issues
            cmd = [
                "curl", "-X", "POST", url,
                "-H", "Content-Type: application/json",
                "-d", payload_json,
                "--max-time", "30",
                "--silent"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            
            if result.returncode == 0 and result.stdout:
                try:
                    data = json.loads(result.stdout)
                    logger.info(f"✅ Healthcare AI response received for agent: {data.get('agent_type')}")
                    return data
                except json.JSONDecodeError as je:
                    logger.error(f"❌ JSON decode error: {je}")
                    logger.error(f"📄 Raw response: {result.stdout}")
                    return self._get_fallback_response(user_message, language)
            else:
                logger.error(f"❌ Curl error: return code {result.returncode}")
                logger.error(f"📄 Stderr: {result.stderr}")
                return self._get_fallback_response(user_message, language)
                
        except Exception as e:
            logger.error(f"❌ Healthcare AI connection error: {e}")
            logger.error(f"🔍 Exception type: {type(e)}")
            import traceback
            logger.error(f"📄 Full traceback: {traceback.format_exc()}")
            return self._get_fallback_response(user_message, language)

    def _get_fallback_response(self, user_message: str, language: str) -> Dict[str, Any]:
        """
        Fallback response when Healthcare AI is unavailable
        """
        if language == "zh" or any(ord(char) > 127 for char in user_message):
            message = "抱歉，我的醫療AI系統暫時不可用。請稍後再試，或聯繫醫療專業人士。🏥"
            agent_name = "系統助手"
        else:
            message = "Sorry, my healthcare AI system is temporarily unavailable. Please try again later or consult a medical professional. 🏥"
            agent_name = "System Assistant"
        
        return {
            "message": message,
            "agent_type": "illness_monitor",
            "agent_name": agent_name,
            "confidence": 0.5,
            "urgency_level": "low",
            "language": language,
            "session_id": "fallback",
            "processing_time_ms": 100,
            "hk_data_used": [],
            "routing_info": {"fallback": True}
        }

    def map_to_live2d_response(self, healthcare_response: Dict[str, Any], user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Map Healthcare AI response to Live2D format with emotions and gestures
        """
        agent_type = healthcare_response.get("agent_type", "illness_monitor")
        urgency = healthcare_response.get("urgency_level", "low")
        message = healthcare_response.get("message", "")
        language = healthcare_response.get("language", "en")
        
        # Get agent personality
        personality = self.agent_personalities.get(agent_type, self.agent_personalities["illness_monitor"])
        
        # Determine emotion based on urgency and content
        emotion = self._determine_emotion(agent_type, urgency, message)
        
        # Determine gesture based on context
        gesture = self._determine_gesture(agent_type, message, urgency)
        
        # Get recommended Live2D model
        recommended_model = personality["model_preference"]
        
        # Prepare Live2D response
        live2d_response = {
            "reply": message,
            "status": "success",
            "live2d_data": {
                "agent_type": agent_type,
                "agent_name": personality["name"],
                "agent_name_en": personality["name_en"],
                "emotion": emotion,
                "gesture": gesture,
                "recommended_model": recommended_model,
                "voice_settings": personality["voice_settings"],
                "urgency": urgency,
                "language": language,
                "confidence": healthcare_response.get("confidence", 0.8),
                "processing_time_ms": healthcare_response.get("processing_time_ms", 1000),
                "hk_facilities": healthcare_response.get("hk_data_used", []),
                "cultural_context": self._get_cultural_context(language, agent_type),
                "session_id": healthcare_response.get("session_id", "default"),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        logger.info(f"🎭 Live2D Response: {agent_type} -> {emotion} + {gesture} (Model: {recommended_model})")
        return live2d_response

    def _determine_emotion(self, agent_type: str, urgency: str, message: str) -> str:
        """
        Determine appropriate emotion based on agent type, urgency, and message content
        """
        personality = self.agent_personalities.get(agent_type, self.agent_personalities["illness_monitor"])
        
        # Check for specific emotional keywords
        if any(word in message.lower() for word in ["congratulations", "great", "excellent", "wonderful", "恭喜", "好極了", "太好了"]):
            return "celebrating_joyful"
        elif any(word in message.lower() for word in ["sorry", "unfortunately", "concerned", "worried", "抱歉", "擔心", "憂慮"]):
            return "concerned_sympathetic"
        elif any(word in message.lower() for word in ["emergency", "urgent", "immediate", "緊急", "立即", "馬上"]):
            return "urgent_alert"
        
        # Use urgency-based emotions
        emotions = personality.get("emotions", {})
        return emotions.get(urgency, personality["default_emotion"])

    def _determine_gesture(self, agent_type: str, message: str, urgency: str) -> str:
        """
        Determine appropriate gesture based on context
        """
        personality = self.agent_personalities.get(agent_type, self.agent_personalities["illness_monitor"])
        gestures = personality.get("gestures", {})
        
        # Context-based gesture selection
        if "hello" in message.lower() or "hi" in message.lower() or "你好" in message or "哈囉" in message:
            return gestures.get("greeting", "respectful_bow")
        elif any(word in message.lower() for word in ["explain", "tell", "what", "how", "解釋", "告訴", "什麼", "怎樣"]):
            return gestures.get("explaining", "medical_consultation")
        elif any(word in message.lower() for word in ["help", "support", "comfort", "幫助", "支持", "安慰"]):
            return gestures.get("comforting", "comforting_gesture")
        elif urgency in ["high", "emergency"]:
            return gestures.get("urgent", "urgent_pointing")
        
        # Add Hong Kong cultural gestures occasionally
        if random.random() < 0.3:  # 30% chance for cultural gesture
            cultural_gestures = list(self.hk_gestures.keys())
            return random.choice(cultural_gestures)
        
        # Default gesture
        return gestures.get("explaining", "medical_consultation")

    def _get_cultural_context(self, language: str, agent_type: str) -> Dict[str, Any]:
        """
        Get Hong Kong cultural context information
        """
        if language == "zh" or language == "zh-HK":
            return {
                "cultural_notes": {
                    "greeting_style": "formal_respectful",
                    "communication_style": "indirect_polite",
                    "medical_context": "hong_kong_healthcare_system",
                    "language_preference": "traditional_chinese",
                    "cultural_gestures": list(self.hk_gestures.keys())
                },
                "hk_context": {
                    "healthcare_system": "public_private_mixed",
                    "emergency_number": "999",
                    "common_hospitals": ["Queen Mary", "Prince of Wales", "Tuen Mun"],
                    "cultural_sensitivity": "high"
                }
            }
        else:
            return {
                "cultural_notes": {
                    "greeting_style": "professional_friendly",
                    "communication_style": "direct_clear",
                    "medical_context": "international_standards",
                    "language_preference": "english",
                    "cultural_awareness": "hong_kong_expatriate"
                }
            }

    async def process_chat_message(
        self, 
        user_message: str, 
        language: str = "auto",
        session_id: Optional[str] = None,
        user_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Main method to process chat messages through Healthcare AI V2 and return Live2D format
        """
        logger.info(f"🎭 Processing Live2D chat: '{user_message[:50]}...' (lang: {language})")
        
        # Get response from Healthcare AI V2 with user context
        healthcare_response = await self.get_healthcare_response(user_message, language, session_id, user_context)
        logger.info(f"🔄 Got healthcare response, mapping to Live2D format...")
        logger.info(f"📋 Healthcare response data: {healthcare_response}")
        
        # Map to Live2D format
        try:
            live2d_response = self.map_to_live2d_response(healthcare_response, user_context)
            logger.info(f"✅ Live2D mapping completed successfully")
            logger.info(f"📋 Live2D response: {live2d_response}")
            return live2d_response
        except Exception as mapping_error:
            logger.error(f"❌ Mapping error: {mapping_error}")
            import traceback
            logger.error(f"📄 Mapping traceback: {traceback.format_exc()}")
            return self._get_fallback_response(user_message, language)

    async def get_agent_info(self) -> Dict[str, Any]:
        """
        Get available agents information from Healthcare AI V2
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.healthcare_api_url}/api/v1/agents"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Enhance with Live2D personality data
                    enhanced_agents = []
                    for agent in data.get("agents", []):
                        agent_type = agent.get("type")
                        if agent_type in self.agent_personalities:
                            personality = self.agent_personalities[agent_type]
                            agent.update({
                                "live2d_personality": personality,
                                "recommended_model": personality["model_preference"],
                                "cultural_context": "hong_kong_healthcare"
                            })
                        enhanced_agents.append(agent)
                    
                    return {
                        "agents": enhanced_agents,
                        "total": len(enhanced_agents),
                        "live2d_models": list(set([p["model_preference"] for p in self.agent_personalities.values()])),
                        "cultural_gestures": self.hk_gestures
                    }
                else:
                    logger.error(f"❌ Failed to get agent info: {response.status}")
                    return {"agents": [], "error": "Healthcare AI unavailable"}
                    
        except Exception as e:
            logger.error(f"❌ Error getting agent info: {e}")
            return {"agents": [], "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of Healthcare AI V2 connection
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.healthcare_api_url}/health"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "healthcare_ai_status": "healthy",
                        "live2d_bridge_status": "healthy",
                        "backend_info": data,
                        "available_personalities": len(self.agent_personalities),
                        "cultural_gestures": len(self.hk_gestures)
                    }
                else:
                    return {
                        "healthcare_ai_status": "unhealthy",
                        "live2d_bridge_status": "degraded",
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "healthcare_ai_status": "unavailable",
                "live2d_bridge_status": "error",
                "error": str(e)
            }
    
    async def check_healthcare_ai_status(self) -> bool:
        """Check if Healthcare AI backend is available"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(f"{self.healthcare_api_url}/health", timeout=5) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Healthcare AI status check failed: {e}")
            return False
    
    async def get_bridge_status(self) -> Dict[str, Any]:
        """Get bridge status for admin interface"""
        try:
            healthcare_ai_status = await self.check_healthcare_ai_status()
            
            return {
                "healthcare_ai_url": self.healthcare_api_url,
                "healthcare_ai_connected": healthcare_ai_status,
                "session_active": self.session is not None and not self.session.closed,
                "agent_personalities_loaded": len(self.agent_personalities),
                "available_agents": list(self.agent_personalities.keys()),
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting bridge status: {e}")
            return {
                "error": str(e),
                "status": "error"
            }
    
    def get_agent_emotions(self, agent_type: str) -> List[str]:
        """Get available emotions for specific agent type"""
        try:
            if agent_type in self.agent_personalities:
                return list(self.agent_personalities[agent_type]["emotions"].keys())
            return ["neutral", "happy", "concerned", "professional"]
        except Exception as e:
            logger.error(f"Error getting emotions for {agent_type}: {e}")
            return []
    
    def get_agent_gestures(self, agent_type: str) -> List[str]:
        """Get available gestures for specific agent type"""
        try:
            if agent_type in self.agent_personalities:
                return list(self.agent_personalities[agent_type]["gestures"].keys())
            return ["default", "greeting", "explaining", "thinking"]
        except Exception as e:
            logger.error(f"Error getting gestures for {agent_type}: {e}")
            return []
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """Get information about available agents"""
        try:
            return {
                "available_agents": list(self.agent_personalities.keys()),
                "agent_details": {
                    agent_type: {
                        "name": details["name"],
                        "name_en": details["name_en"],
                        "model_preference": details["model_preference"],
                        "default_emotion": details["default_emotion"]
                    }
                    for agent_type, details in self.agent_personalities.items()
                },
                "total_agents": len(self.agent_personalities)
            }
        except Exception as e:
            logger.error(f"Error getting agent info: {e}")
            return {"error": str(e)}

# Global bridge instance - lazy initialization
bridge = None

def get_bridge():
    """Get or create the global bridge instance"""
    global bridge
    if bridge is None:
        bridge = HealthcareAIBridge()
    return bridge

# Convenience functions for the main chatbot backend
async def get_live2d_healthcare_response(user_message: str, language: str = "auto", session_id: Optional[str] = None, user_context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Convenience function to get Healthcare AI response in Live2D format with user context
    """
    async with HealthcareAIBridge() as bridge:
        return await bridge.process_chat_message(user_message, language, session_id, user_context)

def detect_language_enhanced(message: str) -> str:
    """
    Enhanced language detection for Hong Kong context
    """
    chinese_chars = sum(1 for char in message if '\u4e00' <= char <= '\u9fff')
    total_chars = len([char for char in message if char.isalpha() or '\u4e00' <= char <= '\u9fff'])
    
    if total_chars == 0:
        return "auto"
    
    chinese_ratio = chinese_chars / total_chars
    
    # Hong Kong specific detection
    hk_indicators = ['香港', '港', '茶餐廳', '地鐵', 'MTR', '999', '廣東話', '粵語']
    has_hk_context = any(indicator in message for indicator in hk_indicators)
    
    if chinese_ratio > 0.5 or has_hk_context:
        return "zh-HK"  # Traditional Chinese (Hong Kong)
    elif chinese_ratio < 0.1:
        return "en"  # English
    else:
        return "auto"  # Mixed language

if __name__ == "__main__":
    # Test the bridge
    async def test_bridge():
        async with HealthcareAIBridge() as bridge:
            # Test health check
            health = await bridge.health_check()
            print("🏥 Health Check:", json.dumps(health, indent=2))
            
            # Test agent info
            agents = await bridge.get_agent_info()
            print("🤖 Agents:", json.dumps(agents, indent=2))
            
            # Test chat
            response = await bridge.process_chat_message("我頭痛，點算好？", "zh-HK")
            print("💬 Chat Response:", json.dumps(response, indent=2))
    
    asyncio.run(test_bridge())
