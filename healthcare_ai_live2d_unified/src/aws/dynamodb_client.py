"""
DynamoDB Data Access Layer
=========================

Comprehensive DynamoDB client with efficient query patterns, conversation management,
and user profile handling for the healthcare AI system.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# Import optimization system
try:
    from .lambda_optimizer import get_optimized_dynamodb_client, lambda_optimizer
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    # Fallback for when optimization is not available
    import boto3
    OPTIMIZATION_AVAILABLE = False

try:
    from boto3.dynamodb.conditions import Key, Attr
except ImportError:
    # Handle case where boto3 is not available during import
    Key = None
    Attr = None

logger = logging.getLogger(__name__)


class ConversationStatus(Enum):
    """Conversation status types."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FLAGGED = "flagged"


@dataclass
class ConversationMessage:
    """Individual conversation message."""
    message_id: str
    conversation_id: str
    timestamp: datetime
    user_input: str
    ai_response: str
    agent_type: str
    confidence_score: float
    urgency_level: str
    metadata: Dict[str, Any]


@dataclass
class UserProfile:
    """User profile information."""
    user_id: str
    age_group: str
    language_preference: str
    cultural_context: Dict[str, Any]
    health_preferences: Dict[str, Any]
    emergency_contacts: List[Dict[str, str]]
    created_at: datetime
    updated_at: datetime
    privacy_settings: Dict[str, Any]


@dataclass
class ConversationSummary:
    """Conversation summary for efficient retrieval."""
    conversation_id: str
    user_id: str
    agent_type: str
    status: ConversationStatus
    start_time: datetime
    last_activity: datetime
    message_count: int
    topics: List[str]
    urgency_level: str
    requires_followup: bool


