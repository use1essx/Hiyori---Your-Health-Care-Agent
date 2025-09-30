#!/usr/bin/env python3
"""
Healthcare AI V2 - Automated Backup and Restore System
Provides automated database backup, restore, and maintenance functions for pgAdmin integration
"""

import os
import sys
import asyncio
import subprocess
import logging
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config import settings
from src.database.connection import get_async_session
from src.core.logging import setup_logging


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


class BackupManager:
    """
    Comprehensive backup and restore system for Healthcare AI V2 database
    """
    
    def __init__(self):
        self.backup_dir = Path("/var/lib/pgadmin/storage/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Database connection settings
        self.db_host = "postgres"
        self.db_port = "5432"
        self.db_name = settings.DATABASE_NAME
        self.db_user = settings.DATABASE_USER
        self.db_password = settings.DATABASE_PASSWORD
        
        # Backup settings
        self.retention_days = 30
        self.compress_backups = True
        self.max_backup_size_gb = 10
        
        # S3 settings (optional for cloud backups)
        self.s3_enabled = bool(os.getenv('AWS_BACKUP_ENABLED', False))
        self.s3_bucket = os.getenv('AWS_BACKUP_BUCKET', 'healthcare-ai-backups')
        self.s3_region = os.getenv('AWS_REGION', 'us-east-1')
        
        if self.s3_enabled:
            try:
                self.s3_client = boto3.client('s3', region_name=self.s3_region)
            except NoCredentialsError:
                logger.warning("AWS credentials not found, S3 backups disabled")
                self.s3_enabled = False
    
    async def create_full_backup(
        self, 
        backup_name: Optional[str] = None,
        include_data: bool = True,
        include_schema: bool = True
    ) -> Dict[str, Any]:
        """
        Create a full database backup using pg_dump
        """
        try:
            # Generate backup name if not provided
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"healthcare_ai_v2_full_{timestamp}"
            
            backup_file = self.backup_dir / f"{backup_name}.sql"
            
            # Build pg_dump command
            dump_cmd = [
                "pg_dump",
                f"--host={self.db_host}",
                f"--port={self.db_port}",
                f"--username={self.db_user}",
                f"--dbname={self.db_name}",
                "--verbose",
                "--no-password",
                "--format=custom",
                "--compress=9"
            ]
            
            if not include_data:
                dump_cmd.append("--schema-only")
            elif not include_schema:
                dump_cmd.append("--data-only")
            
            # Add file output
            dump_cmd.extend(["--file", str(backup_file)])
            
            # Set environment for password
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password
            
            logger.info(f"Starting database backup: {backup_name}")
            start_time = datetime.now()
            
            # Execute backup
            result = subprocess.run(
                dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Backup failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "backup_name": backup_name
                }
            
            backup_time = datetime.now() - start_time
            backup_size = backup_file.stat().st_size
            
            # Compress if enabled
            if self.compress_backups:
                await self._compress_backup(backup_file)
                backup_file = backup_file.with_suffix('.sql.gz')
                backup_size = backup_file.stat().st_size
            
            # Upload to S3 if enabled
            s3_uploaded = False
            if self.s3_enabled:
                s3_uploaded = await self._upload_to_s3(backup_file, backup_name)
            
            # Log backup details
            backup_info = {
                "success": True,
                "backup_name": backup_name,
                "backup_file": str(backup_file),
                "backup_size_bytes": backup_size,
                "backup_size_mb": round(backup_size / (1024 * 1024), 2),
                "backup_duration_seconds": backup_time.total_seconds(),
                "compressed": self.compress_backups,
                "s3_uploaded": s3_uploaded,
                "created_at": datetime.now().isoformat(),
                "include_data": include_data,
                "include_schema": include_schema
            }
            
            # Save backup metadata
            await self._save_backup_metadata(backup_info)
            
            logger.info(f"Backup completed successfully: {backup_name} ({backup_info['backup_size_mb']} MB)")
            return backup_info
            
        except subprocess.TimeoutExpired:
            logger.error(f"Backup timeout for {backup_name}")
            return {
                "success": False,
                "error": "Backup operation timed out",
                "backup_name": backup_name
            }
        except Exception as e:
            logger.error(f"Backup failed for {backup_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "backup_name": backup_name
            }
    
    async def restore_backup(
        self, 
        backup_file: str,
        target_database: Optional[str] = None,
        clean_first: bool = False
    ) -> Dict[str, Any]:
        """
        Restore database from backup file
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                # Try to find in backup directory
                backup_path = self.backup_dir / backup_file
                if not backup_path.exists():
                    return {
                        "success": False,
                        "error": f"Backup file not found: {backup_file}"
                    }
            
            target_db = target_database or self.db_name
            
            # Decompress if needed
            working_file = backup_path
            if backup_path.suffix == '.gz':
                working_file = await self._decompress_backup(backup_path)
            
            # Build pg_restore command
            restore_cmd = [
                "pg_restore",
                f"--host={self.db_host}",
                f"--port={self.db_port}",
                f"--username={self.db_user}",
                f"--dbname={target_db}",
                "--verbose",
                "--no-password"
            ]
            
            if clean_first:
                restore_cmd.extend(["--clean", "--if-exists"])
            
            restore_cmd.append(str(working_file))
            
            # Set environment for password
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password
            
            logger.info(f"Starting database restore: {backup_file} -> {target_db}")
            start_time = datetime.now()
            
            # Execute restore
            result = subprocess.run(
                restore_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            restore_time = datetime.now() - start_time
            
            # pg_restore may have warnings but still succeed
            if result.returncode != 0:
                # Check if it's a fatal error or just warnings
                if "ERROR" in result.stderr.upper():
                    logger.error(f"Restore failed: {result.stderr}")
                    return {
                        "success": False,
                        "error": result.stderr,
                        "backup_file": backup_file
                    }
                else:
                    logger.warning(f"Restore completed with warnings: {result.stderr}")
            
            # Clean up temporary decompressed file
            if working_file != backup_path:
                working_file.unlink()
            
            restore_info = {
                "success": True,
                "backup_file": backup_file,
                "target_database": target_db,
                "restore_duration_seconds": restore_time.total_seconds(),
                "clean_first": clean_first,
                "restored_at": datetime.now().isoformat(),
                "warnings": result.stderr if result.stderr else None
            }
            
            logger.info(f"Restore completed successfully: {backup_file} -> {target_db}")
            return restore_info
            
        except subprocess.TimeoutExpired:
            logger.error(f"Restore timeout for {backup_file}")
            return {
                "success": False,
                "error": "Restore operation timed out",
                "backup_file": backup_file
            }
        except Exception as e:
            logger.error(f"Restore failed for {backup_file}: {e}")
            return {
                "success": False,
                "error": str(e),
                "backup_file": backup_file
            }
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups with metadata
        """
        try:
            backups = []
            metadata_file = self.backup_dir / "backup_metadata.json"
            
            # Load metadata if exists
            metadata = {}
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load backup metadata: {e}")
            
            # Scan backup directory
            for backup_file in self.backup_dir.glob("*.sql*"):
                file_stat = backup_file.stat()
                backup_name = backup_file.stem.replace('.sql', '')
                
                backup_info = {
                    "backup_name": backup_name,
                    "file_name": backup_file.name,
                    "file_path": str(backup_file),
                    "size_bytes": file_stat.st_size,
                    "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "compressed": backup_file.suffix == '.gz'
                }
                
                # Add metadata if available
                if backup_name in metadata:
                    backup_info.update(metadata[backup_name])
                
                backups.append(backup_info)
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    async def cleanup_old_backups(self) -> Dict[str, Any]:
        """
        Clean up backups older than retention period
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            deleted_files = []
            total_space_freed = 0
            
            for backup_file in self.backup_dir.glob("*.sql*"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    file_size = backup_file.stat().st_size
                    backup_file.unlink()
                    deleted_files.append({
                        "file_name": backup_file.name,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "created_at": file_time.isoformat()
                    })
                    total_space_freed += file_size
            
            cleanup_info = {
                "success": True,
                "retention_days": self.retention_days,
                "deleted_files": deleted_files,
                "files_deleted": len(deleted_files),
                "space_freed_mb": round(total_space_freed / (1024 * 1024), 2),
                "cleanup_at": datetime.now().isoformat()
            }
            
            logger.info(f"Backup cleanup completed: {len(deleted_files)} files deleted, {cleanup_info['space_freed_mb']} MB freed")
            return cleanup_info
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_backup(self, backup_file: str) -> Dict[str, Any]:
        """
        Verify backup file integrity
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                backup_path = self.backup_dir / backup_file
                if not backup_path.exists():
                    return {
                        "success": False,
                        "error": f"Backup file not found: {backup_file}"
                    }
            
            # Check file size
            file_size = backup_path.stat().st_size
            if file_size == 0:
                return {
                    "success": False,
                    "error": "Backup file is empty"
                }
            
            # Test file readability
            try:
                if backup_path.suffix == '.gz':
                    with gzip.open(backup_path, 'rt') as f:
                        # Read first few lines to verify it's a valid SQL dump
                        header = f.read(1024)
                else:
                    with open(backup_path, 'r') as f:
                        header = f.read(1024)
                
                # Check for PostgreSQL dump header
                if "PostgreSQL database dump" not in header and "pg_dump" not in header:
                    return {
                        "success": False,
                        "error": "File does not appear to be a valid PostgreSQL dump"
                    }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Cannot read backup file: {e}"
                }
            
            verification_info = {
                "success": True,
                "backup_file": backup_file,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "readable": True,
                "valid_format": True,
                "verified_at": datetime.now().isoformat()
            }
            
            return verification_info
            
        except Exception as e:
            logger.error(f"Backup verification failed for {backup_file}: {e}")
            return {
                "success": False,
                "error": str(e),
                "backup_file": backup_file
            }
    
    # Helper methods
    
    async def _compress_backup(self, backup_file: Path) -> Path:
        """Compress backup file using gzip"""
        compressed_file = backup_file.with_suffix('.sql.gz')
        
        with open(backup_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original file
        backup_file.unlink()
        
        return compressed_file
    
    async def _decompress_backup(self, backup_file: Path) -> Path:
        """Decompress backup file for restore"""
        decompressed_file = backup_file.with_suffix('')
        
        with gzip.open(backup_file, 'rb') as f_in:
            with open(decompressed_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return decompressed_file
    
    async def _upload_to_s3(self, backup_file: Path, backup_name: str) -> bool:
        """Upload backup to S3 (if configured)"""
        if not self.s3_enabled:
            return False
        
        try:
            s3_key = f"healthcare-ai-v2/{datetime.now().year}/{datetime.now().month:02d}/{backup_file.name}"
            
            self.s3_client.upload_file(
                str(backup_file),
                self.s3_bucket,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'Metadata': {
                        'backup_name': backup_name,
                        'created_at': datetime.now().isoformat()
                    }
                }
            )
            
            logger.info(f"Backup uploaded to S3: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return False
    
    async def _save_backup_metadata(self, backup_info: Dict[str, Any]):
        """Save backup metadata to JSON file"""
        try:
            metadata_file = self.backup_dir / "backup_metadata.json"
            
            # Load existing metadata
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            # Add new backup info
            metadata[backup_info['backup_name']] = backup_info
            
            # Save updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Could not save backup metadata: {e}")


# CLI functions for manual operation

async def main():
    """Main CLI function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Healthcare AI V2 Backup Manager")
    parser.add_argument("action", choices=["backup", "restore", "list", "cleanup", "verify"])
    parser.add_argument("--name", help="Backup name")
    parser.add_argument("--file", help="Backup file for restore/verify")
    parser.add_argument("--target-db", help="Target database for restore")
    parser.add_argument("--clean", action="store_true", help="Clean database before restore")
    parser.add_argument("--schema-only", action="store_true", help="Backup schema only")
    parser.add_argument("--data-only", action="store_true", help="Backup data only")
    
    args = parser.parse_args()
    
    backup_manager = BackupManager()
    
    if args.action == "backup":
        result = await backup_manager.create_full_backup(
            backup_name=args.name,
            include_data=not args.schema_only,
            include_schema=not args.data_only
        )
        print(json.dumps(result, indent=2))
    
    elif args.action == "restore":
        if not args.file:
            print("Error: --file required for restore")
            sys.exit(1)
        result = await backup_manager.restore_backup(
            backup_file=args.file,
            target_database=args.target_db,
            clean_first=args.clean
        )
        print(json.dumps(result, indent=2))
    
    elif args.action == "list":
        backups = await backup_manager.list_backups()
        print(json.dumps(backups, indent=2))
    
    elif args.action == "cleanup":
        result = await backup_manager.cleanup_old_backups()
        print(json.dumps(result, indent=2))
    
    elif args.action == "verify":
        if not args.file:
            print("Error: --file required for verify")
            sys.exit(1)
        result = await backup_manager.verify_backup(args.file)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
