"""
Lambda Layer Configuration for Optimization
==========================================

Configuration and deployment scripts for Lambda layers that include the optimization system.
This ensures all Lambda functions have access to the optimization components.
"""

import json
import os
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

# Layer configuration
OPTIMIZATION_LAYER_CONFIG = {
    "layer_name": "healthcare-ai-optimization-layer",
    "description": "Lambda optimization system with connection pooling and cold start reduction",
    "compatible_runtimes": ["python3.9", "python3.10", "python3.11"],
    "compatible_architectures": ["x86_64", "arm64"],
    "license_info": "MIT"
}

# Required packages for the optimization layer
OPTIMIZATION_REQUIREMENTS = [
    "boto3>=1.26.0",
    "botocore>=1.29.0",
    "typing-extensions>=4.0.0"
]

def create_layer_package(output_dir: str = "lambda_layers") -> str:
    """
    Create a Lambda layer package with the optimization system.
    
    Args:
        output_dir: Directory to create the layer package
        
    Returns:
        Path to the created layer zip file
    """
    layer_dir = Path(output_dir) / "optimization_layer"
    python_dir = layer_dir / "python"
    
    # Create directories
    python_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy optimization modules
    src_dir = Path(__file__).parent
    optimization_files = [
        "lambda_optimizer.py",
        "__init__.py"
    ]
    
    aws_dir = python_dir / "aws"
    aws_dir.mkdir(exist_ok=True)
    
    for file_name in optimization_files:
        src_file = src_dir / file_name
        if src_file.exists():
            shutil.copy2(src_file, aws_dir / file_name)
    
    # Create __init__.py files
    (aws_dir / "__init__.py").touch()
    (python_dir / "__init__.py").touch()
    
    # Create requirements.txt
    requirements_file = layer_dir / "requirements.txt"
    with open(requirements_file, 'w') as f:
        f.write('\n'.join(OPTIMIZATION_REQUIREMENTS))
    
    # Create layer metadata
    metadata = {
        "layer_config": OPTIMIZATION_LAYER_CONFIG,
        "created_at": "2024-12-01T00:00:00Z",
        "version": "1.0.0",
        "contents": {
            "optimization_system": True,
            "connection_pooling": True,
            "lazy_loading": True,
            "lambda_warming": True
        }
    }
    
    metadata_file = layer_dir / "layer_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Create zip file
    zip_path = Path(output_dir) / f"{OPTIMIZATION_LAYER_CONFIG['layer_name']}.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(layer_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(layer_dir)
                zipf.write(file_path, arcname)
    
    print(f"Created Lambda layer package: {zip_path}")
    return str(zip_path)


def generate_cloudformation_layer_config() -> Dict[str, Any]:
    """
    Generate CloudFormation configuration for the optimization layer.
    
    Returns:
        CloudFormation resource configuration
    """
    return {
        "OptimizationLayer": {
            "Type": "AWS::Lambda::LayerVersion",
            "Properties": {
                "LayerName": OPTIMIZATION_LAYER_CONFIG["layer_name"],
                "Description": OPTIMIZATION_LAYER_CONFIG["description"],
                "Content": {
                    "S3Bucket": {"Ref": "DeploymentBucket"},
                    "S3Key": f"layers/{OPTIMIZATION_LAYER_CONFIG['layer_name']}.zip"
                },
                "CompatibleRuntimes": OPTIMIZATION_LAYER_CONFIG["compatible_runtimes"],
                "CompatibleArchitectures": OPTIMIZATION_LAYER_CONFIG["compatible_architectures"],
                "LicenseInfo": OPTIMIZATION_LAYER_CONFIG["license_info"]
            }
        }
    }