class DynamoDBClient:
    """Main DynamoDB client with optimized query patterns."""
    
    def __init__(self, table_prefix: str = "HealthcareAI"):
        if OPTIMIZATION_AVAILABLE:
            self.dynamodb = get_optimized_dynamodb_client()
        else:
            import boto3
            self.dynamodb = boto3.resource('dynamodb')
        self.table_prefix = table_prefix
        
        # Initialize table references
        self.conversations_table = self.dynamodb.Table(f"{table_prefix}-Conversations")
        self.users_table = self.dynamodb.Table(f"{table_prefix}-Users")
        self.conversation_summaries_table = self.dynamodb.Table(f"{table_prefix}-ConversationSummaries")
        
        # Pagination settings
        self.default_page_size = 20
        self.max_page_size = 100
    
    # Conversation Management
    
    def store_conversation_message(self, message: ConversationMessage) -> bool:
        """Store a single conversation message with optimized structure."""
        try:
            # Calculate TTL (30 days for regular conversations, 90 days for emergencies)
            ttl_days = 90 if message.urgency_level == 'critical' else 30
            ttl = int((datetime.utcnow() + timedelta(days=ttl_days)).timestamp())
            
            item = {
                'conversation_id': message.conversation_id,
                'timestamp': message.timestamp.isoformat(),
                'message_id': message.message_id,
                'user_input': message.user_input,
                'ai_response': message.ai_response,
                'agent_type': message.agent_type,
                'confidence_score': message.confidence_score,
                'urgency_level': message.urgency_level,
                'metadata': message.metadata,
                'ttl': ttl
            }
            
            self.conversations_table.put_item(Item=item)
            
            # Update conversation summary
            self._update_conversation_summary(message)
            
            logger.info(f"Stored message {message.message_id} for conversation {message.conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing conversation message: {e}")
            return False
    
    def get_conversation_history(self, conversation_id: str, 
                               limit: int = None, 
                               last_evaluated_key: str = None) -> Tuple[List[ConversationMessage], Optional[str]]:
        """Get conversation history with pagination support."""
        try:
            limit = min(limit or self.default_page_size, self.max_page_size)
            
            query_params = {
                'KeyConditionExpression': Key('conversation_id').eq(conversation_id),
                'ScanIndexForward': False,  # Most recent first
                'Limit': limit
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = json.loads(last_evaluated_key)
            
            response = self.conversations_table.query(**query_params)
            
            messages = []
            for item in response.get('Items', []):
                message = ConversationMessage(
                    message_id=item['message_id'],
                    conversation_id=item['conversation_id'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    user_input=item['user_input'],
                    ai_response=item['ai_response'],
                    agent_type=item['agent_type'],
                    confidence_score=item['confidence_score'],
                    urgency_level=item['urgency_level'],
                    metadata=item.get('metadata', {})
                )
                messages.append(message)
            
            # Handle pagination
            next_key = None
            if 'LastEvaluatedKey' in response:
                next_key = json.dumps(response['LastEvaluatedKey'])
            
            return messages, next_key
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return [], None
    
    def search_conversations(self, user_id: str, 
                           agent_type: str = None,
                           status: ConversationStatus = None,
                           start_date: datetime = None,
                           end_date: datetime = None,
                           limit: int = None) -> List[ConversationSummary]:
        """Search conversations with multiple filters."""
        try:
            limit = min(limit or self.default_page_size, self.max_page_size)
            
            # Build filter expression
            filter_expressions = []
            expression_values = {}
            
            if agent_type:
                filter_expressions.append("agent_type = :agent_type")
                expression_values[':agent_type'] = agent_type
            
            if status:
                filter_expressions.append("#status = :status")
                expression_values[':status'] = status.value
            
            if start_date:
                filter_expressions.append("start_time >= :start_date")
                expression_values[':start_date'] = start_date.isoformat()
            
            if end_date:
                filter_expressions.append("start_time <= :end_date")
                expression_values[':end_date'] = end_date.isoformat()
            
            query_params = {
                'IndexName': 'UserIdIndex',
                'KeyConditionExpression': Key('user_id').eq(user_id),
                'ScanIndexForward': False,
                'Limit': limit
            }
            
            if filter_expressions:
                query_params['FilterExpression'] = ' AND '.join(filter_expressions)
                query_params['ExpressionAttributeValues'] = expression_values
                
                if status:  # Add expression attribute names for reserved keywords
                    query_params['ExpressionAttributeNames'] = {'#status': 'status'}
            
            response = self.conversation_summaries_table.query(**query_params)
            
            summaries = []
            for item in response.get('Items', []):
                summary = ConversationSummary(
                    conversation_id=item['conversation_id'],
                    user_id=item['user_id'],
                    agent_type=item['agent_type'],
                    status=ConversationStatus(item['status']),
                    start_time=datetime.fromisoformat(item['start_time']),
                    last_activity=datetime.fromisoformat(item['last_activity']),
                    message_count=item['message_count'],
                    topics=item.get('topics', []),
                    urgency_level=item['urgency_level'],
                    requires_followup=item.get('requires_followup', False)
                )
                summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            return []
    
    def _update_conversation_summary(self, message: ConversationMessage):
        """Update or create conversation summary."""
        try:
            # Extract topics from metadata
            topics = message.metadata.get('topics', [])
            if isinstance(topics, str):
                topics = [topics]
            
            # Update summary
            response = self.conversation_summaries_table.update_item(
                Key={'conversation_id': message.conversation_id},
                UpdateExpression="""
                    SET 
                        user_id = if_not_exists(user_id, :user_id),
                        agent_type = :agent_type,
                        #status = if_not_exists(#status, :status),
                        start_time = if_not_exists(start_time, :start_time),
                        last_activity = :last_activity,
                        message_count = if_not_exists(message_count, :zero) + :one,
                        topics = list_append(if_not_exists(topics, :empty_list), :topics),
                        urgency_level = :urgency_level,
                        requires_followup = :requires_followup
                """,
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':user_id': message.metadata.get('user_id', 'unknown'),
                    ':agent_type': message.agent_type,
                    ':status': ConversationStatus.ACTIVE.value,
                    ':start_time': message.timestamp.isoformat(),
                    ':last_activity': message.timestamp.isoformat(),
                    ':zero': 0,
                    ':one': 1,
                    ':empty_list': [],
                    ':topics': topics,
                    ':urgency_level': message.urgency_level,
                    ':requires_followup': message.metadata.get('requires_followup', False)
                },
                ReturnValues='UPDATED_NEW'
            )
            
        except Exception as e:
            logger.error(f"Error updating conversation summary: {e}")
    
    # User Profile Management
    
    def create_user_profile(self, profile: UserProfile) -> bool:
        """Create a new user profile."""
        try:
            item = asdict(profile)
            item['created_at'] = profile.created_at.isoformat()
            item['updated_at'] = profile.updated_at.isoformat()
            
            self.users_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(user_id)'
            )
            
            logger.info(f"Created user profile for {profile.user_id}")
            return True
            
        except self.users_table.meta.client.exceptions.ConditionalCheckFailedException:
            logger.warning(f"User profile already exists for {profile.user_id}")
            return False
        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID."""
        try:
            response = self.users_table.get_item(Key={'user_id': user_id})
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            profile = UserProfile(
                user_id=item['user_id'],
                age_group=item.get('age_group', 'adult'),
                language_preference=item.get('language_preference', 'zh'),
                cultural_context=item.get('cultural_context', {'region': 'hong_kong'}),
                health_preferences=item.get('health_preferences', {}),
                emergency_contacts=item.get('emergency_contacts', []),
                created_at=datetime.fromisoformat(item['created_at']),
                updated_at=datetime.fromisoformat(item['updated_at']),
                privacy_settings=item.get('privacy_settings', {})
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error retrieving user profile: {e}")
            return None
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile with partial updates."""
        try:
            # Build update expression
            update_expressions = []
            expression_values = {}
            expression_names = {}
            
            for key, value in updates.items():
                if key in ['created_at', 'user_id']:  # Skip immutable fields
                    continue
                
                if key in ['status', 'type']:  # Reserved keywords
                    expression_names[f'#{key}'] = key
                    update_expressions.append(f'#{key} = :{key}')
                else:
                    update_expressions.append(f'{key} = :{key}')
                
                expression_values[f':{key}'] = value
            
            # Always update the updated_at timestamp
            update_expressions.append('updated_at = :updated_at')
            expression_values[':updated_at'] = datetime.utcnow().isoformat()
            
            update_params = {
                'Key': {'user_id': user_id},
                'UpdateExpression': 'SET ' + ', '.join(update_expressions),
                'ExpressionAttributeValues': expression_values,
                'ReturnValues': 'UPDATED_NEW'
            }
            
            if expression_names:
                update_params['ExpressionAttributeNames'] = expression_names
            
            self.users_table.update_item(**update_params)
            
            logger.info(f"Updated user profile for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False
    
    def delete_user_data(self, user_id: str) -> bool:
        """Delete all user data (GDPR compliance)."""
        try:
            # Delete user profile
            self.users_table.delete_item(Key={'user_id': user_id})
            
            # Find and delete all conversations
            summaries = self.search_conversations(user_id)
            
            for summary in summaries:
                # Delete conversation messages
                messages, _ = self.get_conversation_history(summary.conversation_id, limit=1000)
                
                with self.conversations_table.batch_writer() as batch:
                    for message in messages:
                        batch.delete_item(
                            Key={
                                'conversation_id': message.conversation_id,
                                'timestamp': message.timestamp.isoformat()
                            }
                        )
                
                # Delete conversation summary
                self.conversation_summaries_table.delete_item(
                    Key={'conversation_id': summary.conversation_id}
                )
            
            logger.info(f"Deleted all data for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user data: {e}")
            return False
    
    # Analytics and Reporting
    
    def get_conversation_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get conversation analytics for specified date range."""
        try:
            # Scan conversation summaries for the date range
            filter_expression = Attr('start_time').between(
                start_date.isoformat(),
                end_date.isoformat()
            )
            
            response = self.conversation_summaries_table.scan(
                FilterExpression=filter_expression
            )
            
            summaries = response.get('Items', [])
            
            # Calculate analytics
            total_conversations = len(summaries)
            agent_distribution = {}
            urgency_distribution = {}
            avg_messages_per_conversation = 0
            
            for summary in summaries:
                agent_type = summary.get('agent_type', 'unknown')
                agent_distribution[agent_type] = agent_distribution.get(agent_type, 0) + 1
                
                urgency = summary.get('urgency_level', 'low')
                urgency_distribution[urgency] = urgency_distribution.get(urgency, 0) + 1
                
                avg_messages_per_conversation += summary.get('message_count', 0)
            
            if total_conversations > 0:
                avg_messages_per_conversation /= total_conversations
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_conversations': total_conversations,
                'agent_distribution': agent_distribution,
                'urgency_distribution': urgency_distribution,
                'average_messages_per_conversation': round(avg_messages_per_conversation, 2),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating conversation analytics: {e}")
            return {}
    
    def get_user_engagement_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get engagement metrics for a specific user."""
        try:
            summaries = self.search_conversations(user_id, limit=100)
            
            if not summaries:
                return {'user_id': user_id, 'no_data': True}
            
            # Calculate metrics
            total_conversations = len(summaries)
            total_messages = sum(s.message_count for s in summaries)
            
            # Agent preferences
            agent_usage = {}
            for summary in summaries:
                agent = summary.agent_type
                agent_usage[agent] = agent_usage.get(agent, 0) + 1
            
            # Activity timeline
            first_conversation = min(s.start_time for s in summaries)
            last_conversation = max(s.last_activity for s in summaries)
            
            # Urgency patterns
            urgency_counts = {}
            for summary in summaries:
                urgency = summary.urgency_level
                urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
            
            return {
                'user_id': user_id,
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'average_messages_per_conversation': round(total_messages / total_conversations, 2),
                'agent_preferences': agent_usage,
                'activity_period': {
                    'first_conversation': first_conversation.isoformat(),
                    'last_conversation': last_conversation.isoformat(),
                    'days_active': (last_conversation - first_conversation).days + 1
                },
                'urgency_patterns': urgency_counts,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating user engagement metrics: {e}")
            return {'user_id': user_id, 'error': str(e)}
    
    # Health and Maintenance
    
    def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired data (manual cleanup for testing)."""
        try:
            current_time = int(datetime.utcnow().timestamp())
            cleanup_stats = {'conversations_deleted': 0, 'summaries_deleted': 0}
            
            # Scan for expired conversations
            response = self.conversations_table.scan(
                FilterExpression=Attr('ttl').lt(current_time),
                ProjectionExpression='conversation_id, #ts',
                ExpressionAttributeNames={'#ts': 'timestamp'}
            )
            
            # Delete expired conversations
            with self.conversations_table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(
                        Key={
                            'conversation_id': item['conversation_id'],
                            'timestamp': item['timestamp']
                        }
                    )
                    cleanup_stats['conversations_deleted'] += 1
            
            logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on DynamoDB tables."""
        try:
            health_status = {
                'timestamp': datetime.utcnow().isoformat(),
                'tables': {}
            }
            
            tables = [
                ('conversations', self.conversations_table),
                ('users', self.users_table),
                ('conversation_summaries', self.conversation_summaries_table)
            ]
            
            for table_name, table in tables:
                try:
                    # Test table accessibility
                    table.load()
                    
                    # Get table status
                    status = table.table_status
                    item_count = table.item_count
                    
                    health_status['tables'][table_name] = {
                        'status': status,
                        'item_count': item_count,
                        'accessible': True
                    }
                    
                except Exception as e:
                    health_status['tables'][table_name] = {
                        'status': 'error',
                        'error': str(e),
                        'accessible': False
                    }
            
            # Overall health
            all_healthy = all(
                table_info.get('accessible', False) 
                for table_info in health_status['tables'].values()
            )
            health_status['overall_status'] = 'healthy' if all_healthy else 'degraded'
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_status': 'error',
                'error': str(e)
            }


# Convenience functions for common operations

def create_conversation_message(conversation_id: str, user_input: str, ai_response: str,
                              agent_type: str, confidence_score: float, urgency_level: str,
                              metadata: Dict[str, Any] = None) -> ConversationMessage:
    """Create a ConversationMessage object with generated ID and timestamp."""
    return ConversationMessage(
        message_id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        timestamp=datetime.utcnow(),
        user_input=user_input,
        ai_response=ai_response,
        agent_type=agent_type,
        confidence_score=confidence_score,
        urgency_level=urgency_level,
        metadata=metadata or {}
    )


def create_user_profile(user_id: str, age_group: str = 'adult', 
                       language_preference: str = 'zh',
                       cultural_context: Dict[str, Any] = None) -> UserProfile:
    """Create a UserProfile object with default values."""
    now = datetime.utcnow()
    
    return UserProfile(
        user_id=user_id,
        age_group=age_group,
        language_preference=language_preference,
        cultural_context=cultural_context or {'region': 'hong_kong'},
        health_preferences={},
        emergency_contacts=[],
        created_at=now,
        updated_at=now,
        privacy_settings={'data_retention_days': 30}
    )


# Global client instance
dynamodb_client = DynamoDBClient()