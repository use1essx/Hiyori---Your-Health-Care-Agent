"""
Hong Kong Healthcare Data API endpoints
Provides access to real-time HK government healthcare data for frontend consumption
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from enum import Enum

from src.data.storage.hk_data_repository import get_hk_data_repository, HKDataRepository
from src.data.storage.cache_manager import get_cache_manager, HKDataCacheManager
from src.data.pipeline import get_pipeline_orchestrator, HKDataPipelineOrchestrator
from src.core.logging import get_logger, log_api_request
from src.core.exceptions import NotFoundError, DatabaseError

router = APIRouter()
logger = get_logger(__name__)


class FacilityType(str, Enum):
    """Healthcare facility types"""
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    EMERGENCY = "emergency"
    MATERNAL_CHILD = "maternal_child"
    ELDERLY = "elderly"
    ALL = "all"


class DataSource(str, Enum):
    """Data source types"""
    HOSPITAL_AUTHORITY = "hospital_authority"
    DEPARTMENT_HEALTH = "department_health"
    EMERGENCY_SERVICES = "emergency_services"
    ENVIRONMENTAL_DATA = "environmental_data"


class UrgencyLevel(str, Enum):
    """Urgency levels for filtering"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


# Response Models
class FacilityResponse(BaseModel):
    """Healthcare facility response model"""
    id: str
    name_en: str
    name_zh: Optional[str] = None
    type: str
    district: str
    region: Optional[str] = None
    address_en: Optional[str] = None
    address_zh: Optional[str] = None
    phone: Optional[str] = None
    services: List[str] = []
    has_emergency_services: bool = False
    operating_hours: Optional[Dict[str, str]] = None
    current_status: Optional[str] = None
    waiting_time: Optional[str] = None
    waiting_minutes: Optional[int] = None
    last_updated: datetime


class EmergencyHotlineResponse(BaseModel):
    """Emergency hotline response model"""
    hotline_number: str
    service_name_en: str
    service_name_zh: Optional[str] = None
    service_type: str
    category: str
    description_en: Optional[str] = None
    description_zh: Optional[str] = None
    is_24_7: bool
    priority_level: int
    language_support: List[str] = []


class AirQualityResponse(BaseModel):
    """Air quality response model"""
    station_id: str
    station_name_en: str
    station_name_zh: Optional[str] = None
    district: str
    aqi_value: int
    aqi_level: str
    health_risk_level: str
    pollutants: Dict[str, float] = {}
    health_advisory: str
    timestamp: datetime


class HealthAdvisoryResponse(BaseModel):
    """Health advisory response model"""
    advisory_id: str
    title_en: str
    title_zh: Optional[str] = None
    summary_en: str
    summary_zh: Optional[str] = None
    category: str
    severity_level: str
    urgency_score: int
    is_current: bool
    published_date: datetime
    affected_areas: List[str] = []
    target_groups: List[str] = []


class DataSummaryResponse(BaseModel):
    """Data summary response model"""
    source: str
    data_type: str
    total_records: int
    active_records: int
    latest_update: Optional[datetime] = None
    average_quality_score: float
    data_freshness_hours: float


# API Endpoints

