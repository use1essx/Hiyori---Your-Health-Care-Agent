#!/usr/bin/env python3
"""
Healthcare AI V2 - Performance Monitoring for pgAdmin
Real-time database performance monitoring and alerting system
"""

import asyncio
import logging
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import settings
from src.database.connection import get_async_session
from src.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Real-time database performance monitoring for Healthcare AI V2
    """
    
    def __init__(self):
        self.alert_thresholds = {
            'cpu_usage_percent': 85,
            'memory_usage_percent': 90,
            'disk_usage_percent': 85,
            'connection_count': 180,  # Out of 200 max
            'slow_query_threshold_ms': 5000,
            'lock_wait_threshold_ms': 30000,
            'cache_hit_ratio_min': 0.95,
            'deadlock_count_threshold': 5
        }
        
        self.notification_settings = {
            'email_enabled': bool(settings.MAIL_SERVER if hasattr(settings, 'MAIL_SERVER') else False),
            'email_recipients': ['admin@healthcare-ai.com'],
            'slack_enabled': False,  # Configure if needed
            'slack_webhook': None
        }
        
        self.last_alert_times = {}  # To prevent spam
        self.alert_cooldown_minutes = 15
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive database performance statistics
        """
        try:
            async with get_async_session() as session:
                # Database size and basic stats
                db_stats_query = """
                SELECT 
                    pg_database_size(current_database()) as db_size_bytes,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                    (SELECT count(*) FROM pg_stat_activity) as total_connections,
                    (SELECT max_connections FROM pg_settings WHERE name = 'max_connections') as max_connections
                """
                
                result = await session.execute(db_stats_query)
                db_stats = dict(result.fetchone()._mapping)
                
                # Query performance stats (requires pg_stat_statements)
                query_stats_query = """
                SELECT 
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    max_exec_time,
                    stddev_exec_time,
                    rows
                FROM pg_stat_statements 
                WHERE calls > 10
                ORDER BY mean_exec_time DESC 
                LIMIT 10
                """
                
                try:
                    result = await session.execute(query_stats_query)
                    query_stats = [dict(row._mapping) for row in result.fetchall()]
                except Exception:
                    query_stats = []  # pg_stat_statements might not be enabled
                
                # Cache hit ratio
                cache_stats_query = """
                SELECT 
                    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
                FROM pg_statio_user_tables
                WHERE heap_blks_read > 0
                """
                
                result = await session.execute(cache_stats_query)
                cache_row = result.fetchone()
                cache_hit_ratio = float(cache_row[0]) if cache_row and cache_row[0] else 1.0
                
                # Lock statistics
                lock_stats_query = """
                SELECT 
                    mode,
                    count(*) as lock_count
                FROM pg_locks 
                WHERE granted = false
                GROUP BY mode
                """
                
                result = await session.execute(lock_stats_query)
                lock_stats = [dict(row._mapping) for row in result.fetchall()]
                
                # Table sizes and bloat
                table_stats_query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    n_live_tup,
                    n_dead_tup,
                    CASE 
                        WHEN n_live_tup > 0 
                        THEN round((n_dead_tup::float / n_live_tup::float) * 100, 2)
                        ELSE 0 
                    END as dead_tuple_percent
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
                """
                
                result = await session.execute(table_stats_query)
                table_stats = [dict(row._mapping) for row in result.fetchall()]
                
                # Recent activity
                activity_query = """
                SELECT 
                    state,
                    count(*) as connection_count,
                    max(extract(epoch from (now() - query_start))) as longest_query_seconds
                FROM pg_stat_activity 
                WHERE pid != pg_backend_pid()
                GROUP BY state
                """
                
                result = await session.execute(activity_query)
                activity_stats = [dict(row._mapping) for row in result.fetchall()]
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'database_stats': db_stats,
                    'query_performance': query_stats,
                    'cache_hit_ratio': cache_hit_ratio,
                    'lock_stats': lock_stats,
                    'table_stats': table_stats,
                    'activity_stats': activity_stats,
                    'status': 'healthy'
                }
                
        except Exception as e:
            logger.error(f"Error collecting database stats: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    async def check_slow_queries(self) -> List[Dict[str, Any]]:
        """
        Check for slow running queries
        """
        try:
            async with get_async_session() as session:
                slow_queries_query = """
                SELECT 
                    pid,
                    usename,
                    application_name,
                    client_addr,
                    state,
                    query_start,
                    extract(epoch from (now() - query_start)) as duration_seconds,
                    left(query, 200) as query_preview
                FROM pg_stat_activity 
                WHERE state = 'active' 
                AND pid != pg_backend_pid()
                AND extract(epoch from (now() - query_start)) > %s
                ORDER BY query_start ASC
                """
                
                result = await session.execute(
                    slow_queries_query, 
                    (self.alert_thresholds['slow_query_threshold_ms'] / 1000,)
                )
                
                slow_queries = []
                for row in result.fetchall():
                    slow_queries.append({
                        'pid': row.pid,
                        'username': row.usename,
                        'application': row.application_name,
                        'client_ip': str(row.client_addr) if row.client_addr else 'local',
                        'state': row.state,
                        'query_start': row.query_start.isoformat(),
                        'duration_seconds': float(row.duration_seconds),
                        'query_preview': row.query_preview
                    })
                
                return slow_queries
                
        except Exception as e:
            logger.error(f"Error checking slow queries: {e}")
            return []
    
    async def check_blocked_queries(self) -> List[Dict[str, Any]]:
        """
        Check for blocked/waiting queries
        """
        try:
            async with get_async_session() as session:
                blocked_queries_query = """
                SELECT 
                    blocked_locks.pid AS blocked_pid,
                    blocked_activity.usename AS blocked_user,
                    blocking_locks.pid AS blocking_pid,
                    blocking_activity.usename AS blocking_user,
                    blocked_activity.query AS blocked_statement,
                    blocking_activity.query AS current_statement_in_blocking_process,
                    blocked_activity.application_name AS blocked_application,
                    blocking_activity.application_name AS blocking_application
                FROM pg_catalog.pg_locks blocked_locks
                JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
                JOIN pg_catalog.pg_locks blocking_locks 
                    ON blocking_locks.locktype = blocked_locks.locktype
                    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
                    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
                    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
                    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
                    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
                    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
                    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
                    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
                    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
                    AND blocking_locks.pid != blocked_locks.pid
                JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
                WHERE NOT blocked_locks.granted
                """
                
                result = await session.execute(blocked_queries_query)
                blocked_queries = [dict(row._mapping) for row in result.fetchall()]
                
                return blocked_queries
                
        except Exception as e:
            logger.error(f"Error checking blocked queries: {e}")
            return []
    
    async def analyze_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze performance trends over specified time period
        """
        try:
            async with get_async_session() as session:
                # Healthcare AI specific metrics
                conversation_trends_query = """
                SELECT 
                    date_trunc('hour', created_at) as hour,
                    count(*) as conversation_count,
                    avg(processing_time_ms) as avg_processing_time,
                    max(processing_time_ms) as max_processing_time,
                    count(case when processing_time_ms > 5000 then 1 end) as slow_conversations
                FROM conversations 
                WHERE created_at > now() - interval '%s hours'
                GROUP BY date_trunc('hour', created_at)
                ORDER BY hour
                """
                
                result = await session.execute(conversation_trends_query, (hours,))
                conversation_trends = [dict(row._mapping) for row in result.fetchall()]
                
                # Agent performance trends
                agent_trends_query = """
                SELECT 
                    agent_type,
                    date_trunc('hour', created_at) as hour,
                    count(*) as conversation_count,
                    avg(agent_confidence) as avg_confidence,
                    avg(processing_time_ms) as avg_processing_time
                FROM conversations 
                WHERE created_at > now() - interval '%s hours'
                GROUP BY agent_type, date_trunc('hour', created_at)
                ORDER BY hour, agent_type
                """
                
                result = await session.execute(agent_trends_query, (hours,))
                agent_trends = [dict(row._mapping) for row in result.fetchall()]
                
                # Database growth trends
                growth_query = """
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                ORDER BY n_live_tup DESC
                """
                
                result = await session.execute(growth_query)
                growth_stats = [dict(row._mapping) for row in result.fetchall()]
                
                return {
                    'conversation_trends': conversation_trends,
                    'agent_trends': agent_trends,
                    'database_growth': growth_stats,
                    'analysis_period_hours': hours,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error analyzing performance trends: {e}")
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    async def check_health_status(self) -> Dict[str, Any]:
        """
        Comprehensive health check with alerts
        """
        try:
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'healthy',
                'alerts': [],
                'warnings': [],
                'metrics': {}
            }
            
            # Get basic stats
            db_stats = await self.get_database_stats()
            if 'error' in db_stats:
                health_status['overall_status'] = 'error'
                health_status['alerts'].append({
                    'type': 'database_error',
                    'message': f"Database connection error: {db_stats['error']}",
                    'severity': 'critical'
                })
                return health_status
            
            # Check connection count
            connection_usage = (
                db_stats['database_stats']['total_connections'] / 
                db_stats['database_stats']['max_connections']
            ) * 100
            
            if connection_usage > self.alert_thresholds['connection_count']:
                health_status['alerts'].append({
                    'type': 'high_connection_usage',
                    'message': f"High connection usage: {connection_usage:.1f}%",
                    'severity': 'warning',
                    'value': connection_usage,
                    'threshold': self.alert_thresholds['connection_count']
                })
            
            # Check cache hit ratio
            if db_stats['cache_hit_ratio'] < self.alert_thresholds['cache_hit_ratio_min']:
                health_status['alerts'].append({
                    'type': 'low_cache_hit_ratio',
                    'message': f"Low cache hit ratio: {db_stats['cache_hit_ratio']:.3f}",
                    'severity': 'warning',
                    'value': db_stats['cache_hit_ratio'],
                    'threshold': self.alert_thresholds['cache_hit_ratio_min']
                })
            
            # Check slow queries
            slow_queries = await self.check_slow_queries()
            if slow_queries:
                health_status['alerts'].append({
                    'type': 'slow_queries',
                    'message': f"{len(slow_queries)} slow queries detected",
                    'severity': 'warning',
                    'count': len(slow_queries),
                    'queries': slow_queries[:3]  # Show first 3
                })
            
            # Check blocked queries
            blocked_queries = await self.check_blocked_queries()
            if blocked_queries:
                health_status['alerts'].append({
                    'type': 'blocked_queries',
                    'message': f"{len(blocked_queries)} blocked queries detected",
                    'severity': 'critical',
                    'count': len(blocked_queries),
                    'blocked_queries': blocked_queries
                })
            
            # Check table bloat
            for table in db_stats['table_stats']:
                if table['dead_tuple_percent'] > 20:
                    health_status['warnings'].append({
                        'type': 'table_bloat',
                        'message': f"Table {table['tablename']} has {table['dead_tuple_percent']}% dead tuples",
                        'table': table['tablename'],
                        'dead_percent': table['dead_tuple_percent']
                    })
            
            # Set overall status
            if health_status['alerts']:
                critical_alerts = [a for a in health_status['alerts'] if a['severity'] == 'critical']
                if critical_alerts:
                    health_status['overall_status'] = 'critical'
                else:
                    health_status['overall_status'] = 'warning'
            
            health_status['metrics'] = {
                'connection_usage_percent': connection_usage,
                'cache_hit_ratio': db_stats['cache_hit_ratio'],
                'slow_query_count': len(slow_queries),
                'blocked_query_count': len(blocked_queries),
                'database_size_mb': round(db_stats['database_stats']['db_size_bytes'] / (1024 * 1024), 2)
            }
            
            # Send alerts if needed
            if health_status['alerts']:
                await self._send_alerts(health_status['alerts'])
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'error',
                'error': str(e)
            }
    
    async def generate_performance_report(self) -> str:
        """
        Generate comprehensive performance report for pgAdmin
        """
        try:
            # Get current stats
            db_stats = await self.get_database_stats()
            health_status = await self.check_health_status()
            trends = await self.analyze_performance_trends(24)
            
            report = f"""
# Healthcare AI V2 - Database Performance Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Health Status: {health_status.get('overall_status', 'unknown').upper()}

### Key Metrics
- Database Size: {health_status.get('metrics', {}).get('database_size_mb', 0)} MB
- Connection Usage: {health_status.get('metrics', {}).get('connection_usage_percent', 0):.1f}%
- Cache Hit Ratio: {health_status.get('metrics', {}).get('cache_hit_ratio', 0):.3f}
- Slow Queries: {health_status.get('metrics', {}).get('slow_query_count', 0)}
- Blocked Queries: {health_status.get('metrics', {}).get('blocked_query_count', 0)}

### Alerts ({len(health_status.get('alerts', []))})
"""
            
            for alert in health_status.get('alerts', []):
                report += f"- **{alert['severity'].upper()}**: {alert['message']}\n"
            
            report += f"""
### Warnings ({len(health_status.get('warnings', []))})
"""
            
            for warning in health_status.get('warnings', []):
                report += f"- {warning['message']}\n"
            
            if 'conversation_trends' in trends:
                total_conversations = sum(t['conversation_count'] for t in trends['conversation_trends'])
                avg_processing = sum(t['avg_processing_time'] for t in trends['conversation_trends']) / len(trends['conversation_trends'])
                
                report += f"""
### Healthcare AI Performance (24h)
- Total Conversations: {total_conversations}
- Average Processing Time: {avg_processing:.1f}ms
- Performance Trend: {'📈 Improving' if avg_processing < 2000 else '📉 Needs Attention'}
"""
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return f"Error generating report: {e}"
    
    async def _send_alerts(self, alerts: List[Dict[str, Any]]):
        """
        Send alerts via configured notification methods
        """
        try:
            # Check cooldown to prevent spam
            now = datetime.now()
            alert_key = f"general_alerts_{now.strftime('%Y-%m-%d_%H')}"
            
            if alert_key in self.last_alert_times:
                time_diff = now - self.last_alert_times[alert_key]
                if time_diff.total_seconds() < (self.alert_cooldown_minutes * 60):
                    return  # Skip sending due to cooldown
            
            # Send email alerts
            if self.notification_settings['email_enabled']:
                await self._send_email_alert(alerts)
            
            # Update last alert time
            self.last_alert_times[alert_key] = now
            
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
    
    async def _send_email_alert(self, alerts: List[Dict[str, Any]]):
        """
        Send email alert notification
        """
        try:
            if not hasattr(settings, 'MAIL_SERVER'):
                return
            
            # Create email content
            subject = f"Healthcare AI V2 - Database Alert ({len(alerts)} issues)"
            
            body = f"""
Healthcare AI V2 Database Alert

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Number of Issues: {len(alerts)}

Alerts:
"""
            
            for alert in alerts:
                body += f"- {alert['severity'].upper()}: {alert['message']}\n"
            
            body += f"""

Please check the pgAdmin dashboard for more details.
Healthcare AI V2 Monitoring System
"""
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = getattr(settings, 'MAIL_USERNAME', 'admin@healthcare-ai.com')
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send to all recipients
            for recipient in self.notification_settings['email_recipients']:
                msg['To'] = recipient
                
                with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                    if getattr(settings, 'MAIL_USE_TLS', False):
                        server.starttls()
                    if hasattr(settings, 'MAIL_USERNAME'):
                        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                    server.send_message(msg)
            
            logger.info(f"Alert email sent to {len(self.notification_settings['email_recipients'])} recipients")
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")


