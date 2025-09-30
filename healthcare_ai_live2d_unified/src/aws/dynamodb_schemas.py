"""
DynamoDB Table Schemas
=====================

Defines the table schemas and indexes for the healthcare AI system.
"""

from typing import Dict, Any, List


def get_conversations_table_schema() -> Dict[str, Any]:
    """Get the schema for the Conversations table."""
    return {
        'TableName': 'HealthcareAI-Conversations',
        'KeySchema': [
            {
                'AttributeName': 'conversation_id',
                'KeyType': 'HASH'  # Partition key
            },
            {
                'AttributeName': 'timestamp',
                'KeyType': 'RANGE'  # Sort key
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'conversation_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'timestamp',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'agent_type',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'urgency_level',
                'AttributeType': 'S'
            }
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'AgentTypeIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'agent_type',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'timestamp',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'BillingMode': 'PAY_PER_REQUEST'
            },
            {
                'IndexName': 'UrgencyIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'urgency_level',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'timestamp',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'KEYS_ONLY'
                },
                'BillingMode': 'PAY_PER_REQUEST'
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'StreamSpecification': {
            'StreamEnabled': True,
            'StreamViewType': 'NEW_AND_OLD_IMAGES'
        },
        'TimeToLiveSpecification': {
            'AttributeName': 'ttl',
            'Enabled': True
        },
        'Tags': [
            {
                'Key': 'Project',
                'Value': 'HealthcareAI'
            },
            {
                'Key': 'Environment',
                'Value': 'Production'
            },
            {
                'Key': 'DataType',
                'Value': 'Conversations'
            }
        ]
    }


def get_users_table_schema() -> Dict[str, Any]:
    """Get the schema for the Users table."""
    return {
        'TableName': 'HealthcareAI-Users',
        'KeySchema': [
            {
                'AttributeName': 'user_id',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'user_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'age_group',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'created_at',
                'AttributeType': 'S'
            }
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'AgeGroupIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'age_group',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'created_at',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'KEYS_ONLY'
                },
                'BillingMode': 'PAY_PER_REQUEST'
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'StreamSpecification': {
            'StreamEnabled': True,
            'StreamViewType': 'NEW_AND_OLD_IMAGES'
        },
        'Tags': [
            {
                'Key': 'Project',
                'Value': 'HealthcareAI'
            },
            {
                'Key': 'Environment',
                'Value': 'Production'
            },
            {
                'Key': 'DataType',
                'Value': 'UserProfiles'
            },
            {
                'Key': 'Privacy',
                'Value': 'Sensitive'
            }
        ]
    }


def get_conversation_summaries_table_schema() -> Dict[str, Any]:
    """Get the schema for the ConversationSummaries table."""
    return {
        'TableName': 'HealthcareAI-ConversationSummaries',
        'KeySchema': [
            {
                'AttributeName': 'conversation_id',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'conversation_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'user_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'start_time',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'agent_type',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'urgency_level',
                'AttributeType': 'S'
            }
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'UserIdIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'user_id',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'start_time',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'BillingMode': 'PAY_PER_REQUEST'
            },
            {
                'IndexName': 'AgentTypeTimeIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'agent_type',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'start_time',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'BillingMode': 'PAY_PER_REQUEST'
            },
            {
                'IndexName': 'UrgencyTimeIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'urgency_level',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'start_time',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'KEYS_ONLY'
                },
                'BillingMode': 'PAY_PER_REQUEST'
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'StreamSpecification': {
            'StreamEnabled': True,
            'StreamViewType': 'NEW_AND_OLD_IMAGES'
        },
        'Tags': [
            {
                'Key': 'Project',
                'Value': 'HealthcareAI'
            },
            {
                'Key': 'Environment',
                'Value': 'Production'
            },
            {
                'Key': 'DataType',
                'Value': 'ConversationSummaries'
            }
        ]
    }


def get_file_metadata_table_schema() -> Dict[str, Any]:
    """Get the schema for the FileMetadata table (for document uploads)."""
    return {
        'TableName': 'HealthcareAI-FileMetadata',
        'KeySchema': [
            {
                'AttributeName': 'file_id',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'file_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'user_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'upload_time',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'file_type',
                'AttributeType': 'S'
            }
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'UserFilesIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'user_id',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'upload_time',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'BillingMode': 'PAY_PER_REQUEST'
            },
            {
                'IndexName': 'FileTypeIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'file_type',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'upload_time',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'KEYS_ONLY'
                },
                'BillingMode': 'PAY_PER_REQUEST'
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'TimeToLiveSpecification': {
            'AttributeName': 'ttl',
            'Enabled': True
        },
        'Tags': [
            {
                'Key': 'Project',
                'Value': 'HealthcareAI'
            },
            {
                'Key': 'Environment',
                'Value': 'Production'
            },
            {
                'Key': 'DataType',
                'Value': 'FileMetadata'
            },
            {
                'Key': 'Privacy',
                'Value': 'Sensitive'
            }
        ]
    }


