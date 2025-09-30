"""
Healthcare AI V2 - Configuration Management
Centralized configuration using Pydantic Settings for type safety and validation
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator, model_validator

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for pydantic v1
    from pydantic import BaseSettings

# Type aliases for URL validation
PostgresDsn = str
RedisDsn = str


class Settings(BaseSettings):
    """
    Application settings with environment variable support and validation
    """
    
    # =============================================================================
    # APPLICATION CONFIGURATION
    # =============================================================================
    
    app_name: str = Field(default="Healthcare AI V2", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="APP_HOST")
    port: int = Field(default=8000, env="APP_PORT")
    reload: bool = Field(default=False, env="RELOAD")
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    # =============================================================================
    # SECURITY CONFIGURATION
    # =============================================================================
    
    secret_key: str = Field(..., env="SECRET_KEY", min_length=32)
    jwt_secret_key: Optional[str] = Field(default=None, env="JWT_SECRET_KEY")
    
    # Token Configuration
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Password Policy
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    account_lockout_duration_minutes: int = Field(default=30, env="ACCOUNT_LOCKOUT_DURATION_MINUTES")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    
    database_host: str = Field(default="localhost", env="DATABASE_HOST")
    database_port: int = Field(default=5432, env="DATABASE_PORT")
    database_name: str = Field(default="healthcare_ai_v2", env="DATABASE_NAME")
    database_user: str = Field(default="admin", env="DATABASE_USER")
    database_password: str = Field(..., env="DATABASE_PASSWORD")
    
    # Connection Pool Settings
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    
    # Database URLs (auto-generated or override)
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_sync_url: Optional[str] = Field(default=None, env="DATABASE_SYNC_URL")
    
    # =============================================================================
    # REDIS CONFIGURATION
    # =============================================================================
    
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Redis URL (auto-generated or override)
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # Cache TTL Settings (in seconds)
    redis_cache_ttl: int = Field(default=3600, env="REDIS_CACHE_TTL")  # 1 hour
    redis_session_ttl: int = Field(default=1800, env="REDIS_SESSION_TTL")  # 30 minutes
    hk_data_cache_ttl: int = Field(default=1800, env="HK_DATA_CACHE_TTL")  # 30 minutes
    
    # =============================================================================
    # EXTERNAL API CONFIGURATION
    # =============================================================================
    
    # AI Provider Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=2000, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    
    # OpenRouter Configuration
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    openrouter_default_model: str = Field(default="lite", env="OPENROUTER_DEFAULT_MODEL")
    openrouter_app_name: str = Field(default="Healthcare AI V2", env="OPENROUTER_APP_NAME")
    
    # AWS Bedrock Configuration (Future)
    aws_bedrock_enabled: bool = Field(default=False, env="AWS_BEDROCK_ENABLED")
    aws_bedrock_region: str = Field(default="us-east-1", env="AWS_BEDROCK_REGION")
    aws_bedrock_default_model: str = Field(default="claude_3_haiku", env="AWS_BEDROCK_DEFAULT_MODEL")
    
    # Hong Kong Data Configuration
    hk_data_update_interval: int = Field(default=3600, env="HK_DATA_UPDATE_INTERVAL")  # 1 hour
    hk_data_cache_ttl: int = Field(default=1800, env="HK_DATA_CACHE_TTL")  # 30 minutes
    hk_data_retry_attempts: int = Field(default=3, env="HK_DATA_RETRY_ATTEMPTS")
    hk_data_timeout: int = Field(default=30, env="HK_DATA_TIMEOUT")
    
    # =============================================================================
    # FILE UPLOAD CONFIGURATION
    # =============================================================================
    
    upload_path: Path = Field(default=Path("./uploads"), env="UPLOAD_PATH")
    upload_max_size: int = Field(default=52428800, env="UPLOAD_MAX_SIZE")  # 50MB
    upload_allowed_extensions: List[str] = Field(
        default=[".pdf", ".jpg", ".jpeg", ".png", ".txt", ".doc", ".docx"],
        env="UPLOAD_ALLOWED_EXTENSIONS"
    )
    
    # File Processing
    enable_ocr: bool = Field(default=True, env="ENABLE_OCR")
    ocr_language: str = Field(default="eng+chi_tra", env="OCR_LANGUAGE")
    pdf_max_pages: int = Field(default=100, env="PDF_MAX_PAGES")
    
    # =============================================================================
    # AGENT SYSTEM CONFIGURATION
    # =============================================================================
    
    # Agent Configuration
    default_agent_timeout: int = Field(default=30, env="DEFAULT_AGENT_TIMEOUT")
    max_conversation_history: int = Field(default=50, env="MAX_CONVERSATION_HISTORY")
    agent_confidence_threshold: float = Field(default=0.6, env="AGENT_CONFIDENCE_THRESHOLD")
    
    # Agent Routing
    enable_intelligent_routing: bool = Field(default=True, env="ENABLE_INTELLIGENT_ROUTING")
    routing_model: str = Field(default="gpt-4-turbo-preview", env="ROUTING_MODEL")
    urgency_detection_threshold: float = Field(default=0.8, env="URGENCY_DETECTION_THRESHOLD")
    
    # Cultural Settings
    default_language: str = Field(default="en", env="DEFAULT_LANGUAGE")
    supported_languages: List[str] = Field(default=["en", "zh-HK", "zh-CN"], env="SUPPORTED_LANGUAGES")
    cultural_context: str = Field(default="hong_kong", env="CULTURAL_CONTEXT")
    
    # =============================================================================
    # LOGGING AND MONITORING CONFIGURATION
    # =============================================================================
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Path = Field(default=Path("./logs/healthcare_ai.log"), env="LOG_FILE")
    log_max_size: str = Field(default="100MB", env="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # Logging Categories
    log_database_queries: bool = Field(default=False, env="LOG_DATABASE_QUERIES")
    log_api_requests: bool = Field(default=True, env="LOG_API_REQUESTS")
    log_agent_interactions: bool = Field(default=True, env="LOG_AGENT_INTERACTIONS")
    log_security_events: bool = Field(default=True, env="LOG_SECURITY_EVENTS")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    enable_health_checks: bool = Field(default=True, env="ENABLE_HEALTH_CHECKS")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # Error Tracking
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    sentry_environment: str = Field(default="development", env="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=0.1, env="SENTRY_TRACES_SAMPLE_RATE")
    
    # =============================================================================
    # BACKGROUND TASKS CONFIGURATION
    # =============================================================================
    
    # Worker Configuration
    worker_concurrency: int = Field(default=4, env="WORKER_CONCURRENCY")
    worker_max_tasks_per_child: int = Field(default=1000, env="WORKER_MAX_TASKS_PER_CHILD")
    
    # Task Queues
    enable_background_tasks: bool = Field(default=True, env="ENABLE_BACKGROUND_TASKS")
    task_queue_url: Optional[str] = Field(default=None, env="TASK_QUEUE_URL")
    
    # Scheduled Tasks
    enable_data_sync: bool = Field(default=True, env="ENABLE_DATA_SYNC")
    data_sync_interval: int = Field(default=3600, env="DATA_SYNC_INTERVAL")  # 1 hour
    
    enable_learning_updates: bool = Field(default=True, env="ENABLE_LEARNING_UPDATES")
    learning_update_interval: int = Field(default=86400, env="LEARNING_UPDATE_INTERVAL")  # 24 hours
    
    enable_cleanup_tasks: bool = Field(default=True, env="ENABLE_CLEANUP_TASKS")
    cleanup_interval: int = Field(default=604800, env="CLEANUP_INTERVAL")  # 7 days
    
    # =============================================================================
    # SECURITY MONITORING CONFIGURATION
    # =============================================================================
    
    # Security Event Tracking
    enable_security_monitoring: bool = Field(default=True, env="ENABLE_SECURITY_MONITORING")
    security_alert_email: str = Field(default="security@healthcare-ai.com", env="SECURITY_ALERT_EMAIL")
    admin_emails: List[str] = Field(default=["admin@healthcare-ai.com"], env="ADMIN_EMAILS")
    
    # SMTP Configuration for Security Alerts
    smtp_server: str = Field(default="localhost", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    alert_from_email: str = Field(default="security@healthcare-ai.com", env="ALERT_FROM_EMAIL")
    
    # Slack Integration
    slack_webhook_url: str = Field(default="", env="SLACK_WEBHOOK_URL")
    slack_channel: str = Field(default="#security-alerts", env="SLACK_CHANNEL")
    
    # Webhook Alerts
    alert_webhook_urls: List[str] = Field(default=[], env="ALERT_WEBHOOK_URLS")
    
    # Security Thresholds
    failed_login_threshold: int = Field(default=5, env="FAILED_LOGIN_THRESHOLD")
    brute_force_threshold: int = Field(default=10, env="BRUTE_FORCE_THRESHOLD")
    rate_limit_violation_threshold: int = Field(default=10, env="RATE_LIMIT_VIOLATION_THRESHOLD")
    
    # IP Blocking
    auto_block_suspicious_ips: bool = Field(default=True, env="AUTO_BLOCK_SUSPICIOUS_IPS")
    default_ip_block_duration_minutes: int = Field(default=60, env="DEFAULT_IP_BLOCK_DURATION_MINUTES")
    
    # =============================================================================
    # DEVELOPMENT CONFIGURATION
    # =============================================================================
    
    # Development Tools
    enable_api_docs: bool = Field(default=True, env="ENABLE_API_DOCS")
    enable_admin_interface: bool = Field(default=True, env="ENABLE_ADMIN_INTERFACE")
    enable_debug_toolbar: bool = Field(default=False, env="ENABLE_DEBUG_TOOLBAR")
    
    # Testing
    test_database_url: Optional[str] = Field(default=None, env="TEST_DATABASE_URL")
    enable_test_data: bool = Field(default=False, env="ENABLE_TEST_DATA")
    
    # =============================================================================
    # VALIDATORS
    # =============================================================================
    
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: Optional[str]) -> str:
        """Use secret_key if jwt_secret_key is not provided"""
        if v is None:
            return ""  # Will be set in model_validator
        return v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of the allowed values"""
        allowed_environments = ["development", "staging", "production", "testing"]
        if v not in allowed_environments:
            raise ValueError(f"Environment must be one of: {allowed_environments}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v_upper
    
    @field_validator("upload_path", mode="before")
    @classmethod
    def validate_upload_path(cls, v: Union[str, Path]) -> Path:
        """Convert string to Path and ensure it's absolute"""
        path = Path(v) if isinstance(v, str) else v
        if not path.is_absolute():
            path = Path.cwd() / path
        return path
    
    @field_validator("log_file", mode="before")
    @classmethod
    def validate_log_file(cls, v: Union[str, Path]) -> Path:
        """Convert string to Path and ensure directory exists"""
        path = Path(v) if isinstance(v, str) else v
        if not path.is_absolute():
            path = Path.cwd() / path
        
        # Create log directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    @model_validator(mode="after")
    def validate_all_settings(self) -> "Settings":
        """Validate and auto-generate URLs and other settings"""
        # Set jwt_secret_key if not provided
        if not self.jwt_secret_key:
            self.jwt_secret_key = self.secret_key
        
        # Auto-generate database URLs if not provided
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.database_user}:"
                f"{self.database_password}@{self.database_host}:"
                f"{self.database_port}/{self.database_name}"
            )
        
        if not self.database_sync_url:
            self.database_sync_url = (
                f"postgresql://{self.database_user}:"
                f"{self.database_password}@{self.database_host}:"
                f"{self.database_port}/{self.database_name}"
            )
        
        # Auto-generate Redis URL if not provided
        if not self.redis_url:
            password_part = ""
            if self.redis_password:
                password_part = f":{self.redis_password}@"
            
            self.redis_url = (
                f"redis://{password_part}{self.redis_host}:"
                f"{self.redis_port}/{self.redis_db}"
            )
        
        # Auto-generate task queue URL if not provided
        if not self.task_queue_url and self.enable_background_tasks:
            password_part = ""
            if self.redis_password:
                password_part = f":{self.redis_password}@"
            
            self.task_queue_url = (
                f"redis://{password_part}{self.redis_host}:"
                f"{self.redis_port}/1"  # Different DB for task queue
            )
        
        return self
    
    # =============================================================================
    # PROPERTIES
    # =============================================================================
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.environment == "testing"
    
    @property
    def database_url_str(self) -> str:
        """Get database URL as string"""
        return str(self.database_url) if self.database_url else ""
    
    @property
    def database_sync_url_str(self) -> str:
        """Get synchronous database URL as string"""
        return str(self.database_sync_url) if self.database_sync_url else ""
    
    @property
    def redis_url_str(self) -> str:
        """Get Redis URL as string"""
        return str(self.redis_url) if self.redis_url else ""
    
    # =============================================================================
    # CONFIGURATION
    # =============================================================================
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from environment


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Uses lru_cache to avoid re-reading environment variables on every call
    """
    return Settings()


# Global settings instance
settings = get_settings()


def reload_settings() -> Settings:
    """
    Reload settings (useful for testing or configuration changes)
    """
    get_settings.cache_clear()
    return get_settings()


# Environment-specific settings
class DevelopmentSettings(Settings):
    """Development-specific settings"""
    debug: bool = True
    log_level: str = "DEBUG"
    enable_api_docs: bool = True
    log_database_queries: bool = True


class ProductionSettings(Settings):
    """Production-specific settings"""
    debug: bool = False
    log_level: str = "WARNING"
    enable_api_docs: bool = False
    enable_debug_toolbar: bool = False
    log_database_queries: bool = False


class TestingSettings(Settings):
    """Testing-specific settings"""
    environment: str = "testing"
    debug: bool = True
    log_level: str = "DEBUG"
    enable_test_data: bool = True
    
    class Config:
        env_file = ".env.test"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


def get_environment_settings() -> Settings:
    """Get environment-specific settings"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()
