#!/usr/bin/env python3
"""
Healthcare AI V2 - Security Setup and Policy Enforcement for pgAdmin
Implements healthcare-grade security policies and user role management
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import settings
from src.database.connection import get_async_session
from src.core.logging import setup_logging
from src.core.security import get_password_hash

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


class SecurityPolicyManager:
    """
    Manages security policies and user access controls for Healthcare AI V2 database
    """
    
    def __init__(self):
        self.security_policies = {
            'password_policy': {
                'min_length': 12,
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special_chars': True,
                'max_age_days': 90,
                'history_count': 5  # Cannot reuse last 5 passwords
            },
            'access_control': {
                'max_login_attempts': 5,
                'lockout_duration_minutes': 30,
                'session_timeout_minutes': 480,  # 8 hours
                'require_2fa_for_admins': False,  # Can be enabled later
                'ip_whitelist_enabled': False,
                'allowed_ip_ranges': []
            },
            'audit_requirements': {
                'log_all_queries': True,
                'log_data_access': True,
                'log_schema_changes': True,
                'log_user_actions': True,
                'retention_days': 365
            },
            'data_protection': {
                'encrypt_sensitive_data': True,
                'mask_pii_in_logs': True,
                'require_approval_for_exports': True,
                'max_export_rows': 10000
            }
        }
        
        self.sensitive_tables = [
            'users',
            'conversations',
            'uploaded_documents', 
            'audit_logs',
            'user_sessions'
        ]
        
        self.role_permissions = {
            'healthcare_admin': {
                'can_manage_users': True,
                'can_backup_restore': True,
                'can_view_audit_logs': True,
                'can_modify_security': True,
                'can_export_data': True,
                'can_access_pgadmin': True,
                'table_access': 'all'
            },
            'medical_reviewer': {
                'can_manage_users': False,
                'can_backup_restore': False,
                'can_view_audit_logs': True,
                'can_modify_security': False,
                'can_export_data': True,
                'can_access_pgladmin': True,
                'table_access': ['conversations', 'uploaded_documents', 'hk_healthcare_data']
            },
            'data_manager': {
                'can_manage_users': False,
                'can_backup_restore': True,
                'can_view_audit_logs': False,
                'can_modify_security': False,
                'can_export_data': True,
                'can_access_pgadmin': True,
                'table_access': ['hk_healthcare_data', 'uploaded_documents']
            },
            'readonly_user': {
                'can_manage_users': False,
                'can_backup_restore': False,
                'can_view_audit_logs': False,
                'can_modify_security': False,
                'can_export_data': False,
                'can_access_pgadmin': True,
                'table_access': ['hk_healthcare_data']
            }
        }
    
    async def setup_database_security(self) -> Dict[str, Any]:
        """
        Set up comprehensive database security policies
        """
        try:
            results = {
                'security_setup': 'started',
                'policies_applied': [],
                'roles_created': [],
                'errors': []
            }
            
            async with get_async_session() as session:
                # 1. Create security roles
                roles_result = await self._create_security_roles(session)
                results['roles_created'] = roles_result
                
                # 2. Set up row-level security
                rls_result = await self._setup_row_level_security(session)
                results['policies_applied'].extend(rls_result)
                
                # 3. Create audit triggers
                audit_result = await self._setup_audit_triggers(session)
                results['policies_applied'].extend(audit_result)
                
                # 4. Configure security views
                views_result = await self._create_security_views(session)
                results['policies_applied'].extend(views_result)
                
                # 5. Set up password policies
                password_result = await self._setup_password_policies(session)
                results['policies_applied'].extend(password_result)
                
                await session.commit()
                
            results['security_setup'] = 'completed'
            logger.info("Database security setup completed successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"Error setting up database security: {e}")
            return {
                'security_setup': 'failed',
                'error': str(e)
            }
    
    async def _create_security_roles(self, session) -> List[str]:
        """
        Create database roles for different access levels
        """
        created_roles = []
        
        try:
            # Create roles with specific permissions
            role_definitions = {
                'healthcare_admin_role': [
                    'CREATE ROLE healthcare_admin_role',
                    'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO healthcare_admin_role',
                    'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO healthcare_admin_role',
                    'GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO healthcare_admin_role'
                ],
                'medical_reviewer_role': [
                    'CREATE ROLE medical_reviewer_role',
                    'GRANT SELECT, INSERT, UPDATE ON conversations TO medical_reviewer_role',
                    'GRANT SELECT, INSERT, UPDATE ON uploaded_documents TO medical_reviewer_role',
                    'GRANT SELECT ON hk_healthcare_data TO medical_reviewer_role',
                    'GRANT SELECT ON audit_logs TO medical_reviewer_role'
                ],
                'data_manager_role': [
                    'CREATE ROLE data_manager_role',
                    'GRANT SELECT, INSERT, UPDATE, DELETE ON hk_healthcare_data TO data_manager_role',
                    'GRANT SELECT, INSERT, UPDATE ON uploaded_documents TO data_manager_role'
                ],
                'readonly_role': [
                    'CREATE ROLE readonly_role',
                    'GRANT SELECT ON hk_healthcare_data TO readonly_role'
                ]
            }
            
            for role_name, commands in role_definitions.items():
                try:
                    for command in commands:
                        await session.execute(command)
                    created_roles.append(role_name)
                    logger.info(f"Created security role: {role_name}")
                except Exception as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Error creating role {role_name}: {e}")
            
            return created_roles
            
        except Exception as e:
            logger.error(f"Error creating security roles: {e}")
            return []
    
    async def _setup_row_level_security(self, session) -> List[str]:
        """
        Set up row-level security policies for sensitive tables
        """
        policies_applied = []
        
        try:
            # Enable RLS on sensitive tables
            for table in self.sensitive_tables:
                try:
                    # Enable RLS
                    await session.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
                    policies_applied.append(f'RLS enabled on {table}')
                    
                    # Create policy for admins (full access)
                    policy_name = f'{table}_admin_policy'
                    await session.execute(f'''
                        CREATE POLICY {policy_name} ON {table}
                        FOR ALL TO healthcare_admin_role
                        USING (true)
                        WITH CHECK (true)
                    ''')
                    policies_applied.append(f'Admin policy created for {table}')
                    
                    # Create policy for medical reviewers (limited access)
                    if table in ['conversations', 'uploaded_documents']:
                        policy_name = f'{table}_medical_policy'
                        await session.execute(f'''
                            CREATE POLICY {policy_name} ON {table}
                            FOR SELECT TO medical_reviewer_role
                            USING (true)
                        ''')
                        policies_applied.append(f'Medical reviewer policy created for {table}')
                    
                except Exception as e:
                        if "already exists" not in str(e):
                            logger.warning(f"Error setting up RLS for {table}: {e}")
            
            return policies_applied
            
        except Exception as e:
            logger.error(f"Error setting up row-level security: {e}")
            return []
    
    async def _setup_audit_triggers(self, session) -> List[str]:
        """
        Set up audit triggers for tracking all database changes
        """
        audit_setup = []
        
        try:
            # Create audit function
            audit_function = '''
            CREATE OR REPLACE FUNCTION audit_trigger_function()
            RETURNS TRIGGER AS $$
            BEGIN
                INSERT INTO audit_logs (
                    event_type,
                    table_name,
                    record_id,
                    old_values,
                    new_values,
                    user_email,
                    ip_address,
                    created_at
                ) VALUES (
                    TG_OP,
                    TG_TABLE_NAME,
                    COALESCE(NEW.id, OLD.id),
                    CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
                    CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
                    current_setting('application_name', true),
                    inet_client_addr(),
                    now()
                );
                
                RETURN COALESCE(NEW, OLD);
            END;
            $$ LANGUAGE plpgsql;
            '''
            
            await session.execute(audit_function)
            audit_setup.append('Audit trigger function created')
            
            # Create triggers on sensitive tables
            for table in self.sensitive_tables:
                if table != 'audit_logs':  # Don't audit the audit table itself
                    trigger_name = f'{table}_audit_trigger'
                    trigger_sql = f'''
                    DROP TRIGGER IF EXISTS {trigger_name} ON {table};
                    CREATE TRIGGER {trigger_name}
                        AFTER INSERT OR UPDATE OR DELETE ON {table}
                        FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
                    '''
                    
                    await session.execute(trigger_sql)
                    audit_setup.append(f'Audit trigger created for {table}')
            
            return audit_setup
            
        except Exception as e:
            logger.error(f"Error setting up audit triggers: {e}")
            return []
    
    async def _create_security_views(self, session) -> List[str]:
        """
        Create security monitoring views for pgAdmin
        """
        views_created = []
        
        try:
            # Security overview view
            security_overview_view = '''
            CREATE OR REPLACE VIEW security_overview AS
            SELECT 
                'Database Security' as category,
                'Active Users' as metric,
                count(*) as value
            FROM users WHERE is_active = true
            UNION ALL
            SELECT 
                'Database Security',
                'Admin Users',
                count(*)
            FROM users WHERE is_admin = true AND is_active = true
            UNION ALL
            SELECT 
                'Database Security',
                'Failed Logins (24h)',
                count(*)
            FROM audit_logs 
            WHERE event_type = 'login_failure' 
            AND created_at > now() - interval '24 hours'
            UNION ALL
            SELECT 
                'Database Security',
                'Locked Accounts',
                count(*)
            FROM users 
            WHERE account_locked_until > now()
            '''
            
            await session.execute(security_overview_view)
            views_created.append('security_overview view')
            
            # User activity monitoring view
            user_activity_view = '''
            CREATE OR REPLACE VIEW user_activity_monitor AS
            SELECT 
                u.email,
                u.role,
                u.last_login,
                u.failed_login_attempts,
                u.account_locked_until,
                COUNT(al.id) as recent_actions,
                MAX(al.created_at) as last_action
            FROM users u
            LEFT JOIN audit_logs al ON al.user_email = u.email 
                AND al.created_at > now() - interval '24 hours'
            WHERE u.is_active = true
            GROUP BY u.id, u.email, u.role, u.last_login, u.failed_login_attempts, u.account_locked_until
            ORDER BY u.last_login DESC
            '''
            
            await session.execute(user_activity_view)
            views_created.append('user_activity_monitor view')
            
            # Data access monitoring view
            data_access_view = '''
            CREATE OR REPLACE VIEW data_access_monitor AS
            SELECT 
                table_name,
                event_type,
                user_email,
                ip_address,
                created_at,
                CASE 
                    WHEN table_name IN ('users', 'conversations') THEN 'High Sensitivity'
                    WHEN table_name IN ('uploaded_documents', 'audit_logs') THEN 'Medium Sensitivity'
                    ELSE 'Low Sensitivity'
                END as sensitivity_level
            FROM audit_logs 
            WHERE created_at > now() - interval '24 hours'
            AND table_name IS NOT NULL
            ORDER BY created_at DESC
            '''
            
            await session.execute(data_access_view)
            views_created.append('data_access_monitor view')
            
            return views_created
            
        except Exception as e:
            logger.error(f"Error creating security views: {e}")
            return []
    
    async def _setup_password_policies(self, session) -> List[str]:
        """
        Set up password policies and constraints
        """
        policies_setup = []
        
        try:
            # Create password history table
            password_history_table = '''
            CREATE TABLE IF NOT EXISTS password_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            '''
            
            await session.execute(password_history_table)
            policies_setup.append('Password history table created')
            
            # Create password validation function
            password_validation_function = '''
            CREATE OR REPLACE FUNCTION validate_password_policy(
                user_id_param INTEGER,
                new_password_hash VARCHAR(255)
            ) RETURNS BOOLEAN AS $$
            DECLARE
                history_count INTEGER;
            BEGIN
                -- Check password history (prevent reuse of last 5 passwords)
                SELECT COUNT(*) INTO history_count
                FROM password_history 
                WHERE user_id = user_id_param 
                AND password_hash = new_password_hash
                AND created_at > NOW() - INTERVAL '90 days'
                ORDER BY created_at DESC 
                LIMIT 5;
                
                IF history_count > 0 THEN
                    RAISE EXCEPTION 'Password has been used recently and cannot be reused';
                END IF;
                
                RETURN TRUE;
            END;
            $$ LANGUAGE plpgsql;
            '''
            
            await session.execute(password_validation_function)
            policies_setup.append('Password validation function created')
            
            # Create trigger for password changes
            password_trigger = '''
            CREATE OR REPLACE FUNCTION password_change_trigger()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Only execute if password actually changed
                IF OLD.hashed_password != NEW.hashed_password THEN
                    -- Validate password policy
                    PERFORM validate_password_policy(NEW.id, NEW.hashed_password);
                    
                    -- Store old password in history
                    INSERT INTO password_history (user_id, password_hash)
                    VALUES (OLD.id, OLD.hashed_password);
                    
                    -- Clean up old password history (keep only last 10)
                    DELETE FROM password_history 
                    WHERE user_id = NEW.id 
                    AND id NOT IN (
                        SELECT id FROM password_history 
                        WHERE user_id = NEW.id 
                        ORDER BY created_at DESC 
                        LIMIT 10
                    );
                END IF;
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            DROP TRIGGER IF EXISTS password_change_trigger ON users;
            CREATE TRIGGER password_change_trigger
                BEFORE UPDATE ON users
                FOR EACH ROW EXECUTE FUNCTION password_change_trigger();
            '''
            
            await session.execute(password_trigger)
            policies_setup.append('Password change trigger created')
            
            return policies_setup
            
        except Exception as e:
            logger.error(f"Error setting up password policies: {e}")
            return []
    
    async def create_security_user(
        self, 
        email: str, 
        username: str, 
        password: str, 
        role: str,
        full_name: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new user with proper security validation
        """
        try:
            # Validate role
            if role not in self.role_permissions:
                return {
                    'success': False,
                    'error': f'Invalid role: {role}. Must be one of: {list(self.role_permissions.keys())}'
                }
            
            # Validate password policy
            password_validation = self._validate_password(password)
            if not password_validation['valid']:
                return {
                    'success': False,
                    'error': f'Password policy violation: {password_validation["error"]}'
                }
            
            async with get_async_session() as session:
                # Check if user already exists
                existing_user = await session.execute(
                    'SELECT id FROM users WHERE email = %s OR username = %s',
                    (email, username)
                )
                
                if existing_user.fetchone():
                    return {
                        'success': False,
                        'error': 'User with this email or username already exists'
                    }
                
                # Hash password
                hashed_password = get_password_hash(password)
                
                # Determine admin status based on role
                is_admin = role in ['healthcare_admin']
                
                # Create user
                user_insert = '''
                INSERT INTO users (
                    email, username, hashed_password, full_name, 
                    is_active, is_admin, role, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                '''
                
                result = await session.execute(
                    user_insert,
                    (email, username, hashed_password, full_name, True, is_admin, role, datetime.now())
                )
                
                user_id = result.fetchone()[0]
                
                # Grant database role
                db_role = f'{role}_role'
                try:
                    await session.execute(f'GRANT {db_role} TO {username}')
                except Exception as e:
                    logger.warning(f'Could not grant database role {db_role} to {username}: {e}')
                
                await session.commit()
                
                logger.info(f'Created security user: {email} with role {role}')
                
                return {
                    'success': True,
                    'user_id': user_id,
                    'email': email,
                    'role': role,
                    'permissions': self.role_permissions[role]
                }
                
        except Exception as e:
            logger.error(f'Error creating security user: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    async def audit_security_compliance(self) -> Dict[str, Any]:
        """
        Audit current security compliance status
        """
        try:
            compliance_report = {
                'audit_timestamp': datetime.now().isoformat(),
                'overall_compliance': 'unknown',
                'security_checks': {},
                'recommendations': [],
                'critical_issues': [],
                'warnings': []
            }
            
            async with get_async_session() as session:
                # Check password ages
                password_check = await session.execute('''
                    SELECT 
                        email,
                        role,
                        updated_at,
                        EXTRACT(days FROM (now() - updated_at)) as password_age_days
                    FROM users 
                    WHERE is_active = true
                    AND EXTRACT(days FROM (now() - updated_at)) > 90
                ''')
                
                old_passwords = password_check.fetchall()
                compliance_report['security_checks']['expired_passwords'] = len(old_passwords)
                
                if old_passwords:
                    compliance_report['warnings'].append({
                        'type': 'password_expiry',
                        'message': f'{len(old_passwords)} users have passwords older than 90 days',
                        'users': [{'email': row.email, 'age_days': int(row.password_age_days)} for row in old_passwords]
                    })
                
                # Check for admin accounts without recent activity
                inactive_admins = await session.execute('''
                    SELECT email, last_login
                    FROM users 
                    WHERE is_admin = true 
                    AND is_active = true
                    AND (last_login IS NULL OR last_login < now() - interval '30 days')
                ''')
                
                inactive_admin_list = inactive_admins.fetchall()
                compliance_report['security_checks']['inactive_admin_accounts'] = len(inactive_admin_list)
                
                if inactive_admin_list:
                    compliance_report['warnings'].append({
                        'type': 'inactive_admins',
                        'message': f'{len(inactive_admin_list)} admin accounts have not logged in recently',
                        'accounts': [{'email': row.email, 'last_login': row.last_login.isoformat() if row.last_login else None} for row in inactive_admin_list]
                    })
                
                # Check for failed login attempts
                failed_logins = await session.execute('''
                    SELECT 
                        user_email,
                        ip_address,
                        COUNT(*) as attempts
                    FROM audit_logs 
                    WHERE event_type = 'login_failure'
                    AND created_at > now() - interval '24 hours'
                    GROUP BY user_email, ip_address
                    HAVING COUNT(*) > 10
                ''')
                
                suspicious_activity = failed_logins.fetchall()
                compliance_report['security_checks']['suspicious_login_attempts'] = len(suspicious_activity)
                
                if suspicious_activity:
                    compliance_report['critical_issues'].append({
                        'type': 'suspicious_login_activity',
                        'message': f'{len(suspicious_activity)} IP addresses with >10 failed login attempts in 24h',
                        'details': [{'email': row.user_email, 'ip': str(row.ip_address), 'attempts': row.attempts} for row in suspicious_activity]
                    })
                
                # Check audit log retention
                oldest_audit = await session.execute('''
                    SELECT MIN(created_at) as oldest_log
                    FROM audit_logs
                ''')
                
                oldest_log_result = oldest_audit.fetchone()
                if oldest_log_result and oldest_log_result.oldest_log:
                    log_age_days = (datetime.now() - oldest_log_result.oldest_log).days
                    compliance_report['security_checks']['audit_log_retention_days'] = log_age_days
                    
                    if log_age_days > 365:
                        compliance_report['warnings'].append({
                            'type': 'audit_retention',
                            'message': f'Audit logs are {log_age_days} days old, consider archiving'
                        })
                
                # Overall compliance assessment
                critical_count = len(compliance_report['critical_issues'])
                warning_count = len(compliance_report['warnings'])
                
                if critical_count == 0 and warning_count == 0:
                    compliance_report['overall_compliance'] = 'excellent'
                elif critical_count == 0 and warning_count <= 2:
                    compliance_report['overall_compliance'] = 'good'
                elif critical_count == 0:
                    compliance_report['overall_compliance'] = 'fair'
                else:
                    compliance_report['overall_compliance'] = 'poor'
                
                # Generate recommendations
                if warning_count > 0 or critical_count > 0:
                    compliance_report['recommendations'] = [
                        'Review and update password policy enforcement',
                        'Implement automated account lockout for suspicious activity',
                        'Set up automated alerts for security events',
                        'Regular security training for admin users',
                        'Consider implementing 2FA for admin accounts'
                    ]
            
            return compliance_report
            
        except Exception as e:
            logger.error(f'Error in security compliance audit: {e}')
            return {
                'audit_timestamp': datetime.now().isoformat(),
                'overall_compliance': 'error',
                'error': str(e)
            }
    
    def _validate_password(self, password: str) -> Dict[str, Any]:
        """
        Validate password against security policy
        """
        policy = self.security_policies['password_policy']
        
        if len(password) < policy['min_length']:
            return {'valid': False, 'error': f'Password must be at least {policy["min_length"]} characters'}
        
        if policy['require_uppercase'] and not any(c.isupper() for c in password):
            return {'valid': False, 'error': 'Password must contain uppercase letters'}
        
        if policy['require_lowercase'] and not any(c.islower() for c in password):
            return {'valid': False, 'error': 'Password must contain lowercase letters'}
        
        if policy['require_numbers'] and not any(c.isdigit() for c in password):
            return {'valid': False, 'error': 'Password must contain numbers'}
        
        if policy['require_special_chars'] and not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            return {'valid': False, 'error': 'Password must contain special characters'}
        
        return {'valid': True}


# CLI interface
async def main():
    """Main CLI function for security management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Healthcare AI V2 Security Manager")
    parser.add_argument("action", choices=["setup", "create-user", "audit", "policies"])
    parser.add_argument("--email", help="User email for create-user")
    parser.add_argument("--username", help="Username for create-user")
    parser.add_argument("--password", help="Password for create-user")
    parser.add_argument("--role", help="Role for create-user", choices=['healthcare_admin', 'medical_reviewer', 'data_manager', 'readonly_user'])
    parser.add_argument("--full-name", help="Full name for create-user")
    
    args = parser.parse_args()
    
    security_manager = SecurityPolicyManager()
    
    if args.action == "setup":
        result = await security_manager.setup_database_security()
        print(json.dumps(result, indent=2, default=str))
    
    elif args.action == "create-user":
        if not all([args.email, args.username, args.password, args.role]):
            print("Error: --email, --username, --password, and --role are required for create-user")
            sys.exit(1)
        
        result = await security_manager.create_security_user(
            email=args.email,
            username=args.username,
            password=args.password,
            role=args.role,
            full_name=args.full_name or ""
        )
        print(json.dumps(result, indent=2, default=str))
    
    elif args.action == "audit":
        audit_result = await security_manager.audit_security_compliance()
        print(json.dumps(audit_result, indent=2, default=str))
    
    elif args.action == "policies":
        print(json.dumps(security_manager.security_policies, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
