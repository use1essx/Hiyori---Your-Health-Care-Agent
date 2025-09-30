"""
Hong Kong Healthcare Data Integration Lambda
===========================================

Fetches and caches Hong Kong healthcare data including emergency services,
hospital information, and local health resources with Traditional Chinese support.
"""

import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import requests
from urllib.parse import urljoin

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
eventbridge = boto3.client('events')

# Environment variables
SYSTEM_CONFIG_TABLE = os.environ.get('SYSTEM_CONFIG_TABLE')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Initialize DynamoDB table
config_table = dynamodb.Table(SYSTEM_CONFIG_TABLE) if SYSTEM_CONFIG_TABLE else None


class HKHealthcareDataProvider:
    """Provides Hong Kong healthcare data with caching and updates."""
    
    def __init__(self):
        self.config_table = config_table
        
        # Hong Kong healthcare data sources
        self.data_sources = {
            'emergency_services': {
                'static': True,
                'cache_duration': 86400 * 7,  # 7 days
                'data': self._get_emergency_services_data()
            },
            'hospitals': {
                'static': True,
                'cache_duration': 86400 * 7,  # 7 days
                'data': self._get_hospitals_data()
            },
            'clinics': {
                'static': True,
                'cache_duration': 86400 * 7,  # 7 days
                'data': self._get_clinics_data()
            },
            'mental_health_services': {
                'static': True,
                'cache_duration': 86400 * 7,  # 7 days
                'data': self._get_mental_health_services_data()
            },
            'health_education': {
                'static': True,
                'cache_duration': 86400 * 1,  # 1 day
                'data': self._get_health_education_data()
            }
        }
    
    def _get_emergency_services_data(self) -> Dict[str, Any]:
        """Get Hong Kong emergency services information."""
        return {
            'emergency_hotlines': {
                'general_emergency': {
                    'number': '999',
                    'name_en': 'Emergency Services',
                    'name_zh': '緊急服務',
                    'description_en': 'Police, Fire, Ambulance',
                    'description_zh': '警察、消防、救護車',
                    'available_24_7': True
                },
                'poison_control': {
                    'number': '2772 9933',
                    'name_en': 'Poison Information Centre',
                    'name_zh': '中毒資訊中心',
                    'description_en': 'Poison emergency information',
                    'description_zh': '中毒緊急資訊',
                    'available_24_7': True
                },
                'samaritans': {
                    'number': '2896 0000',
                    'name_en': 'Samaritans Hong Kong',
                    'name_zh': '香港撒瑪利亞會',
                    'description_en': 'Suicide prevention and emotional support',
                    'description_zh': '自殺預防及情緒支援',
                    'available_24_7': True
                },
                'suicide_prevention': {
                    'number': '2382 0000',
                    'name_en': 'Suicide Prevention Services',
                    'name_zh': '自殺預防服務',
                    'description_en': 'Crisis intervention and counseling',
                    'description_zh': '危機介入及輔導',
                    'available_24_7': True
                },
                'child_protection': {
                    'number': '2755 1122',
                    'name_en': 'Child Protection Hotline',
                    'name_zh': '保護兒童熱線',
                    'description_en': 'Child abuse reporting and support',
                    'description_zh': '舉報虐兒及支援服務',
                    'available_24_7': True
                }
            },
            'emergency_departments': [
                {
                    'name_en': 'Queen Mary Hospital A&E',
                    'name_zh': '瑪麗醫院急症室',
                    'address_en': '102 Pokfulam Road, Hong Kong',
                    'address_zh': '香港薄扶林道102號',
                    'phone': '2255 3838',
                    'region': 'Hong Kong Island'
                },
                {
                    'name_en': 'Queen Elizabeth Hospital A&E',
                    'name_zh': '伊利沙伯醫院急症室',
                    'address_en': '30 Gascoigne Road, Yau Ma Tei, Kowloon',
                    'address_zh': '九龍油麻地加士居道30號',
                    'phone': '2958 8888',
                    'region': 'Kowloon'
                },
                {
                    'name_en': 'Prince of Wales Hospital A&E',
                    'name_zh': '威爾斯親王醫院急症室',
                    'address_en': '30-32 Ngan Shing Street, Sha Tin, New Territories',
                    'address_zh': '新界沙田銀城街30-32號',
                    'phone': '2632 2211',
                    'region': 'New Territories'
                }
            ]
        }
    
    def _get_hospitals_data(self) -> Dict[str, Any]:
        """Get Hong Kong Hospital Authority hospitals data."""
        return {
            'public_hospitals': [
                {
                    'name_en': 'Queen Mary Hospital',
                    'name_zh': '瑪麗醫院',
                    'cluster': 'Hong Kong West Cluster',
                    'cluster_zh': '港島西聯網',
                    'address_en': '102 Pokfulam Road, Hong Kong',
                    'address_zh': '香港薄扶林道102號',
                    'phone': '2255 3838',
                    'services': ['Emergency', 'General Medicine', 'Surgery', 'Oncology'],
                    'services_zh': ['急症', '內科', '外科', '腫瘤科']
                },
                {
                    'name_en': 'Queen Elizabeth Hospital',
                    'name_zh': '伊利沙伯醫院',
                    'cluster': 'Kowloon Central Cluster',
                    'cluster_zh': '九龍中聯網',
                    'address_en': '30 Gascoigne Road, Yau Ma Tei, Kowloon',
                    'address_zh': '九龍油麻地加士居道30號',
                    'phone': '2958 8888',
                    'services': ['Emergency', 'Cardiology', 'Neurology', 'Orthopedics'],
                    'services_zh': ['急症', '心臟科', '神經科', '骨科']
                },
                {
                    'name_en': 'Prince of Wales Hospital',
                    'name_zh': '威爾斯親王醫院',
                    'cluster': 'New Territories East Cluster',
                    'cluster_zh': '新界東聯網',
                    'address_en': '30-32 Ngan Shing Street, Sha Tin, New Territories',
                    'address_zh': '新界沙田銀城街30-32號',
                    'phone': '2632 2211',
                    'services': ['Emergency', 'Pediatrics', 'Obstetrics', 'Psychiatry'],
                    'services_zh': ['急症', '兒科', '婦產科', '精神科']
                }
            ],
            'private_hospitals': [
                {
                    'name_en': 'Hong Kong Sanatorium & Hospital',
                    'name_zh': '香港養和醫院',
                    'address_en': '2 Village Road, Happy Valley, Hong Kong',
                    'address_zh': '香港跑馬地山村道2號',
                    'phone': '2572 0211',
                    'services': ['General Medicine', 'Surgery', 'Maternity', 'Health Check'],
                    'services_zh': ['內科', '外科', '產科', '身體檢查']
                },
                {
                    'name_en': 'Baptist Hospital',
                    'name_zh': '浸會醫院',
                    'address_en': '222 Waterloo Road, Kowloon Tong, Kowloon',
                    'address_zh': '九龍九龍塘窩打老道222號',
                    'phone': '2339 8888',
                    'services': ['Oncology', 'Cardiology', 'Orthopedics', 'Rehabilitation'],
                    'services_zh': ['腫瘤科', '心臟科', '骨科', '復康科']
                }
            ]
        }
    
    def _get_clinics_data(self) -> Dict[str, Any]:
        """Get Hong Kong clinics and healthcare centers data."""
        return {
            'general_outpatient_clinics': [
                {
                    'name_en': 'Central GOPC',
                    'name_zh': '中環普通科門診診所',
                    'address_en': '1/F, AIA Central, 1 Connaught Road Central',
                    'address_zh': '中環干諾道中1號友邦金融中心1樓',
                    'phone': '2200 2288',
                    'services': ['General Practice', 'Chronic Disease Management'],
                    'services_zh': ['普通科', '慢性疾病管理']
                },
                {
                    'name_en': 'Tsim Sha Tsui GOPC',
                    'name_zh': '尖沙咀普通科門診診所',
                    'address_en': '2/F, 66 Nathan Road, Tsim Sha Tsui',
                    'address_zh': '尖沙咀彌敦道66號2樓',
                    'phone': '2200 2299',
                    'services': ['General Practice', 'Health Education'],
                    'services_zh': ['普通科', '健康教育']
                }
            ],
            'specialist_outpatient_clinics': [
                {
                    'name_en': 'Diabetes Centre',
                    'name_zh': '糖尿病中心',
                    'address_en': 'Queen Mary Hospital',
                    'address_zh': '瑪麗醫院',
                    'phone': '2255 4543',
                    'specialties': ['Diabetes', 'Endocrinology'],
                    'specialties_zh': ['糖尿病', '內分泌科']
                },
                {
                    'name_en': 'Cardiac Centre',
                    'name_zh': '心臟中心',
                    'address_en': 'Queen Elizabeth Hospital',
                    'address_zh': '伊利沙伯醫院',
                    'phone': '2958 6688',
                    'specialties': ['Cardiology', 'Cardiac Surgery'],
                    'specialties_zh': ['心臟科', '心臟外科']
                }
            ]
        }
    
    def _get_mental_health_services_data(self) -> Dict[str, Any]:
        """Get Hong Kong mental health services data."""
        return {
            'crisis_services': [
                {
                    'name_en': 'Samaritans Hong Kong',
                    'name_zh': '香港撒瑪利亞會',
                    'phone': '2896 0000',
                    'whatsapp': '9101 2012',
                    'email': 'jo@samaritans.org.hk',
                    'services': ['24/7 Crisis Support', 'Suicide Prevention'],
                    'services_zh': ['24小時危機支援', '自殺預防'],
                    'languages': ['Cantonese', 'English', 'Mandarin'],
                    'languages_zh': ['廣東話', '英語', '普通話']
                },
                {
                    'name_en': 'Suicide Prevention Services',
                    'name_zh': '自殺預防服務',
                    'phone': '2382 0000',
                    'services': ['Crisis Intervention', 'Counseling'],
                    'services_zh': ['危機介入', '輔導服務'],
                    'available_24_7': True
                }
            ],
            'counseling_services': [
                {
                    'name_en': 'Family Planning Association Counseling Service',
                    'name_zh': '家庭計劃指導會輔導服務',
                    'phone': '2572 2222',
                    'services': ['Individual Counseling', 'Family Therapy'],
                    'services_zh': ['個人輔導', '家庭治療']
                },
                {
                    'name_en': 'Caritas Family Service',
                    'name_zh': '明愛家庭服務',
                    'phone': '2339 3312',
                    'services': ['Family Counseling', 'Youth Services'],
                    'services_zh': ['家庭輔導', '青少年服務']
                }
            ],
            'youth_services': [
                {
                    'name_en': 'Teen Talk',
                    'name_zh': '青少年熱線',
                    'phone': '2777 8899',
                    'whatsapp': '6112 9933',
                    'services': ['Youth Counseling', 'Peer Support'],
                    'services_zh': ['青少年輔導', '朋輩支援'],
                    'age_range': '12-25'
                },
                {
                    'name_en': 'Open Up',
                    'name_zh': 'Open Up',
                    'whatsapp': '9101 2012',
                    'services': ['Online Counseling', 'Mental Health Support'],
                    'services_zh': ['網上輔導', '精神健康支援'],
                    'platform': 'WhatsApp'
                }
            ]
        }
    
    def _get_health_education_data(self) -> Dict[str, Any]:
        """Get Hong Kong health education resources."""
        return {
            'government_resources': [
                {
                    'name_en': 'Centre for Health Protection',
                    'name_zh': '衞生防護中心',
                    'website': 'https://www.chp.gov.hk',
                    'phone': '2125 1111',
                    'services': ['Health Information', 'Disease Prevention'],
                    'services_zh': ['健康資訊', '疾病預防']
                },
                {
                    'name_en': 'Department of Health',
                    'name_zh': '衞生署',
                    'website': 'https://www.dh.gov.hk',
                    'phone': '2961 8989',
                    'services': ['Public Health', 'Health Promotion'],
                    'services_zh': ['公共衞生', '健康推廣']
                }
            ],
            'health_topics': {
                'diabetes': {
                    'name_en': 'Diabetes Management',
                    'name_zh': '糖尿病管理',
                    'resources': [
                        {
                            'title_en': 'Living with Diabetes',
                            'title_zh': '與糖尿病共存',
                            'url': 'https://www.ha.org.hk/diabetes',
                            'type': 'guide'
                        }
                    ]
                },
                'hypertension': {
                    'name_en': 'High Blood Pressure',
                    'name_zh': '高血壓',
                    'resources': [
                        {
                            'title_en': 'Managing High Blood Pressure',
                            'title_zh': '管理高血壓',
                            'url': 'https://www.ha.org.hk/hypertension',
                            'type': 'guide'
                        }
                    ]
                },
                'mental_health': {
                    'name_en': 'Mental Health',
                    'name_zh': '精神健康',
                    'resources': [
                        {
                            'title_en': 'Mental Health First Aid',
                            'title_zh': '精神健康急救',
                            'url': 'https://www.ha.org.hk/mental-health',
                            'type': 'guide'
                        }
                    ]
                }
            }
        }
    
    def get_cached_data(self, data_type: str) -> Optional[Dict[str, Any]]:
        """Get cached data from DynamoDB."""
        if not self.config_table:
            return None
        
        try:
            response = self.config_table.get_item(
                Key={'config_key': f'hk_healthcare_{data_type}'}
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            # Check if data is still valid
            updated_at = datetime.fromisoformat(item['updated_at'])
            cache_duration = self.data_sources[data_type]['cache_duration']
            
            if (datetime.utcnow() - updated_at).total_seconds() > cache_duration:
                return None  # Cache expired
            
            return item['data']
            
        except Exception as e:
            logger.error(f"Error retrieving cached data: {e}")
            return None
    
    def store_cached_data(self, data_type: str, data: Dict[str, Any]) -> bool:
        """Store data in DynamoDB cache."""
        if not self.config_table:
            return False
        
        try:
            self.config_table.put_item(
                Item={
                    'config_key': f'hk_healthcare_{data_type}',
                    'category': 'healthcare_data',
                    'data': data,
                    'updated_at': datetime.utcnow().isoformat(),
                    'data_type': data_type,
                    'source': 'hk_healthcare_integration'
                }
            )
            
            logger.info(f"Stored cached data for {data_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing cached data: {e}")
            return False
    
    def get_healthcare_data(self, data_type: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Get healthcare data with caching."""
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.get_cached_data(data_type)
            if cached_data:
                return {
                    'data': cached_data,
                    'source': 'cache',
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        # Get fresh data
        if data_type not in self.data_sources:
            return {
                'error': f'Unknown data type: {data_type}',
                'available_types': list(self.data_sources.keys())
            }
        
        source_config = self.data_sources[data_type]
        fresh_data = source_config['data']
        
        # Store in cache
        self.store_cached_data(data_type, fresh_data)
        
        return {
            'data': fresh_data,
            'source': 'fresh',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_all_healthcare_data(self) -> Dict[str, Any]:
        """Get all Hong Kong healthcare data."""
        all_data = {}
        
        for data_type in self.data_sources.keys():
            result = self.get_healthcare_data(data_type)
            all_data[data_type] = result
        
        return {
            'healthcare_data': all_data,
            'generated_at': datetime.utcnow().isoformat(),
            'data_types': list(self.data_sources.keys())
        }
    
    def search_services(self, query: str, service_type: str = None, language: str = 'zh') -> List[Dict[str, Any]]:
        """Search healthcare services by query."""
        results = []
        query_lower = query.lower()
        
        # Determine which data types to search
        search_types = [service_type] if service_type else list(self.data_sources.keys())
        
        for data_type in search_types:
            data_result = self.get_healthcare_data(data_type)
            if 'data' not in data_result:
                continue
            
            data = data_result['data']
            
            # Search through the data structure
            matches = self._search_in_data(data, query_lower, language)
            
            for match in matches:
                match['data_type'] = data_type
                results.append(match)
        
        return results
    
    def _search_in_data(self, data: Any, query: str, language: str) -> List[Dict[str, Any]]:
        """Recursively search through data structure."""
        matches = []
        
        if isinstance(data, dict):
            # Check if this dict represents a service/resource
            if self._is_service_dict(data):
                if self._matches_query(data, query, language):
                    matches.append(data)
            else:
                # Recursively search nested dicts
                for value in data.values():
                    matches.extend(self._search_in_data(value, query, language))
        
        elif isinstance(data, list):
            # Search through list items
            for item in data:
                matches.extend(self._search_in_data(item, query, language))
        
        return matches
    
    def _is_service_dict(self, data: Dict[str, Any]) -> bool:
        """Check if a dictionary represents a service or resource."""
        service_indicators = ['name_en', 'name_zh', 'phone', 'address_en', 'services']
        return any(key in data for key in service_indicators)
    
    def _matches_query(self, service: Dict[str, Any], query: str, language: str) -> bool:
        """Check if a service matches the search query."""
        # Fields to search based on language
        if language == 'zh':
            search_fields = ['name_zh', 'description_zh', 'services_zh', 'address_zh']
        else:
            search_fields = ['name_en', 'description_en', 'services', 'address_en']
        
        # Also search common fields
        search_fields.extend(['phone', 'number'])
        
        for field in search_fields:
            if field in service:
                value = service[field]
                if isinstance(value, str) and query in value.lower():
                    return True
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and query in item.lower():
                            return True
        
        return False


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for Hong Kong healthcare data integration.
    
    Expected event structure:
    {
        "action": "get_data" | "get_all" | "search" | "refresh",
        "data_type": "emergency_services" | "hospitals" | "clinics" | "mental_health_services" | "health_education",
        "query": "search query" (for search action),
        "language": "zh" | "en" (default: zh),
        "force_refresh": true/false (default: false)
    }
    """
    try:
        # Parse input
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        action = body.get('action', 'get_data')
        provider = HKHealthcareDataProvider()
        
        if action == 'get_data':
            # Get specific healthcare data type
            data_type = body.get('data_type', 'emergency_services')
            force_refresh = body.get('force_refresh', False)
            
            result = provider.get_healthcare_data(data_type, force_refresh)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(result, ensure_ascii=False)
            }
        
        elif action == 'get_all':
            # Get all healthcare data
            result = provider.get_all_healthcare_data()
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps(result, ensure_ascii=False)
            }
        
        elif action == 'search':
            # Search healthcare services
            query = body.get('query', '')
            service_type = body.get('data_type')
            language = body.get('language', 'zh')
            
            if not query:
                return {
                    'statusCode': 400,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Query is required for search'})
                }
            
            results = provider.search_services(query, service_type, language)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'query': query,
                    'language': language,
                    'results': results,
                    'result_count': len(results),
                    'searched_at': datetime.utcnow().isoformat()
                }, ensure_ascii=False)
            }
        
        elif action == 'refresh':
            # Force refresh all cached data
            refreshed_types = []
            
            for data_type in provider.data_sources.keys():
                result = provider.get_healthcare_data(data_type, force_refresh=True)
                if 'data' in result:
                    refreshed_types.append(data_type)
            
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'refreshed_types': refreshed_types,
                    'refresh_count': len(refreshed_types),
                    'refreshed_at': datetime.utcnow().isoformat()
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
    
    except Exception as e:
        logger.error(f"Error in HK healthcare data handler: {e}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }