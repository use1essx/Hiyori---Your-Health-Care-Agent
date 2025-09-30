"""
Hong Kong Data Repository for Healthcare AI V2
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class HKDataRepository:
    """Repository for Hong Kong healthcare data"""
    
    def __init__(self):
        self.data_cache = {}
    
    async def get_all_facilities(self) -> List[Dict[str, Any]]:
        """Get all healthcare facilities"""
        # Mock data for now
        return [
            {
                "id": 1,
                "name_en": "Queen Mary Hospital",
                "name_zh": "瑪麗醫院",
                "type": "public_hospital",
                "district": "Southern",
                "address": "102 Pokfulam Road, Hong Kong",
                "phone": "2255 3838",
                "emergency": True,
                "waiting_time": "2-3 hours"
            },
            {
                "id": 2,
                "name_en": "Prince of Wales Hospital",
                "name_zh": "威爾斯親王醫院",
                "type": "public_hospital", 
                "district": "Sha Tin",
                "address": "30-32 Ngan Shing Street, Sha Tin, NT",
                "phone": "2632 2211",
                "emergency": True,
                "waiting_time": "1-2 hours"
            }
        ]
    
    async def get_facilities_by_type(self, facility_type: str) -> List[Dict[str, Any]]:
        """Get facilities by type"""
        all_facilities = await self.get_all_facilities()
        return [f for f in all_facilities if f.get("type") == facility_type]
    
    async def get_nearest_facilities(
        self, 
        district: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get nearest facilities"""
        facilities = await self.get_all_facilities()
        if district:
            facilities = [f for f in facilities if f.get("district") == district]
        return facilities[:limit]
    
    async def get_emergency_data(self) -> Dict[str, Any]:
        """Get emergency healthcare data"""
        return {
            "emergency_hotline": "999",
            "poison_hotline": "2772 9133",
            "mental_health_hotline": "2466 7350",
            "hospitals_with_ae": await self.get_facilities_by_type("public_hospital")
        }
    
    async def search_facilities(self, query: str) -> List[Dict[str, Any]]:
        """Search facilities by name or location"""
        facilities = await self.get_all_facilities()
        query_lower = query.lower()
        
        return [
            f for f in facilities 
            if query_lower in f.get("name_en", "").lower() 
            or query_lower in f.get("name_zh", "")
            or query_lower in f.get("district", "").lower()
        ]


# Singleton instance
_hk_data_repository = None


async def get_hk_data_repository() -> HKDataRepository:
    """Get HK data repository instance"""
    global _hk_data_repository
    if _hk_data_repository is None:
        _hk_data_repository = HKDataRepository()
    return _hk_data_repository
















