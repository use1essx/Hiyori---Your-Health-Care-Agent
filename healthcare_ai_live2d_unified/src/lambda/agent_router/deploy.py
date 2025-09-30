#!/usr/bin/env python3
"""
Agent Router Lambda Deployment Script
====================================

Script to package and deploy the Agent Router Lambda function.
"""

import os
import sys
import zipfile
import boto3
import json
from pathlib import Path

def create_deployment_package():
    """Create deployment package for Agent Router Lambda."""
    
    # Get current directory
    current_dir = Path(__file__).parent
    
    # Create deployment package
    package_path = current_dir / 'agent_router_deployment.zip'
    
    with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add handler.py
        handler_path = current_dir / 'handler.py'
        if handler_path.exists():
            zipf.write(handler_path, 'handler.py')
            print(f"Added {handler_path} to package")
        else:
            print(f"Warning: {handler_path} not found")
        
        # Add any additional Python files if needed
        for py_file in current_dir.glob('*.py'):
            if py_file.name not in ['deploy.py', 'handler.py']:
                zipf.write(py_file, py_file.name)
                print(f"Added {py_file} to package")
    
    print(f"Deployment package created: {package_path}")
    return package_path

def update_lambda_function(package_path, function_name, environment='dev'):
    """Update Lambda function with new code."""
    
    try:
        lambda_client = boto3.client('lambda')
        
        # Read the deployment package
        with open(package_path, 'rb') as f:
            zip_content = f.read()
        
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName=f"{environment}-healthcare-agent-router",
            ZipFile=zip_content
        )
        
        print(f"Lambda function updated successfully")
        print(f"Function ARN: {response['FunctionArn']}")
        print(f"Last Modified: {response['LastModified']}")
        
        return True
        
    except Exception as e:
        print(f"Error updating Lambda function: {str(e)}")
        return False

def main():
    """Main deployment function."""
    
    # Get environment from command line or default to 'dev'
    environment = sys.argv[1] if len(sys.argv) > 1 else 'dev'
    
    print(f"Deploying Agent Router Lambda for environment: {environment}")
    
    # Create deployment package
    package_path = create_deployment_package()
    
    # Update Lambda function
    success = update_lambda_function(package_path, 'agent-router', environment)
    
    if success:
        print("Deployment completed successfully!")
    else:
        print("Deployment failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()