def generate_lambda_function_config(function_name: str, handler: str, 
                                  memory_mb: int = 512, timeout_seconds: int = 30) -> Dict[str, Any]:
    """
    Generate optimized Lambda function configuration.
    
    Args:
        function_name: Name of the Lambda function
        handler: Function handler path
        memory_mb: Memory allocation in MB
        timeout_seconds: Timeout in seconds
        
    Returns:
        CloudFormation Lambda function configuration
    """
    return {
        f"{function_name.replace('-', '')}Function": {
            "Type": "AWS::Lambda::Function",
            "Properties": {
                "FunctionName": {"Fn::Sub": f"${{Environment}}-{function_name}"},
                "Runtime": "python3.9",
                "Handler": handler,
                "Code": {
                    "S3Bucket": {"Ref": "DeploymentBucket"},
                    "S3Key": f"functions/{function_name}.zip"
                },
                "MemorySize": memory_mb,
                "Timeout": timeout_seconds,
                "Layers": [
                    {"Ref": "OptimizationLayer"}
                ],
                "Environment": {
                    "Variables": {
                        "ENVIRONMENT": {"Ref": "Environment"},
                        "CONVERSATIONS_TABLE": {"Ref": "ConversationsTable"},
                        "USERS_TABLE": {"Ref": "UserProfilesTable"},
                        "OPTIMIZATION_ENABLED": "true",
                        "CONNECTION_POOL_SIZE": "8",
                        "LAZY_LOADING_ENABLED": "true"
                    }
                },
                "ReservedConcurrencyLimit": 10,  # Prevent runaway costs
                "DeadLetterQueue": {
                    "TargetArn": {"Fn::GetAtt": ["DeadLetterQueue", "Arn"]}
                },
                "TracingConfig": {
                    "Mode": "Active"  # Enable X-Ray tracing
                }
            }
        }
    }


# Optimized configurations for each healthcare agent
HEALTHCARE_FUNCTION_CONFIGS = {
    "healthcare-agent-router": {
        "handler": "src.lambda.agent_router.handler.handler",
        "memory_mb": 512,
        "timeout_seconds": 30,
        "reserved_concurrency": 20
    },
    "healthcare-illness-monitor": {
        "handler": "src.lambda.illness_monitor.handler.lambda_handler",
        "memory_mb": 1024,
        "timeout_seconds": 60,
        "reserved_concurrency": 10
    },
    "healthcare-mental-health": {
        "handler": "src.lambda.mental_health.handler.lambda_handler",
        "memory_mb": 1024,
        "timeout_seconds": 60,
        "reserved_concurrency": 10
    },
    "healthcare-safety-guardian": {
        "handler": "src.lambda.safety_guardian.handler.lambda_handler",
        "memory_mb": 512,
        "timeout_seconds": 30,
        "reserved_concurrency": 15  # Higher for emergency responses
    },
    "healthcare-wellness-coach": {
        "handler": "src.lambda.wellness_coach.handler.lambda_handler",
        "memory_mb": 768,
        "timeout_seconds": 45,
        "reserved_concurrency": 8
    },
    "healthcare-speech-processor": {
        "handler": "src.lambda.speech_processor.handler.lambda_handler",
        "memory_mb": 1536,
        "timeout_seconds": 120,
        "reserved_concurrency": 5
    }
}


def generate_complete_lambda_config() -> Dict[str, Any]:
    """
    Generate complete CloudFormation configuration for all optimized Lambda functions.
    
    Returns:
        Complete CloudFormation resources configuration
    """
    resources = {}
    
    # Add optimization layer
    resources.update(generate_cloudformation_layer_config())
    
    # Add all Lambda functions
    for function_name, config in HEALTHCARE_FUNCTION_CONFIGS.items():
        function_config = generate_lambda_function_config(
            function_name=function_name,
            handler=config["handler"],
            memory_mb=config["memory_mb"],
            timeout_seconds=config["timeout_seconds"]
        )
        
        # Add reserved concurrency
        function_key = list(function_config.keys())[0]
        function_config[function_key]["Properties"]["ReservedConcurrencyLimit"] = config["reserved_concurrency"]
        
        resources.update(function_config)
    
    # Add EventBridge rule for Lambda warming
    resources["LambdaWarmingRule"] = {
        "Type": "AWS::Events::Rule",
        "Properties": {
            "Name": {"Fn::Sub": "${Environment}-lambda-warming"},
            "Description": "Scheduled Lambda warming to reduce cold starts",
            "ScheduleExpression": "rate(5 minutes)",
            "State": "ENABLED",
            "Targets": [
                {
                    "Arn": {"Fn::GetAtt": ["healthcareagentRouterFunction", "Arn"]},
                    "Id": "WarmAgentRouter",
                    "Input": json.dumps({"warming": True, "source": "eventbridge"})
                }
            ]
        }
    }
    
    # Add Lambda permissions for EventBridge
    resources["LambdaWarmingPermission"] = {
        "Type": "AWS::Lambda::Permission",
        "Properties": {
            "FunctionName": {"Ref": "healthcareagentRouterFunction"},
            "Action": "lambda:InvokeFunction",
            "Principal": "events.amazonaws.com",
            "SourceArn": {"Fn::GetAtt": ["LambdaWarmingRule", "Arn"]}
        }
    }
    
    # Add Dead Letter Queue
    resources["DeadLetterQueue"] = {
        "Type": "AWS::SQS::Queue",
        "Properties": {
            "QueueName": {"Fn::Sub": "${Environment}-healthcare-dlq"},
            "MessageRetentionPeriod": 1209600,  # 14 days
            "VisibilityTimeoutSeconds": 60
        }
    }
    
    return resources