# CLI interface
async def main():
    """Main CLI function for performance monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Healthcare AI V2 Performance Monitor")
    parser.add_argument("action", choices=["stats", "health", "trends", "report", "monitor"])
    parser.add_argument("--hours", type=int, default=24, help="Hours for trend analysis")
    parser.add_argument("--continuous", action="store_true", help="Continuous monitoring mode")
    parser.add_argument("--interval", type=int, default=300, help="Monitoring interval in seconds")
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor()
    
    if args.action == "stats":
        stats = await monitor.get_database_stats()
        print(json.dumps(stats, indent=2, default=str))
    
    elif args.action == "health":
        health = await monitor.check_health_status()
        print(json.dumps(health, indent=2, default=str))
    
    elif args.action == "trends":
        trends = await monitor.analyze_performance_trends(args.hours)
        print(json.dumps(trends, indent=2, default=str))
    
    elif args.action == "report":
        report = await monitor.generate_performance_report()
        print(report)
    
    elif args.action == "monitor":
        if args.continuous:
            logger.info(f"Starting continuous monitoring (interval: {args.interval}s)")
            while True:
                health = await monitor.check_health_status()
                logger.info(f"Health check: {health['overall_status']} - {len(health['alerts'])} alerts")
                await asyncio.sleep(args.interval)
        else:
            health = await monitor.check_health_status()
            print(json.dumps(health, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