def get_system_config_table_schema() -> Dict[str, Any]:
    """Get the schema for the SystemConfig table."""
    return {
        'TableName': 'HealthcareAI-SystemConfig',
        'KeySchema': [
            {
                'AttributeName': 'config_key',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        'AttributeDefinitions': [
            {
                'AttributeName': 'config_key',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'category',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'updated_at',
                'AttributeType': 'S'
            }
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'CategoryIndex',
                'KeySchema': [
                    {
                        'AttributeName': 'category',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'updated_at',
                        'KeyType': 'RANGE'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'BillingMode': 'PAY_PER_REQUEST'
            }
        ],
        'BillingMode': 'PAY_PER_REQUEST',
        'Tags': [
            {
                'Key': 'Project',
                'Value': 'HealthcareAI'
            },
            {
                'Key': 'Environment',
                'Value': 'Production'
            },
            {
                'Key': 'DataType',
                'Value': 'SystemConfig'
            }
        ]
    }


def get_all_table_schemas() -> List[Dict[str, Any]]:
    """Get all table schemas for the healthcare AI system."""
    return [
        get_conversations_table_schema(),
        get_users_table_schema(),
        get_conversation_summaries_table_schema(),
        get_file_metadata_table_schema(),
        get_system_config_table_schema()
    ]


def get_table_creation_order() -> List[str]:
    """Get the recommended order for creating tables (dependencies first)."""
    return [
        'HealthcareAI-Users',
        'HealthcareAI-SystemConfig',
        'HealthcareAI-ConversationSummaries',
        'HealthcareAI-Conversations',
        'HealthcareAI-FileMetadata'
    ]


def get_backup_configuration() -> Dict[str, Any]:
    """Get backup configuration for all tables."""
    return {
        'BackupPolicy': {
            'PointInTimeRecoveryEnabled': True
        },
        'ContinuousBackups': {
            'PointInTimeRecoveryDescription': {
                'PointInTimeRecoveryStatus': 'ENABLED'
            }
        },
        'BackupRetentionPeriod': 35,  # 35 days
        'BackupSchedule': {
            'DailyBackupTime': '03:00',  # 3 AM UTC
            'WeeklyBackupDay': 'SUNDAY',
            'MonthlyBackupDay': 1
        }
    }


def get_monitoring_configuration() -> Dict[str, Any]:
    """Get CloudWatch monitoring configuration for tables."""
    return {
        'MetricFilters': [
            {
                'MetricName': 'ConversationVolume',
                'FilterPattern': '[timestamp, request_id, "CONVERSATION_STORED"]',
                'MetricTransformation': {
                    'MetricNamespace': 'HealthcareAI/DynamoDB',
                    'MetricName': 'ConversationsStored',
                    'MetricValue': '1'
                }
            },
            {
                'MetricName': 'UserRegistrations',
                'FilterPattern': '[timestamp, request_id, "USER_CREATED"]',
                'MetricTransformation': {
                    'MetricNamespace': 'HealthcareAI/DynamoDB',
                    'MetricName': 'NewUsers',
                    'MetricValue': '1'
                }
            },
            {
                'MetricName': 'CriticalConversations',
                'FilterPattern': '[timestamp, request_id, "CRITICAL_CONVERSATION"]',
                'MetricTransformation': {
                    'MetricNamespace': 'HealthcareAI/DynamoDB',
                    'MetricName': 'CriticalConversations',
                    'MetricValue': '1'
                }
            }
        ],
        'Alarms': [
            {
                'AlarmName': 'HighConversationVolume',
                'MetricName': 'ConversationsStored',
                'Threshold': 1000,
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 2,
                'Period': 300,
                'Statistic': 'Sum'
            },
            {
                'AlarmName': 'CriticalConversationAlert',
                'MetricName': 'CriticalConversations',
                'Threshold': 1,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                'EvaluationPeriods': 1,
                'Period': 60,
                'Statistic': 'Sum'
            }
        ]
    }