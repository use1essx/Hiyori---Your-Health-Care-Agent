"""
Healthcare AI V2 - Health Profile Models
Extended user profile models for health-focused personalization
"""

from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Date,
    Float,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database.connection import Base
from src.database.models_comprehensive import TimestampMixin, User


class GenderEnum(str, Enum):
    """Gender options"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class BloodTypeEnum(str, Enum):
    """Blood type options"""
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"
    UNKNOWN = "unknown"


class HealthProfile(Base, TimestampMixin):
    """Extended health profile for users"""
    
    __tablename__ = "health_profiles"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Basic health information
    date_of_birth = Column(Date)
    gender = Column(SQLEnum(GenderEnum))
    height_cm = Column(Float)  # Height in centimeters
    weight_kg = Column(Float)  # Weight in kilograms
    blood_type = Column(SQLEnum(BloodTypeEnum))
    
    # Health conditions and allergies
    chronic_conditions = Column(JSONB)  # List of chronic conditions
    allergies = Column(JSONB)  # List of allergies and sensitivities
    current_medications = Column(JSONB)  # Current medications with dosages
    past_surgeries = Column(JSONB)  # Past surgical procedures
    family_medical_history = Column(JSONB)  # Family medical history
    
    # Lifestyle factors
    smoking_status = Column(String(50))  # never, former, current
    alcohol_consumption = Column(String(50))  # none, occasional, moderate, heavy
    exercise_frequency = Column(String(50))  # sedentary, light, moderate, active, very_active
    diet_type = Column(String(50))  # omnivore, vegetarian, vegan, other
    sleep_hours_avg = Column(Float)  # Average sleep hours per night
    
    # Emergency contacts
    emergency_contact_name = Column(String(255))
    emergency_contact_phone = Column(String(50))
    emergency_contact_relationship = Column(String(100))
    
    # Healthcare preferences
    preferred_language = Column(String(10), default="en")  # en, zh-HK, zh-CN
    preferred_hospital = Column(String(255))  # Preferred hospital in Hong Kong
    preferred_doctor = Column(String(255))  # Preferred doctor/clinic
    insurance_provider = Column(String(255))  # Health insurance provider
    insurance_number = Column(String(100))  # Insurance policy number
    
    # Health goals and preferences
    health_goals = Column(JSONB)  # Personal health goals
    notification_preferences = Column(JSONB)  # How user wants to receive health reminders
    privacy_level = Column(String(50), default="standard")  # minimal, standard, comprehensive
    
    # AI personalization preferences
    preferred_agent_types = Column(JSONB)  # Preferred AI agent types
    interaction_style = Column(String(50), default="professional")  # casual, professional, caring
    urgency_sensitivity = Column(String(50), default="normal")  # low, normal, high
    
    # Relationships
    user = relationship("User", back_populates="health_profile")
    health_metrics = relationship("HealthMetric", back_populates="health_profile", cascade="all, delete-orphan")
    medication_schedules = relationship("MedicationSchedule", back_populates="health_profile", cascade="all, delete-orphan")
    health_goals_tracking = relationship("HealthGoal", back_populates="health_profile", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<HealthProfile(user_id={self.user_id}, age={self.get_age()})>"
    
    def get_age(self) -> Optional[int]:
        """Calculate age from date of birth"""
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def get_bmi(self) -> Optional[float]:
        """Calculate BMI from height and weight"""
        if not self.height_cm or not self.weight_kg:
            return None
        height_m = self.height_cm / 100
        return round(self.weight_kg / (height_m ** 2), 1)


class HealthMetric(Base, TimestampMixin):
    """Health metrics tracking (vital signs, measurements)"""
    
    __tablename__ = "health_metrics"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    health_profile_id = Column(Integer, ForeignKey("health_profiles.id"), nullable=False)
    
    # Metric information
    metric_type = Column(String(100), nullable=False, index=True)  # blood_pressure, heart_rate, weight, etc.
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # mmHg, bpm, kg, etc.
    
    # Additional data for complex metrics
    systolic = Column(Float)  # For blood pressure
    diastolic = Column(Float)  # For blood pressure
    notes = Column(Text)
    
    # Recording context
    recorded_at = Column(DateTime(timezone=True), default=func.now())
    recorded_by = Column(String(50), default="user")  # user, device, healthcare_provider
    device_info = Column(JSONB)  # Information about measuring device
    
    # Validation and quality
    is_validated = Column(Boolean, default=False)
    validation_source = Column(String(100))  # healthcare_provider, automatic, etc.
    
    # Relationships
    health_profile = relationship("HealthProfile", back_populates="health_metrics")
    
    def __repr__(self):
        return f"<HealthMetric(type='{self.metric_type}', value={self.value}, date='{self.recorded_at}')>"


class MedicationSchedule(Base, TimestampMixin):
    """Medication scheduling and reminders"""
    
    __tablename__ = "medication_schedules"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    health_profile_id = Column(Integer, ForeignKey("health_profiles.id"), nullable=False)
    
    # Medication information
    medication_name = Column(String(255), nullable=False)
    dosage = Column(String(100), nullable=False)  # e.g., "10mg", "1 tablet"
    frequency = Column(String(100), nullable=False)  # e.g., "twice daily", "as needed"
    route = Column(String(50))  # oral, topical, injection, etc.
    
    # Schedule information
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # Optional end date
    times_per_day = Column(Integer, default=1)
    specific_times = Column(JSONB)  # Specific times like ["08:00", "20:00"]
    
    # Instructions and notes
    instructions = Column(Text)  # Special instructions
    side_effects = Column(Text)  # Known side effects to monitor
    prescribing_doctor = Column(String(255))
    pharmacy = Column(String(255))
    
    # Reminder settings
    reminder_enabled = Column(Boolean, default=True)
    reminder_advance_minutes = Column(Integer, default=15)  # Remind 15 minutes before
    
    # Status
    is_active = Column(Boolean, default=True)
    is_critical = Column(Boolean, default=False)  # Critical medications
    
    # Relationships
    health_profile = relationship("HealthProfile", back_populates="medication_schedules")
    medication_logs = relationship("MedicationLog", back_populates="medication_schedule", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MedicationSchedule(medication='{self.medication_name}', dosage='{self.dosage}')>"


class MedicationLog(Base, TimestampMixin):
    """Log of medication taken/missed"""
    
    __tablename__ = "medication_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    medication_schedule_id = Column(Integer, ForeignKey("medication_schedules.id"), nullable=False)
    
    # Log information
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    actual_time = Column(DateTime(timezone=True))
    status = Column(String(50), nullable=False)  # taken, missed, skipped, delayed
    
    # Additional information
    notes = Column(Text)
    side_effects_experienced = Column(Text)
    effectiveness_rating = Column(Integer)  # 1-5 scale
    
    # Relationships
    medication_schedule = relationship("MedicationSchedule", back_populates="medication_logs")
    
    def __repr__(self):
        return f"<MedicationLog(id={self.id}, status='{self.status}', time='{self.scheduled_time}')>"


class HealthGoal(Base, TimestampMixin):
    """Health goals and progress tracking"""
    
    __tablename__ = "health_goals"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    health_profile_id = Column(Integer, ForeignKey("health_profiles.id"), nullable=False)
    
    # Goal information
    goal_type = Column(String(100), nullable=False, index=True)  # weight_loss, exercise, quit_smoking, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Target and tracking
    target_value = Column(Float)
    current_value = Column(Float)
    unit = Column(String(20))
    target_date = Column(Date)
    
    # Status and progress
    status = Column(String(50), default="active")  # active, completed, paused, cancelled
    progress_percentage = Column(Float, default=0.0)
    
    # Milestones and rewards
    milestones = Column(JSONB)  # Progress milestones
    rewards = Column(JSONB)  # Rewards for achieving milestones
    
    # AI coaching preferences
    coaching_enabled = Column(Boolean, default=True)
    reminder_frequency = Column(String(50), default="weekly")  # daily, weekly, monthly
    motivation_style = Column(String(50), default="encouraging")  # gentle, encouraging, challenging
    
    # Relationships
    health_profile = relationship("HealthProfile", back_populates="health_goals_tracking")
    goal_logs = relationship("HealthGoalLog", back_populates="health_goal", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<HealthGoal(title='{self.title}', progress={self.progress_percentage}%)>"


class HealthGoalLog(Base, TimestampMixin):
    """Daily/weekly progress logs for health goals"""
    
    __tablename__ = "health_goal_logs"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    health_goal_id = Column(Integer, ForeignKey("health_goals.id"), nullable=False)
    
    # Progress information
    log_date = Column(Date, nullable=False)
    value = Column(Float)
    notes = Column(Text)
    mood = Column(String(50))  # excellent, good, okay, difficult, struggling
    
    # Achievements and challenges
    achievements = Column(JSONB)  # Daily achievements
    challenges = Column(JSONB)  # Challenges faced
    
    # AI coach interaction
    ai_feedback = Column(Text)  # AI coach feedback
    user_feedback = Column(Text)  # User feedback to AI
    motivation_needed = Column(Boolean, default=False)
    
    # Relationships
    health_goal = relationship("HealthGoal", back_populates="goal_logs")
    
    def __repr__(self):
        return f"<HealthGoalLog(goal_id={self.health_goal_id}, date='{self.log_date}', value={self.value})>"


class ConversationContext(Base, TimestampMixin):
    """Enhanced conversation context for personalized responses"""
    
    __tablename__ = "conversation_contexts"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    
    # Context information
    health_concerns = Column(JSONB)  # Extracted health concerns
    mentioned_conditions = Column(JSONB)  # Medical conditions mentioned
    mentioned_medications = Column(JSONB)  # Medications mentioned
    mentioned_symptoms = Column(JSONB)  # Symptoms mentioned
    
    # User state and mood
    emotional_state = Column(String(50))  # anxious, worried, calm, stressed, etc.
    urgency_indicators = Column(JSONB)  # Indicators of urgency
    follow_up_needed = Column(Boolean, default=False)
    follow_up_timeframe = Column(String(50))  # immediate, hours, days, weeks
    
    # Personalization context
    preferred_agent_this_session = Column(String(50))
    communication_style_preference = Column(String(50))
    cultural_context_used = Column(JSONB)  # Cultural elements used in response
    
    # AI coaching context
    goals_referenced = Column(JSONB)  # Health goals referenced in conversation
    medications_referenced = Column(JSONB)  # Medications discussed
    recommendations_given = Column(JSONB)  # Recommendations provided
    
    # Relationships
    user = relationship("User")
    conversation = relationship("Conversation")
    
    def __repr__(self):
        return f"<ConversationContext(user_id={self.user_id}, conversation_id={self.conversation_id})>"


# Update User model to include health profile relationship
# This would be added to the User model in models.py
def update_user_model():
    """
    Add this relationship to the User model in models.py:
    health_profile = relationship("HealthProfile", back_populates="user", uselist=False)
    """
    pass


# Export all models
__all__ = [
    "HealthProfile",
    "HealthMetric", 
    "MedicationSchedule",
    "MedicationLog",
    "HealthGoal",
    "HealthGoalLog",
    "ConversationContext",
    "GenderEnum",
    "BloodTypeEnum",
]
