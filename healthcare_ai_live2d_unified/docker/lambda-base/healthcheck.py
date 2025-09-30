#!/usr/bin/env python3
"""
Lambda Container Health Check
============================

Basic health check for Lambda container images.
"""

import sys
import json
import importlib.util

def check_imports():
    """Check if required modules can be imported."""
    required_modules = [
        'boto3',
        'botocore',
        'requests',
        'json',
        'os',
        'logging',
        'datetime'
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError as e:
            failed_imports.append(f"{module}: {e}")
    
    return failed_imports

def check_aws_utilities():
    """Check if AWS utilities are available."""
    try:
        import aws.bedrock_client
        import aws.dynamodb_client
        import aws.config_manager
        return True
    except ImportError as e:
        return f"AWS utilities import failed: {e}"

def main():
    """Run health checks."""
    print("Running Lambda container health check...")
    
    # Check imports
    failed_imports = check_imports()
    if failed_imports:
        print("❌ Import failures:")
        for failure in failed_imports:
            print(f"  - {failure}")
        return 1
    
    print("✅ All required modules imported successfully")
    
    # Check AWS utilities
    aws_check = check_aws_utilities()
    if aws_check is not True:
        print(f"⚠️  AWS utilities check: {aws_check}")
    else:
        print("✅ AWS utilities available")
    
    # Check environment
    import os
    lambda_task_root = os.environ.get('LAMBDA_TASK_ROOT')
    if lambda_task_root:
        print(f"✅ Lambda task root: {lambda_task_root}")
    else:
        print("⚠️  LAMBDA_TASK_ROOT not set")
    
    print("🎉 Health check completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())