@router.get("/facilities", response_model=List[FacilityResponse])
async def get_healthcare_facilities(
    facility_type: FacilityType = Query(FacilityType.ALL, description="Type of healthcare facility"),
    district: Optional[str] = Query(None, description="Hong Kong district"),
    services: Optional[str] = Query(None, description="Required services (comma-separated)"),
    has_emergency: Optional[bool] = Query(None, description="Must have emergency services"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    repository: HKDataRepository = Depends(get_hk_data_repository)
):
    """
    Get healthcare facilities with optional filtering
    
    Returns a list of healthcare facilities including hospitals, clinics,
    and emergency services based on the specified filters.
    """
    try:
        start_time = datetime.utcnow()
        
        # Parse services filter
        services_list = None
        if services:
            services_list = [s.strip() for s in services.split(',')]
        
        # Convert facility type
        facility_type_str = None if facility_type == FacilityType.ALL else facility_type.value
        
        # Search facilities
        facilities = await repository.search_facilities(
            facility_type=facility_type_str,
            district=district,
            services=services_list,
            has_emergency=has_emergency,
            limit=limit
        )
        
        # Convert to response models
        response_data = []
        for facility in facilities:
            response_data.append(FacilityResponse(
                id=facility.get('id', ''),
                name_en=facility.get('name_en', ''),
                name_zh=facility.get('name_zh'),
                type=facility.get('type', ''),
                district=facility.get('district', ''),
                region=facility.get('region'),
                address_en=facility.get('address_en'),
                address_zh=facility.get('address_zh'),
                phone=facility.get('phone'),
                services=facility.get('services', []),
                has_emergency_services=facility.get('has_emergency_services', False),
                operating_hours=facility.get('operating_hours'),
                current_status=facility.get('current_status'),
                waiting_time=facility.get('waiting_time'),
                waiting_minutes=facility.get('waiting_minutes'),
                last_updated=facility.get('last_updated', datetime.utcnow())
            ))
        
        # Log API request
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="GET",
            endpoint="/api/v1/hk-data/facilities",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting healthcare facilities: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/facilities/ae-waiting-times", response_model=List[FacilityResponse])
async def get_ae_waiting_times(
    district: Optional[str] = Query(None, description="Filter by district"),
    repository: HKDataRepository = Depends(get_hk_data_repository)
):
    """
    Get current A&E waiting times for all hospitals
    
    Returns real-time accident and emergency waiting times from Hospital Authority.
    """
    try:
        start_time = datetime.utcnow()
        
        hospitals = await repository.get_ae_waiting_times(district=district)
        
        response_data = []
        for hospital in hospitals:
            response_data.append(FacilityResponse(
                id=hospital.get('hospital_code', ''),
                name_en=hospital.get('hospital_name_en', ''),
                name_zh=hospital.get('hospital_name_zh'),
                type='hospital',
                district=hospital.get('district', ''),
                region=hospital.get('region'),
                services=['emergency'],
                has_emergency_services=True,
                waiting_time=hospital.get('waiting_time'),
                waiting_minutes=hospital.get('waiting_minutes'),
                current_status=hospital.get('urgency_level'),
                last_updated=datetime.fromisoformat(hospital.get('last_updated', datetime.utcnow().isoformat()))
            ))
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="GET",
            endpoint="/api/v1/hk-data/facilities/ae-waiting-times",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting A&E waiting times: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/emergency/hotlines", response_model=List[EmergencyHotlineResponse])
async def get_emergency_hotlines(
    category: Optional[str] = Query(None, description="Filter by category (medical, mental_health, etc.)"),
    emergency_only: bool = Query(False, description="Only show emergency hotlines"),
    repository: HKDataRepository = Depends(get_hk_data_repository)
):
    """
    Get emergency hotlines and support services
    
    Returns emergency contact numbers, crisis hotlines, and support services.
    """
    try:
        start_time = datetime.utcnow()
        
        emergency_info = await repository.get_emergency_info()
        hotlines = emergency_info.get('hotlines', [])
        
        # Apply filters
        if emergency_only:
            hotlines = [h for h in hotlines if h.get('service_type') == 'emergency']
        
        if category:
            hotlines = [h for h in hotlines if h.get('category', '').lower() == category.lower()]
        
        response_data = []
        for hotline in hotlines:
            response_data.append(EmergencyHotlineResponse(
                hotline_number=hotline.get('hotline_number', ''),
                service_name_en=hotline.get('service_name_en', ''),
                service_name_zh=hotline.get('service_name_zh'),
                service_type=hotline.get('service_type', ''),
                category=hotline.get('category', ''),
                description_en=hotline.get('description_en'),
                description_zh=hotline.get('description_zh'),
                is_24_7=hotline.get('is_24_7', False),
                priority_level=hotline.get('priority_level', 3),
                language_support=hotline.get('language_support', [])
            ))
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="GET",
            endpoint="/api/v1/hk-data/emergency/hotlines",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting emergency hotlines: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/environmental/air-quality", response_model=List[AirQualityResponse])
async def get_air_quality(
    district: Optional[str] = Query(None, description="Filter by district"),
    repository: HKDataRepository = Depends(get_hk_data_repository)
):
    """
    Get current air quality data from all monitoring stations
    
    Returns real-time air quality measurements including AQI values and pollutant levels.
    """
    try:
        start_time = datetime.utcnow()
        
        air_quality_data = await repository.get_air_quality_data(district=district)
        stations = air_quality_data.get('stations', [])
        
        response_data = []
        for station in stations:
            response_data.append(AirQualityResponse(
                station_id=station.get('station_id', ''),
                station_name_en=station.get('station_name_en', ''),
                station_name_zh=station.get('station_name_zh'),
                district=station.get('district', ''),
                aqi_value=station.get('aqi_value', 0),
                aqi_level=station.get('aqi_level', 'unknown'),
                health_risk_level=station.get('health_risk_level', 'unknown'),
                pollutants=station.get('pollutants', {}),
                health_advisory=station.get('health_advisory', ''),
                timestamp=datetime.fromisoformat(station.get('timestamp', datetime.utcnow().isoformat()))
            ))
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="GET",
            endpoint="/api/v1/hk-data/environmental/air-quality",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting air quality data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health/advisories", response_model=List[HealthAdvisoryResponse])
async def get_health_advisories(
    category: Optional[str] = Query(None, description="Filter by category"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    active_only: bool = Query(True, description="Only show active advisories"),
    repository: HKDataRepository = Depends(get_hk_data_repository)
):
    """
    Get current health advisories and alerts
    
    Returns health advisories from Department of Health including seasonal alerts,
    outbreak notifications, and public health guidance.
    """
    try:
        start_time = datetime.utcnow()
        
        advisories = await repository.get_health_advisories(
            category=category, 
            active_only=active_only
        )
        
        # Apply severity filter
        if severity:
            advisories = [a for a in advisories if a.get('severity_level', '').lower() == severity.lower()]
        
        response_data = []
        for advisory in advisories:
            response_data.append(HealthAdvisoryResponse(
                advisory_id=advisory.get('advisory_id', ''),
                title_en=advisory.get('title_en', ''),
                title_zh=advisory.get('title_zh'),
                summary_en=advisory.get('summary_en', ''),
                summary_zh=advisory.get('summary_zh'),
                category=advisory.get('category', ''),
                severity_level=advisory.get('severity_level', ''),
                urgency_score=advisory.get('urgency_score', 0),
                is_current=advisory.get('is_current', False),
                published_date=datetime.fromisoformat(advisory.get('published_date', datetime.utcnow().isoformat())),
                affected_areas=advisory.get('affected_areas', []),
                target_groups=advisory.get('target_groups', [])
            ))
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="GET",
            endpoint="/api/v1/hk-data/health/advisories",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting health advisories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/data-summary", response_model=List[DataSummaryResponse])
async def get_data_summary(
    repository: HKDataRepository = Depends(get_hk_data_repository)
):
    """
    Get summary of all data sources and their current status
    
    Returns overview of data freshness, quality scores, and availability
    for all Hong Kong government data sources.
    """
    try:
        start_time = datetime.utcnow()
        
        summaries = await repository.get_data_summary()
        
        response_data = []
        for summary in summaries:
            response_data.append(DataSummaryResponse(
                source=summary.source,
                data_type=summary.data_type,
                total_records=summary.total_records,
                active_records=summary.active_records,
                latest_update=summary.latest_update,
                average_quality_score=summary.average_quality_score,
                data_freshness_hours=summary.data_freshness_hours
            ))
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="GET",
            endpoint="/api/v1/hk-data/data-summary",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting data summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/pipeline/trigger")
async def trigger_data_update(
    source: Optional[DataSource] = Query(None, description="Specific data source to update"),
    endpoint: Optional[str] = Query(None, description="Specific endpoint to update"),
    pipeline: HKDataPipelineOrchestrator = Depends(get_pipeline_orchestrator)
):
    """
    Trigger immediate data update for specified sources
    
    Force an immediate refresh of data from Hong Kong government sources.
    Useful for getting the latest information when needed.
    """
    try:
        start_time = datetime.utcnow()
        
        source_name = source.value if source else None
        
        await pipeline.trigger_immediate_update(
            source_name=source_name,
            endpoint=endpoint
        )
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="POST",
            endpoint="/api/v1/hk-data/pipeline/trigger",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return {
            "message": "Data update triggered successfully",
            "source": source_name,
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering data update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/pipeline/status")
async def get_pipeline_status(
    pipeline: HKDataPipelineOrchestrator = Depends(get_pipeline_orchestrator)
):
    """
    Get current status of the data pipeline
    
    Returns information about pipeline health, task execution,
    and data source status.
    """
    try:
        start_time = datetime.utcnow()
        
        status = await pipeline.get_pipeline_status()
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="GET",
            endpoint="/api/v1/hk-data/pipeline/status",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting pipeline status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/cache/stats")
async def get_cache_stats(
    cache_manager: HKDataCacheManager = Depends(get_cache_manager)
):
    """
    Get cache performance statistics
    
    Returns cache hit rates, memory usage, and performance metrics
    for the data caching system.
    """
    try:
        start_time = datetime.utcnow()
        
        stats = await cache_manager.get_cache_stats()
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="GET",
            endpoint="/api/v1/hk-data/cache/stats",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Utility endpoints for specific use cases

@router.get("/quick-search")
async def quick_search(
    query: str = Query(..., description="Search query"),
    type: Optional[str] = Query(None, description="Search type: facility, emergency, advisory"),
    limit: int = Query(10, ge=1, le=50),
    repository: HKDataRepository = Depends(get_hk_data_repository)
):
    """
    Quick search across all healthcare data
    
    Provides a unified search interface for finding healthcare facilities,
    emergency services, and health information.
    """
    try:
        start_time = datetime.utcnow()
        
        results = {
            'facilities': [],
            'emergency_services': [],
            'health_advisories': [],
            'query': query,
            'search_type': type or 'all'
        }
        
        query_lower = query.lower()
        
        # Search facilities if requested or no type specified
        if not type or type == 'facility':
            facilities = await repository.search_facilities(limit=limit)
            
            # Simple text matching (in production, use full-text search)
            matching_facilities = []
            for facility in facilities:
                if (query_lower in facility.get('name_en', '').lower() or 
                    query_lower in facility.get('district', '').lower() or
                    any(query_lower in service.lower() for service in facility.get('services', []))):
                    matching_facilities.append(facility)
            
            results['facilities'] = matching_facilities[:limit]
        
        # Search emergency services
        if not type or type == 'emergency':
            emergency_info = await repository.get_emergency_info()
            hotlines = emergency_info.get('hotlines', [])
            
            matching_emergency = []
            for hotline in hotlines:
                if (query_lower in hotline.get('service_name_en', '').lower() or
                    query_lower in hotline.get('category', '').lower()):
                    matching_emergency.append(hotline)
            
            results['emergency_services'] = matching_emergency[:limit]
        
        # Search health advisories
        if not type or type == 'advisory':
            advisories = await repository.get_health_advisories()
            
            matching_advisories = []
            for advisory in advisories:
                if (query_lower in advisory.get('title_en', '').lower() or
                    query_lower in advisory.get('category', '').lower() or
                    query_lower in advisory.get('summary_en', '').lower()):
                    matching_advisories.append(advisory)
            
            results['health_advisories'] = matching_advisories[:limit]
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_api_request(
            method="GET",
            endpoint="/api/v1/hk-data/quick-search",
            status_code=200,
            response_time_ms=int(response_time)
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error in quick search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")