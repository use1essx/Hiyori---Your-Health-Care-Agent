"""
API Security utilities for Healthcare AI V2
Handles secure API key management and prevents exposure
"""

import os
import logging
from datetime import datetime
from typing import Optional
from src.config import settings

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Secure API key management utilities"""
    
    @staticmethod
    def get_openrouter_key() -> Optional[str]:
        """
        Safely retrieve OpenRouter API key from environment
        Never logs or exposes the actual key value
        """
        try:
            api_key = settings.openrouter_api_key
            if api_key:
                # Only log that we found a key, never the actual value
                logger.debug("OpenRouter API key loaded from environment")
                return api_key
            else:
                logger.warning("OpenRouter API key not found in environment variables")
                return None
        except Exception as e:
            logger.error(f"Error loading OpenRouter API key: {e}")
            return None
    
    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """
        Safely mask an API key for logging purposes
        Shows only the prefix and suffix for identification
        """
        if not api_key or len(api_key) < 10:
            return "***hidden***"
        
        # Show first 6 characters and last 4, mask the middle
        masked = api_key[:6] + "*" * (len(api_key) - 10) + api_key[-4:]
        return masked
    
    @staticmethod
    def validate_api_key_format(api_key: str) -> bool:
        """
        Validate API key format without exposing the key
        Returns True if format looks correct
        """
        if not api_key:
            return False
            
        # OpenRouter keys should start with 'sk-or-v1-'
        if api_key.startswith('sk-or-v1-') and len(api_key) > 20:
            return True
            
        return False
    
    @staticmethod
    def is_api_key_configured() -> bool:
        """
        Check if API key is configured without exposing it
        """
        api_key = APIKeyManager.get_openrouter_key()
        return api_key is not None and APIKeyManager.validate_api_key_format(api_key)
    
    @staticmethod
    def get_safe_status() -> dict:
        """
        Get API key status for monitoring without exposing sensitive data
        """
        api_key = APIKeyManager.get_openrouter_key()
        
        if not api_key:
            return {
                "configured": False,
                "format_valid": False,
                "status": "not_configured",
                "key_prefix": "***",
                "key_suffix": "***",
                "key_length": 0,
                "source": "environment_variable",
                "last_checked": datetime.now().isoformat()
            }
        
        format_valid = APIKeyManager.validate_api_key_format(api_key)
        
        return {
            "configured": True,
            "format_valid": format_valid,
            "status": "configured" if format_valid else "invalid_format",
            "key_prefix": api_key[:6] if len(api_key) >= 6 else "***",
            "key_suffix": api_key[-4:] if len(api_key) >= 4 else "***",
            "key_length": len(api_key),
            "source": "environment_variable",
            "last_checked": datetime.now().isoformat()
        }


def log_api_operation(operation: str, success: bool, details: str = None):
    """
    Log API operations securely without exposing sensitive data
    """
    if success:
        logger.info(f"API operation successful: {operation}")
    else:
        logger.error(f"API operation failed: {operation} - {details or 'Unknown error'}")


# Security reminder for developers
def _security_reminder():
    """
    Development reminder about API key security
    """
    logger.info(
        "🔒 API Security Reminder: Never log, print, or expose actual API key values. "
        "Use APIKeyManager utilities for safe handling."
    )


# Initialize security reminder in development
if settings.debug:
    _security_reminder()
