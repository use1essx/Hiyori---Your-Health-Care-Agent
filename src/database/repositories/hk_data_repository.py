#!/usr/bin/env python3
"""
Hong Kong Healthcare Data Repository
Database operations for real-time HK government data
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc, func, text, select
from sqlalchemy.exc import SQLAlchemyError

from ..models_hk_data import (
    HKHealthcareFacility, HKHealthcareUpdate, HKHealthAlert, 
    HKDataSnapshot, HKDataSourceStatus, HKDataRecord, HKDataSummary,
    UpdateType, DataSourceType
)


class HKDataRepository:
    """Repository for Hong Kong healthcare data operations"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.logger = logging.getLogger(__name__)
        self.is_async = isinstance(db_session, AsyncSession)
    
    # ==================================================================
    # FACILITY OPERATIONS
    # ==================================================================
    
    async def create_or_update_facility(self, facility_data: Dict[str, Any]) -> HKHealthcareFacility:
        """Create or update a healthcare facility"""
        try:
            facility_id = facility_data.get("facility_id")
            
            # Check if facility exists
            facility = self.db.query(HKHealthcareFacility).filter(
                HKHealthcareFacility.facility_id == facility_id
            ).first()
            
            if facility:
                # Update existing facility
                for key, value in facility_data.items():
                    if hasattr(facility, key):
                        setattr(facility, key, value)
                facility.updated_at = datetime.now(timezone.utc)
                self.logger.info(f"Updated facility: {facility_id}")
            else:
                # Create new facility
                facility = HKHealthcareFacility(**facility_data)
                self.db.add(facility)
                self.logger.info(f"Created new facility: {facility_id}")
            
            if self.is_async:
                await self.db.commit()
            else:
                self.db.commit()
            return facility
            
        except SQLAlchemyError as e:
            if self.is_async:
                await self.db.rollback()
            else:
                self.db.rollback()
            self.logger.error(f"Error creating/updating facility {facility_id}: {e}")
            raise
    
    def get_facility_by_id(self, facility_id: str) -> Optional[HKHealthcareFacility]:
        """Get facility by ID"""
        return self.db.query(HKHealthcareFacility).filter(
            HKHealthcareFacility.facility_id == facility_id
        ).first()
    
    def get_facilities_by_type(self, facility_type: str, emergency_only: bool = False) -> List[HKHealthcareFacility]:
        """Get facilities by type"""
        query = self.db.query(HKHealthcareFacility).filter(
            HKHealthcareFacility.facility_type == facility_type,
            HKHealthcareFacility.is_active == True
        )
        
        if emergency_only:
            query = query.filter(HKHealthcareFacility.emergency_services == True)
        
        return query.all()
    
    def get_facilities_by_region(self, region: str, district: str = None) -> List[HKHealthcareFacility]:
        """Get facilities by geographic region"""
        query = self.db.query(HKHealthcareFacility).filter(
            HKHealthcareFacility.region == region,
            HKHealthcareFacility.is_active == True
        )
        
        if district:
            query = query.filter(HKHealthcareFacility.district == district)
        
        return query.all()
    
    # ==================================================================
    # REAL-TIME DATA UPDATES
    # ==================================================================
    
    async def store_data_update(self, update_data: HKDataRecord) -> HKHealthcareUpdate:
        """Store a real-time data update"""
        try:
            # Find or create facility
            facility = None
            if update_data.facility_id:
                facility = self.get_facility_by_id(update_data.facility_id)
            
            # Create update record
            update = HKHealthcareUpdate(
                facility_id=facility.id if facility else None,
                update_type=update_data.update_type,
                field_name=update_data.source_name,
                new_value=json.dumps(update_data.data),
                value_type='json',
                data_source=update_data.source_name,
                source_timestamp=update_data.timestamp,
                confidence_score=update_data.confidence_score,
                created_at=datetime.now(timezone.utc)
            )
            
            self.db.add(update)
            self.db.commit()
            
            self.logger.info(f"Stored data update from {update_data.source_name}")
            return update
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Error storing data update: {e}")
            raise
    
    def get_recent_updates(self, hours: int = 24, source_name: str = None) -> List[HKHealthcareUpdate]:
        """Get recent data updates"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = self.db.query(HKHealthcareUpdate).filter(
            HKHealthcareUpdate.created_at >= cutoff_time
        ).order_by(desc(HKHealthcareUpdate.created_at))
        
        if source_name:
            query = query.filter(HKHealthcareUpdate.data_source == source_name)
        
        return query.all()
    
    def get_facility_updates(self, facility_id: str, hours: int = 24) -> List[HKHealthcareUpdate]:
        """Get updates for a specific facility"""
        facility = self.get_facility_by_id(facility_id)
        if not facility:
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return self.db.query(HKHealthcareUpdate).filter(
            and_(
                HKHealthcareUpdate.facility_id == facility.id,
                HKHealthcareUpdate.created_at >= cutoff_time
            )
        ).order_by(desc(HKHealthcareUpdate.created_at)).all()
    
    # ==================================================================
    # HEALTH ALERTS
    # ==================================================================
    
    async def create_health_alert(self, alert_data: Dict[str, Any]) -> HKHealthAlert:
        """Create a health alert"""
        try:
            alert = HKHealthAlert(**alert_data)
            self.db.add(alert)
            self.db.commit()
            
            self.logger.info(f"Created health alert: {alert.alert_id}")
            return alert
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Error creating health alert: {e}")
            raise
    
    def get_active_alerts(self, severity: str = None) -> List[HKHealthAlert]:
        """Get active health alerts"""
        query = self.db.query(HKHealthAlert).filter(
            HKHealthAlert.is_active == True
        ).order_by(desc(HKHealthAlert.issued_at))
        
        if severity:
            query = query.filter(HKHealthAlert.severity == severity)
        
        return query.all()
    
    def get_alerts_by_region(self, region: str) -> List[HKHealthAlert]:
        """Get alerts affecting a specific region"""
        return self.db.query(HKHealthAlert).filter(
            and_(
                HKHealthAlert.is_active == True,
                HKHealthAlert.affected_regions.contains([region])
            )
        ).order_by(desc(HKHealthAlert.issued_at)).all()
    
    # ==================================================================
    # DATA SNAPSHOTS
    # ==================================================================
    
    async def create_data_snapshot(self, data: Dict[str, Any], snapshot_type: str = 'hourly') -> HKDataSnapshot:
        """Create a complete data snapshot"""
        try:
            # Calculate metrics
            total_facilities = len(data.get('facilities', []))
            active_alerts = len(data.get('alerts', []))
            quality_score = data.get('summary', {}).get('data_quality_score', 0.0)
            emergency_status = data.get('system_status', 'unknown')
            
            snapshot = HKDataSnapshot(
                snapshot_type=snapshot_type,
                complete_data=data,
                data_sources=data.get('data_sources', []),
                data_quality_score=quality_score,
                total_facilities=total_facilities,
                active_alerts=active_alerts,
                emergency_status=emergency_status,
                created_at=datetime.now(timezone.utc)
            )
            
            self.db.add(snapshot)
            self.db.commit()
            
            self.logger.info(f"Created {snapshot_type} data snapshot")
            return snapshot
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Error creating data snapshot: {e}")
            raise
    
    def get_latest_snapshot(self, snapshot_type: str = None) -> Optional[HKDataSnapshot]:
        """Get the latest data snapshot"""
        query = self.db.query(HKDataSnapshot).order_by(desc(HKDataSnapshot.created_at))
        
        if snapshot_type:
            query = query.filter(HKDataSnapshot.snapshot_type == snapshot_type)
        
        return query.first()
    
    def get_snapshots_for_period(self, hours: int = 24) -> List[HKDataSnapshot]:
        """Get snapshots for a time period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return self.db.query(HKDataSnapshot).filter(
            HKDataSnapshot.created_at >= cutoff_time
        ).order_by(desc(HKDataSnapshot.created_at)).all()
    
    # ==================================================================
    # DATA SOURCE STATUS MONITORING
    # ==================================================================
    
    async def update_source_status(self, source_name: str, is_success: bool, 
                                 response_time_ms: int = None, error: str = None) -> HKDataSourceStatus:
        """Update the status of a data source"""
        try:
            # Get or create source status
            status = self.db.query(HKDataSourceStatus).filter(
                HKDataSourceStatus.source_name == source_name
            ).first()
            
            if not status:
                status = HKDataSourceStatus(
                    source_name=source_name,
                    source_type='hk_government',
                    created_at=datetime.now(timezone.utc)
                )
                self.db.add(status)
            
            # Update status
            current_time = datetime.now(timezone.utc)
            
            if is_success:
                status.last_success_at = current_time
                status.consecutive_failures = 0
                status.success_count_24h += 1
                if response_time_ms:
                    # Update average response time (simple moving average)
                    if status.avg_response_time_ms:
                        status.avg_response_time_ms = int((status.avg_response_time_ms + response_time_ms) / 2)
                    else:
                        status.avg_response_time_ms = response_time_ms
            else:
                status.last_failure_at = current_time
                status.consecutive_failures += 1
                status.failure_count_24h += 1
                if error:
                    status.last_error = error[:1000]  # Truncate long errors
            
            # Update health status
            if status.consecutive_failures == 0:
                status.health_status = 'healthy'
            elif status.consecutive_failures < 3:
                status.health_status = 'degraded'
            else:
                status.health_status = 'unhealthy'
            
            # Calculate uptime percentage
            total_attempts = status.success_count_24h + status.failure_count_24h
            if total_attempts > 0:
                status.uptime_percentage = (status.success_count_24h / total_attempts) * 100
            
            status.updated_at = current_time
            self.db.commit()
            
            return status
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Error updating source status {source_name}: {e}")
            raise
    
    def get_all_source_status(self) -> List[HKDataSourceStatus]:
        """Get status of all data sources"""
        return self.db.query(HKDataSourceStatus).order_by(
            desc(HKDataSourceStatus.last_success_at)
        ).all()
    
    def get_unhealthy_sources(self) -> List[HKDataSourceStatus]:
        """Get sources that are currently unhealthy"""
        return self.db.query(HKDataSourceStatus).filter(
            HKDataSourceStatus.health_status.in_(['degraded', 'unhealthy'])
        ).all()
    
    # ==================================================================
    # ANALYTICS AND REPORTING
    # ==================================================================
    
    def get_data_summary(self) -> HKDataSummary:
        """Get comprehensive data summary"""
        try:
            # Count facilities
            total_facilities = self.db.query(func.count(HKHealthcareFacility.id)).filter(
                HKHealthcareFacility.is_active == True
            ).scalar()
            
            # Count active alerts
            active_alerts = self.db.query(func.count(HKHealthAlert.id)).filter(
                HKHealthAlert.is_active == True
            ).scalar()
            
            # Get latest snapshot for data quality
            latest_snapshot = self.get_latest_snapshot()
            data_quality_score = latest_snapshot.data_quality_score if latest_snapshot else 0.0
            emergency_status = latest_snapshot.emergency_status if latest_snapshot else 'unknown'
            last_updated = latest_snapshot.created_at if latest_snapshot else datetime.now(timezone.utc)
            
            # Count healthy sources
            healthy_sources = self.db.query(func.count(HKDataSourceStatus.id)).filter(
                HKDataSourceStatus.health_status == 'healthy'
            ).scalar()
            
            # Performance metrics
            avg_response_time = self.db.query(func.avg(HKDataSourceStatus.avg_response_time_ms)).scalar()
            avg_uptime = self.db.query(func.avg(HKDataSourceStatus.uptime_percentage)).scalar()
            
            return HKDataSummary(
                total_facilities=total_facilities or 0,
                active_alerts=active_alerts or 0,
                data_quality_score=float(data_quality_score or 0.0),
                last_updated=last_updated,
                emergency_status=emergency_status,
                real_time_sources=healthy_sources or 0,
                performance_metrics={
                    'avg_response_time_ms': int(avg_response_time or 0),
                    'avg_uptime_percentage': float(avg_uptime or 0.0)
                }
            )
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error generating data summary: {e}")
            # Return empty summary on error
            return HKDataSummary(
                total_facilities=0,
                active_alerts=0,
                data_quality_score=0.0,
                last_updated=datetime.now(timezone.utc),
                emergency_status='unknown',
                real_time_sources=0,
                performance_metrics={}
            )
    
    def get_facility_statistics(self) -> Dict[str, Any]:
        """Get comprehensive facility statistics"""
        try:
            # Facility type breakdown
            type_counts = dict(
                self.db.query(
                    HKHealthcareFacility.facility_type, 
                    func.count(HKHealthcareFacility.id)
                ).filter(
                    HKHealthcareFacility.is_active == True
                ).group_by(HKHealthcareFacility.facility_type).all()
            )
            
            # Regional breakdown
            region_counts = dict(
                self.db.query(
                    HKHealthcareFacility.region,
                    func.count(HKHealthcareFacility.id)
                ).filter(
                    HKHealthcareFacility.is_active == True
                ).group_by(HKHealthcareFacility.region).all()
            )
            
            # Emergency services count
            emergency_count = self.db.query(func.count(HKHealthcareFacility.id)).filter(
                and_(
                    HKHealthcareFacility.is_active == True,
                    HKHealthcareFacility.emergency_services == True
                )
            ).scalar()
            
            return {
                'by_type': type_counts,
                'by_region': region_counts,
                'emergency_services': emergency_count,
                'total_active': sum(type_counts.values())
            }
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error generating facility statistics: {e}")
            return {}
    
    # ==================================================================
    # MAINTENANCE AND CLEANUP
    # ==================================================================
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old data records"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Clean old updates
            old_updates = self.db.query(HKHealthcareUpdate).filter(
                HKHealthcareUpdate.created_at < cutoff_date
            ).count()
            
            self.db.query(HKHealthcareUpdate).filter(
                HKHealthcareUpdate.created_at < cutoff_date
            ).delete()
            
            # Clean old snapshots (keep daily ones longer)
            old_snapshots = self.db.query(HKDataSnapshot).filter(
                and_(
                    HKDataSnapshot.created_at < cutoff_date,
                    HKDataSnapshot.snapshot_type == 'hourly'
                )
            ).count()
            
            self.db.query(HKDataSnapshot).filter(
                and_(
                    HKDataSnapshot.created_at < cutoff_date,
                    HKDataSnapshot.snapshot_type == 'hourly'
                )
            ).delete()
            
            # Clean expired alerts
            expired_alerts = self.db.query(HKHealthAlert).filter(
                and_(
                    HKHealthAlert.expires_at < datetime.now(timezone.utc),
                    HKHealthAlert.is_active == True
                )
            ).count()
            
            self.db.query(HKHealthAlert).filter(
                and_(
                    HKHealthAlert.expires_at < datetime.now(timezone.utc),
                    HKHealthAlert.is_active == True
                )
            ).update({'is_active': False})
            
            self.db.commit()
            
            return {
                'updates_deleted': old_updates,
                'snapshots_deleted': old_snapshots,
                'alerts_expired': expired_alerts
            }
            
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Error during data cleanup: {e}")
            raise
