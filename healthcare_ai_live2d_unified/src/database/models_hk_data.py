#!/usr/bin/env python3
"""
Hong Kong Healthcare Data Models
Database models for real-time HK government data integration
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    Numeric, JSON, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

Base = declarative_base()


class UpdateType(Enum):
    """Types of healthcare data updates"""
    WAITING_TIME = "waiting_time"
    CAPACITY = "capacity"
    STATUS = "status"
    SERVICES = "services"
    EMERGENCY = "emergency"
    ENVIRONMENTAL = "environmental"
    ALERT = "alert"


class DataSourceType(Enum):
    """Types of data sources"""
    HOSPITAL_AUTHORITY = "hospital_authority"
    HK_OBSERVATORY = "hk_observatory"
    DEPARTMENT_HEALTH = "department_health"
    EMERGENCY_SERVICES = "emergency_services"
    TRANSPORT = "transport"
    ENVIRONMENTAL = "environmental"


class HKHealthcareFacility(Base):
    """Hong Kong healthcare facilities model"""
    __tablename__ = "hk_healthcare_facilities"
    
    id = Column(Integer, primary_key=True)
    
    # Facility Identification
    facility_id = Column(String(50), unique=True, nullable=False, index=True)
    facility_code = Column(String(20))
    
    # Names (Multi-language support)
    name_en = Column(String(255), nullable=False)
    name_zh_hant = Column(String(255))  # Traditional Chinese
    name_zh_hans = Column(String(255))  # Simplified Chinese
    
    # Facility Type and Classification
    facility_type = Column(String(50), nullable=False, index=True)
    facility_subtype = Column(String(100))
    cluster = Column(String(50))  # HA cluster
    
    # Services Offered
    services_offered = Column(ARRAY(String))
    specialties = Column(ARRAY(String))
    emergency_services = Column(Boolean, default=False, index=True)
    a_e_services = Column(Boolean, default=False)
    
    # Location Information
    address_en = Column(Text)
    address_zh = Column(Text)
    district = Column(String(50), index=True)
    region = Column(String(20), index=True)
    
    # Geographic Coordinates
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    
    # Contact Information
    phone_main = Column(String(20))
    phone_appointment = Column(String(20))
    phone_emergency = Column(String(20))
    fax = Column(String(20))
    email = Column(String(255))
    website = Column(String(500))
    
    # Operating Information
    operating_hours = Column(JSON)
    capacity_info = Column(JSON)
    waiting_time_info = Column(JSON)
    
    # Status and Metadata
    is_active = Column(Boolean, default=True, index=True)
    data_quality_score = Column(Numeric(3, 2), default=1.0)
    last_data_update = Column(DateTime(timezone=True))
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    updated_by = Column(Integer)  # Will be FK to users table
    
    # Relationships
    updates = relationship("HKHealthcareUpdate", back_populates="facility", cascade="all, delete-orphan")
    alerts = relationship("HKHealthAlert", back_populates="facility")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("facility_type IN ('hospital', 'clinic', 'health_center', 'emergency', 'specialist', 'dental', 'mental_health')", name='check_facility_type'),
        CheckConstraint("region IN ('Hong Kong Island', 'Kowloon', 'New Territories')", name='check_region'),
        Index('idx_facility_location', 'latitude', 'longitude'),
        Index('idx_facility_services', 'services_offered', postgresql_using='gin'),
    )


class HKHealthcareUpdate(Base):
    """Real-time healthcare data updates"""
    __tablename__ = "hk_healthcare_updates"
    
    id = Column(Integer, primary_key=True)
    facility_id = Column(Integer, ForeignKey('hk_healthcare_facilities.id', ondelete='CASCADE'), index=True)
    
    # Update Information
    update_type = Column(String(50), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    
    # Data Values
    old_value = Column(Text)
    new_value = Column(Text)
    value_type = Column(String(20), default='string')
    
    # Source Information
    data_source = Column(String(100), nullable=False, index=True)
    source_timestamp = Column(DateTime(timezone=True))
    confidence_score = Column(Numeric(3, 2), default=1.0)
    
    # Validation
    is_validated = Column(Boolean, default=False, index=True)
    validation_method = Column(String(100))
    validation_score = Column(Numeric(3, 2))
    
    # Processing
    processed = Column(Boolean, default=False, index=True)
    processing_error = Column(Text)
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    facility = relationship("HKHealthcareFacility", back_populates="updates")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("value_type IN ('string', 'integer', 'decimal', 'boolean', 'json')", name='check_value_type'),
        Index('idx_update_source_time', 'data_source', 'source_timestamp'),
    )


class HKHealthAlert(Base):
    """Hong Kong health alerts and notifications"""
    __tablename__ = "hk_health_alerts"
    
    id = Column(Integer, primary_key=True)
    
    # Alert Identification
    alert_id = Column(String(100), unique=True, index=True)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    
    # Content
    title_en = Column(String(500), nullable=False)
    title_zh = Column(String(500))
    description_en = Column(Text)
    description_zh = Column(Text)
    
    # Source and Timing
    source_authority = Column(String(100), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True))
    
    # Geographic Scope
    affected_regions = Column(ARRAY(String))
    affected_districts = Column(ARRAY(String))
    facility_id = Column(Integer, ForeignKey('hk_healthcare_facilities.id'), nullable=True)
    
    # Alert Data
    alert_data = Column(JSON)
    action_required = Column(Text)
    contact_info = Column(JSON)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    acknowledgments = Column(Integer, default=0)
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    facility = relationship("HKHealthcareFacility", back_populates="alerts")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("alert_type IN ('weather', 'emergency', 'capacity', 'service', 'health_advisory', 'system')", name='check_alert_type'),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='check_severity'),
        Index('idx_alert_active_severity', 'is_active', 'severity'),
    )


class HKDataSnapshot(Base):
    """Periodic snapshots of complete HK healthcare data"""
    __tablename__ = "hk_data_snapshots"
    
    id = Column(Integer, primary_key=True)
    
    # Snapshot Information
    snapshot_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    snapshot_type = Column(String(50), nullable=False)  # 'hourly', 'daily', 'emergency'
    
    # Data Content
    complete_data = Column(JSON, nullable=False)
    data_sources = Column(JSON)  # List of included data sources
    
    # Quality Metrics
    data_quality_score = Column(Numeric(3, 2))
    total_facilities = Column(Integer)
    active_alerts = Column(Integer)
    emergency_status = Column(String(20))
    
    # Performance Metrics
    fetch_time_ms = Column(Integer)
    processing_time_ms = Column(Integer)
    success_rate = Column(Numeric(5, 2))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    created_by = Column(String(100))  # System user or process
    
    # Constraints
    __table_args__ = (
        CheckConstraint("snapshot_type IN ('hourly', 'daily', 'emergency', 'manual')", name='check_snapshot_type'),
        Index('idx_snapshot_type_created', 'snapshot_type', 'created_at'),
    )


class HKDataSourceStatus(Base):
    """Status tracking for individual HK data sources"""
    __tablename__ = "hk_data_source_status"
    
    id = Column(Integer, primary_key=True)
    
    # Source Information
    source_name = Column(String(100), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    source_url = Column(String(500))
    
    # Status Information
    is_active = Column(Boolean, default=True, index=True)
    last_success_at = Column(DateTime(timezone=True), index=True)
    last_failure_at = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, default=0)
    
    # Performance Metrics
    success_count_24h = Column(Integer, default=0)
    failure_count_24h = Column(Integer, default=0)
    avg_response_time_ms = Column(Integer)
    
    # Health Information
    health_status = Column(String(20), default='unknown')
    last_error = Column(Text)
    uptime_percentage = Column(Numeric(5, 2))
    
    # Configuration
    check_interval_minutes = Column(Integer, default=15)
    timeout_seconds = Column(Integer, default=30)
    retry_count = Column(Integer, default=3)
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Constraints
    __table_args__ = (
        CheckConstraint("health_status IN ('healthy', 'degraded', 'unhealthy', 'unknown')", name='check_health_status'),
        Index('idx_source_status_health', 'source_name', 'health_status'),
    )


# Utility Models for Integration
@dataclass
class HKDataRecord:
    """Data transfer object for HK healthcare data"""
    source_name: str
    facility_id: Optional[str]
    update_type: str
    data: Dict[str, Any]
    timestamp: datetime
    confidence_score: float = 1.0
    quality_score: float = 1.0


@dataclass 
class HKDataSummary:
    """Summary of HK healthcare data for API responses"""
    total_facilities: int
    active_alerts: int
    data_quality_score: float
    last_updated: datetime
    emergency_status: str
    real_time_sources: int
    performance_metrics: Dict[str, Any]