def create_deployment_script() -> str:
    """
    Create a deployment script for the optimization system.
    
    Returns:
        Path to the deployment script
    """
    script_content = '''#!/bin/bash
set -e

# Healthcare AI Lambda Optimization Deployment Script
echo "Deploying Healthcare AI Lambda Optimization System..."

# Configuration
ENVIRONMENT=${ENVIRONMENT:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
DEPLOYMENT_BUCKET=${DEPLOYMENT_BUCKET:-healthcare-ai-deployment-$ENVIRONMENT}

# Create deployment bucket if it doesn't exist
aws s3 mb s3://$DEPLOYMENT_BUCKET --region $AWS_REGION || true

# Create and upload optimization layer
echo "Creating optimization layer..."
python3 -c "
from lambda_layer_config import create_layer_package
layer_zip = create_layer_package()
print(f'Created layer: {layer_zip}')
"

# Upload layer to S3
echo "Uploading optimization layer to S3..."
aws s3 cp lambda_layers/healthcare-ai-optimization-layer.zip s3://$DEPLOYMENT_BUCKET/layers/

# Package and upload Lambda functions
echo "Packaging Lambda functions..."
for function in agent_router illness_monitor mental_health safety_guardian wellness_coach speech_processor; do
    echo "Packaging $function..."
    cd src/lambda/$function
    zip -r ../../../$function.zip . -x "*.pyc" "__pycache__/*" "*.git*"
    cd ../../..
    
    echo "Uploading $function to S3..."
    aws s3 cp $function.zip s3://$DEPLOYMENT_BUCKET/functions/healthcare-$function.zip
    rm $function.zip
done

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \\
    --template-file infrastructure/cloudformation-template.yaml \\
    --stack-name healthcare-ai-$ENVIRONMENT \\
    --parameter-overrides Environment=$ENVIRONMENT \\
    --capabilities CAPABILITY_IAM \\
    --region $AWS_REGION

echo "Deployment completed successfully!"
echo "Optimization features enabled:"
echo "  ✓ Connection pooling for AWS services"
echo "  ✓ Lazy loading for non-critical modules"
echo "  ✓ Lambda warming every 5 minutes"
echo "  ✓ Optimized memory and timeout settings"
echo "  ✓ Reserved concurrency limits"
'''
    
    script_path = "deploy_optimization.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    print(f"Created deployment script: {script_path}")
    return script_path


if __name__ == "__main__":
    # Create layer package
    layer_zip = create_layer_package()
    
    # Generate CloudFormation config
    cf_config = generate_complete_lambda_config()
    
    # Save CloudFormation config
    with open("optimization_cloudformation.json", 'w') as f:
        json.dump(cf_config, f, indent=2)
    
    # Create deployment script
    deploy_script = create_deployment_script()
    
    print("\nOptimization system setup completed!")
    print(f"Layer package: {layer_zip}")
    print(f"CloudFormation config: optimization_cloudformation.json")
    print(f"Deployment script: {deploy_script}")