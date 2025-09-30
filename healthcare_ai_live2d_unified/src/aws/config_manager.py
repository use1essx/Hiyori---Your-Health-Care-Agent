"""
Configuration Management System
==============================

Manages system configuration using AWS Systems Manager Parameter Store
with auto-discovery, validation, and environment-specific settings.
"""

import json
import boto3
import os
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigType(Enum):
    """Configuration parameter types."""
    STRING = "String"
    SECURE_STRING = "SecureString"
    STRING_LIST = "StringList"


@dataclass
class ConfigParameter:
    """Configuration parameter definition."""
    name: str
    value: Union[str, List[str]]
    type: ConfigType
    description: str
    environment: str
    category: str
    sensitive: bool = False
    required: bool = True


class ConfigManager:
    """Manages system configuration with AWS Systems Manager Parameter Store."""
    
    def __init__(self, environment: str = None):
        self.ssm_client = boto3.client('ssm')
        self.sts_client = boto3.client('sts')
        self.environment = environment or os.environ.get('ENVIRONMENT', 'dev')
        
        # Configuration hierarchy
        self.config_prefix = f"/healthcare-ai/{self.environment}"
        
        # Auto-discovered AWS resources
        self._aws_resources = {}
        
        # Configuration categories
        self.categories = {
            'aws_resources': 'AWS Resource ARNs and identifiers',
            'api_endpoints': 'API Gateway and service endpoints',
            'database': 'Database connection and configuration',
            'security': 'Security keys and certificates',
            'features': 'Feature flags and toggles',
            'monitoring': 'Monitoring and alerting configuration',
            'healthcare': 'Healthcare-specific settings'
        }
    
    def get_parameter_name(self, category: str, key: str) -> str:
        """Generate full parameter name with hierarchy."""
        return f"{self.config_prefix}/{category}/{key}"
    
    def put_parameter(self, param: ConfigParameter) -> bool:
        """Store configuration parameter in Parameter Store."""
        try:
            parameter_name = self.get_parameter_name(param.category, param.name)
            
            # Prepare value based on type
            if param.type == ConfigType.STRING_LIST:
                value = ','.join(param.value) if isinstance(param.value, list) else param.value
            else:
                value = str(param.value)
            
            # Put parameter
            self.ssm_client.put_parameter(
                Name=parameter_name,
                Value=value,
                Type=param.type.value,
                Description=param.description,
                Overwrite=True,
                Tags=[
                    {'Key': 'Environment', 'Value': param.environment},
                    {'Key': 'Category', 'Value': param.category},
                    {'Key': 'Sensitive', 'Value': str(param.sensitive)},
                    {'Key': 'Required', 'Value': str(param.required)},
                    {'Key': 'ManagedBy', 'Value': 'HealthcareAI'},
                    {'Key': 'UpdatedAt', 'Value': datetime.utcnow().isoformat()}
                ]
            )
            
            logger.info(f"Stored parameter: {parameter_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing parameter {param.name}: {e}")
            return False
    
    def get_parameter(self, category: str, key: str, decrypt: bool = True) -> Optional[str]:
        """Get configuration parameter from Parameter Store."""
        try:
            parameter_name = self.get_parameter_name(category, key)
            
            response = self.ssm_client.get_parameter(
                Name=parameter_name,
                WithDecryption=decrypt
            )
            
            return response['Parameter']['Value']
            
        except self.ssm_client.exceptions.ParameterNotFound:
            logger.warning(f"Parameter not found: {category}/{key}")
            return None
        except Exception as e:
            logger.error(f"Error getting parameter {category}/{key}: {e}")
            return None
    
    def get_parameters_by_category(self, category: str, decrypt: bool = True) -> Dict[str, str]:
        """Get all parameters in a category."""
        try:
            path = f"{self.config_prefix}/{category}/"
            
            response = self.ssm_client.get_parameters_by_path(
                Path=path,
                Recursive=True,
                WithDecryption=decrypt
            )
            
            parameters = {}
            for param in response['Parameters']:
                # Extract key from full parameter name
                key = param['Name'].replace(path, '')
                parameters[key] = param['Value']
            
            return parameters
            
        except Exception as e:
            logger.error(f"Error getting parameters for category {category}: {e}")
            return {}
    
    def get_all_parameters(self, decrypt: bool = True) -> Dict[str, Dict[str, str]]:
        """Get all configuration parameters organized by category."""
        all_config = {}
        
        for category in self.categories.keys():
            all_config[category] = self.get_parameters_by_category(category, decrypt)
        
        return all_config
    
    def delete_parameter(self, category: str, key: str) -> bool:
        """Delete configuration parameter."""
        try:
            parameter_name = self.get_parameter_name(category, key)
            
            self.ssm_client.delete_parameter(Name=parameter_name)
            
            logger.info(f"Deleted parameter: {parameter_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting parameter {category}/{key}: {e}")
            return False
    
    def auto_discover_aws_resources(self) -> Dict[str, str]:
        """Auto-discover AWS resource ARNs and identifiers."""
        resources = {}
        
        try:
            # Get account ID and region
            account_id = self.sts_client.get_caller_identity()['Account']
            region = boto3.Session().region_name or 'us-east-1'
            
            resources['account_id'] = account_id
            resources['region'] = region
            
            # Discover Lambda functions
            lambda_client = boto3.client('lambda')
            try:
                functions = lambda_client.list_functions()
                healthcare_functions = {}
                
                for func in functions['Functions']:
                    func_name = func['FunctionName']
                    if 'healthcare' in func_name.lower():
                        healthcare_functions[func_name] = func['FunctionArn']
                
                resources['lambda_functions'] = json.dumps(healthcare_functions)
            except Exception as e:
                logger.warning(f"Could not discover Lambda functions: {e}")
            
            # Discover DynamoDB tables
            dynamodb_client = boto3.client('dynamodb')
            try:
                tables = dynamodb_client.list_tables()
                healthcare_tables = {}
                
                for table_name in tables['TableNames']:
                    if 'healthcare' in table_name.lower():
                        table_arn = f"arn:aws:dynamodb:{region}:{account_id}:table/{table_name}"
                        healthcare_tables[table_name] = table_arn
                
                resources['dynamodb_tables'] = json.dumps(healthcare_tables)
            except Exception as e:
                logger.warning(f"Could not discover DynamoDB tables: {e}")
            
            # Discover S3 buckets
            s3_client = boto3.client('s3')
            try:
                buckets = s3_client.list_buckets()
                healthcare_buckets = {}
                
                for bucket in buckets['Buckets']:
                    bucket_name = bucket['Name']
                    if 'healthcare' in bucket_name.lower():
                        bucket_arn = f"arn:aws:s3:::{bucket_name}"
                        healthcare_buckets[bucket_name] = bucket_arn
                
                resources['s3_buckets'] = json.dumps(healthcare_buckets)
            except Exception as e:
                logger.warning(f"Could not discover S3 buckets: {e}")
            
            # Discover API Gateway APIs
            apigateway_client = boto3.client('apigateway')
            try:
                apis = apigateway_client.get_rest_apis()
                healthcare_apis = {}
                
                for api in apis['items']:
                    api_name = api['name']
                    if 'healthcare' in api_name.lower():
                        api_url = f"https://{api['id']}.execute-api.{region}.amazonaws.com"
                        healthcare_apis[api_name] = api_url
                
                resources['api_gateways'] = json.dumps(healthcare_apis)
            except Exception as e:
                logger.warning(f"Could not discover API Gateways: {e}")
            
            # Discover SNS topics
            sns_client = boto3.client('sns')
            try:
                topics = sns_client.list_topics()
                healthcare_topics = {}
                
                for topic in topics['Topics']:
                    topic_arn = topic['TopicArn']
                    topic_name = topic_arn.split(':')[-1]
                    if 'healthcare' in topic_name.lower():
                        healthcare_topics[topic_name] = topic_arn
                
                resources['sns_topics'] = json.dumps(healthcare_topics)
            except Exception as e:
                logger.warning(f"Could not discover SNS topics: {e}")
            
            self._aws_resources = resources
            return resources
            
        except Exception as e:
            logger.error(f"Error during auto-discovery: {e}")
            return {}
    
    def store_aws_resources(self) -> bool:
        """Store auto-discovered AWS resources in Parameter Store."""
        if not self._aws_resources:
            self.auto_discover_aws_resources()
        
        success_count = 0
        
        for key, value in self._aws_resources.items():
            param = ConfigParameter(
                name=key,
                value=value,
                type=ConfigType.STRING,
                description=f"Auto-discovered {key} for healthcare AI system",
                environment=self.environment,
                category='aws_resources',
                sensitive=False,
                required=False
            )
            
            if self.put_parameter(param):
                success_count += 1
        
        logger.info(f"Stored {success_count}/{len(self._aws_resources)} AWS resources")
        return success_count == len(self._aws_resources)
    
    def initialize_default_config(self) -> bool:
        """Initialize default configuration parameters."""
        default_params = [
            # API Endpoints
            ConfigParameter(
                name="agent_router_url",
                value="{{API_GATEWAY_URL}}/agent-router",
                type=ConfigType.STRING,
                description="Agent router API endpoint",
                environment=self.environment,
                category="api_endpoints"
            ),
            ConfigParameter(
                name="speech_to_text_url",
                value="{{API_GATEWAY_URL}}/speech-to-text",
                type=ConfigType.STRING,
                description="Speech-to-text API endpoint",
                environment=self.environment,
                category="api_endpoints"
            ),
            ConfigParameter(
                name="text_to_speech_url",
                value="{{API_GATEWAY_URL}}/text-to-speech",
                type=ConfigType.STRING,
                description="Text-to-speech API endpoint",
                environment=self.environment,
                category="api_endpoints"
            ),
            
            # Database Configuration
            ConfigParameter(
                name="conversations_table",
                value=f"HealthcareAI-{self.environment.title()}-Conversations",
                type=ConfigType.STRING,
                description="DynamoDB conversations table name",
                environment=self.environment,
                category="database"
            ),
            ConfigParameter(
                name="users_table",
                value=f"HealthcareAI-{self.environment.title()}-Users",
                type=ConfigType.STRING,
                description="DynamoDB users table name",
                environment=self.environment,
                category="database"
            ),
            
            # Feature Flags
            ConfigParameter(
                name="speech_enabled",
                value="true",
                type=ConfigType.STRING,
                description="Enable speech-to-text and text-to-speech features",
                environment=self.environment,
                category="features"
            ),
            ConfigParameter(
                name="live2d_enabled",
                value="true",
                type=ConfigType.STRING,
                description="Enable Live2D avatar functionality",
                environment=self.environment,
                category="features"
            ),
            ConfigParameter(
                name="file_upload_enabled",
                value="true",
                type=ConfigType.STRING,
                description="Enable file upload and processing",
                environment=self.environment,
                category="features"
            ),
            
            # Healthcare Configuration
            ConfigParameter(
                name="supported_languages",
                value=["zh-HK", "en-US"],
                type=ConfigType.STRING_LIST,
                description="Supported languages for healthcare AI",
                environment=self.environment,
                category="healthcare"
            ),
            ConfigParameter(
                name="emergency_hotline",
                value="999",
                type=ConfigType.STRING,
                description="Hong Kong emergency services number",
                environment=self.environment,
                category="healthcare"
            ),
            ConfigParameter(
                name="crisis_hotline",
                value="2896 0000",
                type=ConfigType.STRING,
                description="Samaritans Hong Kong crisis hotline",
                environment=self.environment,
                category="healthcare"
            ),
            
            # Monitoring Configuration
            ConfigParameter(
                name="cost_alert_threshold_daily",
                value="50.0",
                type=ConfigType.STRING,
                description="Daily cost alert threshold in USD",
                environment=self.environment,
                category="monitoring"
            ),
            ConfigParameter(
                name="log_level",
                value="INFO",
                type=ConfigType.STRING,
                description="Application log level",
                environment=self.environment,
                category="monitoring"
            )
        ]
        
        success_count = 0
        for param in default_params:
            if self.put_parameter(param):
                success_count += 1
        
        logger.info(f"Initialized {success_count}/{len(default_params)} default parameters")
        return success_count == len(default_params)
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration and report issues."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'missing_required': [],
            'categories_checked': list(self.categories.keys())
        }
        
        # Check each category
        for category in self.categories.keys():
            try:
                params = self.get_parameters_by_category(category, decrypt=False)
                
                if not params:
                    validation_result['warnings'].append(f"No parameters found in category: {category}")
                    continue
                
                # Category-specific validations
                if category == 'api_endpoints':
                    required_endpoints = ['agent_router_url', 'speech_to_text_url', 'text_to_speech_url']
                    for endpoint in required_endpoints:
                        if endpoint not in params:
                            validation_result['missing_required'].append(f"{category}/{endpoint}")
                        elif '{{' in params[endpoint]:
                            validation_result['warnings'].append(f"Endpoint {endpoint} contains placeholder values")
                
                elif category == 'database':
                    required_tables = ['conversations_table', 'users_table']
                    for table in required_tables:
                        if table not in params:
                            validation_result['missing_required'].append(f"{category}/{table}")
                
                elif category == 'healthcare':
                    required_settings = ['supported_languages', 'emergency_hotline']
                    for setting in required_settings:
                        if setting not in params:
                            validation_result['missing_required'].append(f"{category}/{setting}")
                
            except Exception as e:
                validation_result['errors'].append(f"Error validating category {category}: {e}")
        
        # Set overall validity
        if validation_result['errors'] or validation_result['missing_required']:
            validation_result['valid'] = False
        
        return validation_result
    
    def export_configuration(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Export all configuration for backup or migration."""
        try:
            config_export = {
                'environment': self.environment,
                'exported_at': datetime.utcnow().isoformat(),
                'categories': {}
            }
            
            for category in self.categories.keys():
                params = self.get_parameters_by_category(category, decrypt=include_sensitive)
                if params:
                    config_export['categories'][category] = params
            
            return config_export
            
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return {'error': str(e)}
    
    def import_configuration(self, config_data: Dict[str, Any], overwrite: bool = False) -> Dict[str, Any]:
        """Import configuration from backup or migration."""
        import_result = {
            'success': True,
            'imported_count': 0,
            'skipped_count': 0,
            'errors': []
        }
        
        try:
            categories = config_data.get('categories', {})
            
            for category, params in categories.items():
                for key, value in params.items():
                    # Check if parameter already exists
                    existing_value = self.get_parameter(category, key)
                    
                    if existing_value and not overwrite:
                        import_result['skipped_count'] += 1
                        continue
                    
                    # Create parameter
                    param = ConfigParameter(
                        name=key,
                        value=value,
                        type=ConfigType.STRING,  # Default type for imports
                        description=f"Imported parameter from backup",
                        environment=self.environment,
                        category=category
                    )
                    
                    if self.put_parameter(param):
                        import_result['imported_count'] += 1
                    else:
                        import_result['errors'].append(f"Failed to import {category}/{key}")
            
            if import_result['errors']:
                import_result['success'] = False
            
            return import_result
            
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return {
                'success': False,
                'error': str(e),
                'imported_count': 0,
                'skipped_count': 0,
                'errors': [str(e)]
            }


# Global configuration manager instance
config_manager = ConfigManager()


def get_config(category: str, key: str, default: str = None) -> str:
    """Convenience function to get configuration value."""
    value = config_manager.get_parameter(category, key)
    return value if value is not None else default


def get_config_dict(category: str) -> Dict[str, str]:
    """Convenience function to get all configuration in a category."""
    return config_manager.get_parameters_by_category(category)


def setup_configuration(environment: str = None) -> Dict[str, Any]:
    """Setup configuration for the healthcare AI system."""
    if environment:
        global config_manager
        config_manager = ConfigManager(environment)
    
    # Auto-discover AWS resources
    logger.info("Auto-discovering AWS resources...")
    resources = config_manager.auto_discover_aws_resources()
    
    # Store discovered resources
    logger.info("Storing AWS resources in Parameter Store...")
    config_manager.store_aws_resources()
    
    # Initialize default configuration
    logger.info("Initializing default configuration...")
    config_manager.initialize_default_config()
    
    # Validate configuration
    logger.info("Validating configuration...")
    validation = config_manager.validate_configuration()
    
    return {
        'environment': config_manager.environment,
        'aws_resources_discovered': len(resources),
        'validation': validation,
        'setup_completed_at': datetime.utcnow().isoformat()
    }