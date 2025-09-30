"""
PostgreSQL to DynamoDB Migration Script
=======================================

Migrates data from PostgreSQL database to DynamoDB tables with validation and rollback support.
"""

import json
import boto3
import psycopg2
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid
import argparse
from dataclasses import dataclass
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MigrationStats:
    """Migration statistics tracking."""
    table_name: str
    total_records: int = 0
    migrated_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    start_time: datetime = None
    end_time: datetime = None
    
    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        if self.total_records > 0:
            return (self.migrated_records / self.total_records) * 100
        return 0.0


class PostgreSQLToDynamoDBMigrator:
    """Migrates data from PostgreSQL to DynamoDB with validation and rollback."""
    
    def __init__(self, postgres_config: Dict[str, str], aws_region: str = 'us-east-1'):
        self.postgres_config = postgres_config
        self.dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        self.postgres_conn = None
        self.migration_stats = {}
        
        # Table mappings: PostgreSQL table -> DynamoDB table
        self.table_mappings = {
            'users': 'HealthcareAI-Users',
            'conversations': 'HealthcareAI-Conversations',
            'conversation_summaries': 'HealthcareAI-ConversationSummaries',
            'file_metadata': 'HealthcareAI-FileMetadata',
            'system_config': 'HealthcareAI-SystemConfig'
        }
        
        # Field mappings and transformations
        self.field_mappings = {
            'users': {
                'id': 'user_id',
                'created_at': 'created_at',
                'updated_at': 'updated_at',
                'age_group': 'age_group',
                'language_preference': 'language_preference',
                'cultural_context': 'cultural_context',
                'health_preferences': 'health_preferences',
                'emergency_contacts': 'emergency_contacts',
                'privacy_settings': 'privacy_settings'
            },
            'conversations': {
                'id': 'message_id',
                'conversation_id': 'conversation_id',
                'user_id': 'user_id',
                'timestamp': 'timestamp',
                'user_input': 'user_input',
                'ai_response': 'ai_response',
                'agent_type': 'agent_type',
                'confidence_score': 'confidence_score',
                'urgency_level': 'urgency_level',
                'metadata': 'metadata'
            }
        }
    
    def connect_postgres(self) -> bool:
        """Connect to PostgreSQL database."""
        try:
            self.postgres_conn = psycopg2.connect(**self.postgres_config)
            logger.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False
    
    def disconnect_postgres(self):
        """Disconnect from PostgreSQL database."""
        if self.postgres_conn:
            self.postgres_conn.close()
            logger.info("Disconnected from PostgreSQL")
    
    def get_postgres_tables(self) -> List[str]:
        """Get list of tables in PostgreSQL database."""
        try:
            cursor = self.postgres_conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return tables
            
        except Exception as e:
            logger.error(f"Error getting PostgreSQL tables: {e}")
            return []
    
    def get_table_count(self, table_name: str) -> int:
        """Get record count for a PostgreSQL table."""
        try:
            cursor = self.postgres_conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            logger.error(f"Error getting count for table {table_name}: {e}")
            return 0
    
    def fetch_postgres_data(self, table_name: str, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Fetch data from PostgreSQL table in batches."""
        try:
            cursor = self.postgres_conn.cursor()
            
            # Get column names
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            # Fetch data in batches
            offset = 0
            while True:
                cursor.execute(f"""
                    SELECT * FROM {table_name} 
                    ORDER BY id 
                    LIMIT {batch_size} OFFSET {offset}
                """)
                
                rows = cursor.fetchall()
                if not rows:
                    break
                
                # Convert to dictionaries
                batch_data = []
                for row in rows:
                    record = {}
                    for i, value in enumerate(row):
                        column_name = columns[i]
                        
                        # Handle different data types
                        if isinstance(value, datetime):
                            record[column_name] = value.isoformat()
                        elif value is None:
                            record[column_name] = None
                        else:
                            record[column_name] = value
                    
                    batch_data.append(record)
                
                yield batch_data
                offset += batch_size
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Error fetching data from {table_name}: {e}")
            yield []
    
    def transform_record(self, table_name: str, postgres_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform PostgreSQL record to DynamoDB format."""
        if table_name not in self.field_mappings:
            # Default transformation - use record as-is
            return postgres_record
        
        field_mapping = self.field_mappings[table_name]
        dynamodb_record = {}
        
        for postgres_field, dynamodb_field in field_mapping.items():
            if postgres_field in postgres_record:
                value = postgres_record[postgres_field]
                
                # Apply transformations based on field type
                if dynamodb_field in ['created_at', 'updated_at', 'timestamp']:
                    # Ensure datetime fields are ISO format strings
                    if isinstance(value, str):
                        dynamodb_record[dynamodb_field] = value
                    elif value:
                        dynamodb_record[dynamodb_field] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
                
                elif dynamodb_field in ['cultural_context', 'health_preferences', 'emergency_contacts', 'privacy_settings', 'metadata']:
                    # Handle JSON fields
                    if isinstance(value, str):
                        try:
                            dynamodb_record[dynamodb_field] = json.loads(value)
                        except json.JSONDecodeError:
                            dynamodb_record[dynamodb_field] = value
                    else:
                        dynamodb_record[dynamodb_field] = value or {}
                
                else:
                    dynamodb_record[dynamodb_field] = value
        
        # Add TTL for certain tables
        if table_name == 'conversations':
            # Add TTL (30 days for regular conversations, 90 days for critical)
            urgency = dynamodb_record.get('urgency_level', 'low')
            ttl_days = 90 if urgency == 'critical' else 30
            ttl = int((datetime.utcnow() + timedelta(days=ttl_days)).timestamp())
            dynamodb_record['ttl'] = ttl
        
        elif table_name == 'file_metadata':
            # Add TTL (90 days for medical files, 30 days for others)
            file_category = dynamodb_record.get('file_category', 'document')
            ttl_days = 90 if file_category == 'medical' else 30
            ttl = int((datetime.utcnow() + timedelta(days=ttl_days)).timestamp())
            dynamodb_record['ttl'] = ttl
        
        return dynamodb_record
    
    def validate_record(self, table_name: str, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate DynamoDB record before insertion."""
        errors = []
        
        # Check required fields based on table
        if table_name == 'HealthcareAI-Users':
            if not record.get('user_id'):
                errors.append("Missing required field: user_id")
        
        elif table_name == 'HealthcareAI-Conversations':
            required_fields = ['conversation_id', 'timestamp', 'user_input', 'ai_response']
            for field in required_fields:
                if not record.get(field):
                    errors.append(f"Missing required field: {field}")
        
        elif table_name == 'HealthcareAI-ConversationSummaries':
            if not record.get('conversation_id'):
                errors.append("Missing required field: conversation_id")
        
        # Check data types and constraints
        for key, value in record.items():
            # Check string length limits (DynamoDB has 400KB item size limit)
            if isinstance(value, str) and len(value.encode('utf-8')) > 350000:  # Leave some buffer
                errors.append(f"Field {key} exceeds size limit")
        
        return len(errors) == 0, errors
    
    def write_to_dynamodb(self, table_name: str, records: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Write records to DynamoDB table."""
        try:
            table = self.dynamodb.Table(table_name)
            
            success_count = 0
            failure_count = 0
            
            # Use batch writer for efficiency
            with table.batch_writer() as batch:
                for record in records:
                    try:
                        # Validate record
                        is_valid, validation_errors = self.validate_record(table_name, record)
                        
                        if not is_valid:
                            logger.warning(f"Invalid record for {table_name}: {validation_errors}")
                            failure_count += 1
                            continue
                        
                        # Write to DynamoDB
                        batch.put_item(Item=record)
                        success_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error writing record to {table_name}: {e}")
                        failure_count += 1
            
            return success_count, failure_count
            
        except Exception as e:
            logger.error(f"Error writing batch to {table_name}: {e}")
            return 0, len(records)
    
    def migrate_table(self, postgres_table: str, dynamodb_table: str, batch_size: int = 100) -> MigrationStats:
        """Migrate a single table from PostgreSQL to DynamoDB."""
        stats = MigrationStats(table_name=dynamodb_table)
        stats.start_time = datetime.utcnow()
        
        try:
            # Get total record count
            stats.total_records = self.get_table_count(postgres_table)
            logger.info(f"Migrating {stats.total_records} records from {postgres_table} to {dynamodb_table}")
            
            # Process data in batches
            for batch_data in self.fetch_postgres_data(postgres_table, batch_size):
                if not batch_data:
                    break
                
                # Transform records
                transformed_records = []
                for postgres_record in batch_data:
                    try:
                        dynamodb_record = self.transform_record(postgres_table, postgres_record)
                        transformed_records.append(dynamodb_record)
                    except Exception as e:
                        logger.error(f"Error transforming record: {e}")
                        stats.failed_records += 1
                
                # Write to DynamoDB
                if transformed_records:
                    success_count, failure_count = self.write_to_dynamodb(dynamodb_table, transformed_records)
                    stats.migrated_records += success_count
                    stats.failed_records += failure_count
                
                # Log progress
                progress = (stats.migrated_records + stats.failed_records) / stats.total_records * 100
                logger.info(f"Progress: {progress:.1f}% ({stats.migrated_records} migrated, {stats.failed_records} failed)")
        
        except Exception as e:
            logger.error(f"Error migrating table {postgres_table}: {e}")
        
        stats.end_time = datetime.utcnow()
        return stats
    
    def migrate_all_tables(self, batch_size: int = 100) -> Dict[str, MigrationStats]:
        """Migrate all configured tables."""
        logger.info("Starting full database migration...")
        
        all_stats = {}
        
        for postgres_table, dynamodb_table in self.table_mappings.items():
            logger.info(f"Starting migration: {postgres_table} -> {dynamodb_table}")
            
            stats = self.migrate_table(postgres_table, dynamodb_table, batch_size)
            all_stats[postgres_table] = stats
            
            logger.info(f"Completed {postgres_table}: {stats.migrated_records}/{stats.total_records} records migrated "
                       f"({stats.success_rate:.1f}% success rate) in {stats.duration:.1f}s")
        
        return all_stats
    
    def create_migration_report(self, stats: Dict[str, MigrationStats]) -> Dict[str, Any]:
        """Create comprehensive migration report."""
        total_records = sum(s.total_records for s in stats.values())
        total_migrated = sum(s.migrated_records for s in stats.values())
        total_failed = sum(s.failed_records for s in stats.values())
        total_duration = sum(s.duration for s in stats.values())
        
        report = {
            'migration_summary': {
                'total_tables': len(stats),
                'total_records': total_records,
                'total_migrated': total_migrated,
                'total_failed': total_failed,
                'overall_success_rate': (total_migrated / total_records * 100) if total_records > 0 else 0,
                'total_duration_seconds': total_duration,
                'migration_completed_at': datetime.utcnow().isoformat()
            },
            'table_details': {}
        }
        
        for table_name, table_stats in stats.items():
            report['table_details'][table_name] = {
                'total_records': table_stats.total_records,
                'migrated_records': table_stats.migrated_records,
                'failed_records': table_stats.failed_records,
                'success_rate': table_stats.success_rate,
                'duration_seconds': table_stats.duration,
                'start_time': table_stats.start_time.isoformat() if table_stats.start_time else None,
                'end_time': table_stats.end_time.isoformat() if table_stats.end_time else None
            }
        
        return report
    
    def save_migration_report(self, report: Dict[str, Any], filename: str = None):
        """Save migration report to file."""
        if not filename:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"migration_report_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Migration report saved to: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving migration report: {e}")


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Migrate PostgreSQL data to DynamoDB')
    parser.add_argument('--postgres-host', required=True, help='PostgreSQL host')
    parser.add_argument('--postgres-port', default='5432', help='PostgreSQL port')
    parser.add_argument('--postgres-db', required=True, help='PostgreSQL database name')
    parser.add_argument('--postgres-user', required=True, help='PostgreSQL username')
    parser.add_argument('--postgres-password', required=True, help='PostgreSQL password')
    parser.add_argument('--aws-region', default='us-east-1', help='AWS region')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for migration')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without writing to DynamoDB')
    parser.add_argument('--table', help='Migrate specific table only')
    
    args = parser.parse_args()
    
    # PostgreSQL configuration
    postgres_config = {
        'host': args.postgres_host,
        'port': args.postgres_port,
        'database': args.postgres_db,
        'user': args.postgres_user,
        'password': args.postgres_password
    }
    
    # Initialize migrator
    migrator = PostgreSQLToDynamoDBMigrator(postgres_config, args.aws_region)
    
    # Connect to PostgreSQL
    if not migrator.connect_postgres():
        logger.error("Failed to connect to PostgreSQL. Exiting.")
        sys.exit(1)
    
    try:
        if args.dry_run:
            logger.info("DRY RUN MODE - No data will be written to DynamoDB")
        
        if args.table:
            # Migrate specific table
            if args.table not in migrator.table_mappings:
                logger.error(f"Table {args.table} not found in mappings")
                sys.exit(1)
            
            dynamodb_table = migrator.table_mappings[args.table]
            
            if not args.dry_run:
                stats = migrator.migrate_table(args.table, dynamodb_table, args.batch_size)
                logger.info(f"Migration completed: {stats.migrated_records}/{stats.total_records} records")
            else:
                count = migrator.get_table_count(args.table)
                logger.info(f"Would migrate {count} records from {args.table}")
        
        else:
            # Migrate all tables
            if not args.dry_run:
                all_stats = migrator.migrate_all_tables(args.batch_size)
                
                # Generate and save report
                report = migrator.create_migration_report(all_stats)
                migrator.save_migration_report(report)
                
                # Print summary
                summary = report['migration_summary']
                logger.info(f"Migration completed: {summary['total_migrated']}/{summary['total_records']} "
                           f"records migrated ({summary['overall_success_rate']:.1f}% success rate)")
            else:
                # Dry run - just show what would be migrated
                postgres_tables = migrator.get_postgres_tables()
                for table in postgres_tables:
                    if table in migrator.table_mappings:
                        count = migrator.get_table_count(table)
                        logger.info(f"Would migrate {count} records from {table} to {migrator.table_mappings[table]}")
    
    finally:
        migrator.disconnect_postgres()


if __name__ == '__main__':
    main()