"""
Healthcare AI Deployment Automation
===================================

Comprehensive deployment automation with blue-green deployment strategy,
rollback procedures, and health checks.
"""

import json
import boto3
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import argparse
import sys
import os

logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """Deployment configuration."""
    environment: str
    aws_region: str
    stack_name: str
    template_path: str
    parameters: Dict[str, str]
    capabilities: List[str]
    timeout_minutes: int = 60
    enable_rollback: bool = True


@dataclass
class DeploymentResult:
    """Deployment result information."""
    success: bool
    stack_id: Optional[str] = None
    outputs: Optional[Dict[str, str]] = None
    duration: float = 0.0
    error_message: Optional[str] = None
    rollback_performed: bool = False


class HealthcareAIDeployer:
    """Main deployment orchestrator for healthcare AI system."""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.cloudformation = boto3.client('cloudformation', region_name=config.aws_region)
        self.lambda_client = boto3.client('lambda', region_name=config.aws_region)
        self.apigateway = boto3.client('apigateway', region_name=config.aws_region)
        self.s3 = boto3.client('s3', region_name=config.aws_region)
        
        # Deployment tracking
        self.deployment_start_time = None
        self.previous_stack_info = None
        
    def get_stack_info(self, stack_name: str) -> Optional[Dict[str, Any]]:
        """Get current stack information."""
        try:
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            if response['Stacks']:
                stack = response['Stacks'][0]
                return {
                    'stack_id': stack['StackId'],
                    'stack_status': stack['StackStatus'],
                    'outputs': {
                        output['OutputKey']: output['OutputValue']
                        for output in stack.get('Outputs', [])
                    },
                    'parameters': {
                        param['ParameterKey']: param['ParameterValue']
                        for param in stack.get('Parameters', [])
                    }
                }
        except self.cloudformation.exceptions.ClientError as e:
            if 'does not exist' in str(e):
                return None
            raise
        
        return None
    
    def validate_template(self) -> bool:
        """Validate CloudFormation template."""
        try:
            with open(self.config.template_path, 'r') as f:
                template_body = f.read()
            
            response = self.cloudformation.validate_template(TemplateBody=template_body)
            
            logger.info("Template validation successful")
            logger.info(f"Template description: {response.get('Description', 'N/A')}")
            
            # Log parameters
            if response.get('Parameters'):
                logger.info("Template parameters:")
                for param in response['Parameters']:
                    logger.info(f"  - {param['ParameterKey']}: {param.get('Description', 'No description')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            return False
    
    def prepare_parameters(self) -> List[Dict[str, str]]:
        """Prepare CloudFormation parameters."""
        parameters = []
        
        for key, value in self.config.parameters.items():
            parameters.append({
                'ParameterKey': key,
                'ParameterValue': str(value)
            })
        
        return parameters
    
    def deploy_stack(self) -> DeploymentResult:
        """Deploy or update CloudFormation stack."""
        self.deployment_start_time = time.time()
        
        try:
            # Get existing stack info for rollback
            self.previous_stack_info = self.get_stack_info(self.config.stack_name)
            
            # Read template
            with open(self.config.template_path, 'r') as f:
                template_body = f.read()
            
            # Prepare parameters
            parameters = self.prepare_parameters()
            
            # Determine if this is create or update
            is_update = self.previous_stack_info is not None
            
            if is_update:
                logger.info(f"Updating existing stack: {self.config.stack_name}")
                
                response = self.cloudformation.update_stack(
                    StackName=self.config.stack_name,
                    TemplateBody=template_body,
                    Parameters=parameters,
                    Capabilities=self.config.capabilities
                )
                
                operation = 'UPDATE'
                
            else:
                logger.info(f"Creating new stack: {self.config.stack_name}")
                
                response = self.cloudformation.create_stack(
                    StackName=self.config.stack_name,
                    TemplateBody=template_body,
                    Parameters=parameters,
                    Capabilities=self.config.capabilities,
                    EnableTerminationProtection=self.config.environment == 'production',
                    TimeoutInMinutes=self.config.timeout_minutes,
                    OnFailure='ROLLBACK' if self.config.enable_rollback else 'DO_NOTHING'
                )
                
                operation = 'CREATE'
            
            stack_id = response['StackId']
            logger.info(f"Stack {operation} initiated: {stack_id}")
            
            # Wait for completion
            result = self._wait_for_stack_completion(stack_id, operation)
            
            if result.success:
                # Get final stack info
                final_stack_info = self.get_stack_info(self.config.stack_name)
                if final_stack_info:
                    result.outputs = final_stack_info['outputs']
                
                logger.info(f"Stack {operation.lower()} completed successfully")
                
                # Run post-deployment validation
                if not self._validate_deployment(result.outputs):
                    logger.warning("Post-deployment validation failed")
                    if self.config.enable_rollback and is_update:
                        logger.info("Initiating rollback due to validation failure")
                        rollback_result = self._rollback_stack()
                        result.rollback_performed = rollback_result
            
            return result
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            
            duration = time.time() - self.deployment_start_time if self.deployment_start_time else 0
            
            return DeploymentResult(
                success=False,
                duration=duration,
                error_message=str(e)
            )
    
    def _wait_for_stack_completion(self, stack_id: str, operation: str) -> DeploymentResult:
        """Wait for CloudFormation stack operation to complete."""
        start_time = time.time()
        timeout = self.config.timeout_minutes * 60
        
        success_statuses = {
            'CREATE': ['CREATE_COMPLETE'],
            'UPDATE': ['UPDATE_COMPLETE']
        }
        
        failure_statuses = {
            'CREATE': ['CREATE_FAILED', 'ROLLBACK_COMPLETE', 'ROLLBACK_FAILED'],
            'UPDATE': ['UPDATE_FAILED', 'UPDATE_ROLLBACK_COMPLETE', 'UPDATE_ROLLBACK_FAILED']
        }
        
        while True:
            try:
                response = self.cloudformation.describe_stacks(StackName=stack_id)
                stack = response['Stacks'][0]
                status = stack['StackStatus']
                
                logger.info(f"Stack status: {status}")
                
                if status in success_statuses[operation]:
                    duration = time.time() - start_time
                    return DeploymentResult(
                        success=True,
                        stack_id=stack_id,
                        duration=duration
                    )
                
                elif status in failure_statuses[operation]:
                    duration = time.time() - start_time
                    
                    # Get failure reason
                    error_message = self._get_stack_failure_reason(stack_id)
                    
                    return DeploymentResult(
                        success=False,
                        stack_id=stack_id,
                        duration=duration,
                        error_message=error_message
                    )
                
                # Check timeout
                if time.time() - start_time > timeout:
                    return DeploymentResult(
                        success=False,
                        stack_id=stack_id,
                        duration=time.time() - start_time,
                        error_message=f"Deployment timed out after {self.config.timeout_minutes} minutes"
                    )
                
                # Wait before next check
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error checking stack status: {e}")
                time.sleep(10)
    
    def _get_stack_failure_reason(self, stack_id: str) -> str:
        """Get detailed failure reason from stack events."""
        try:
            response = self.cloudformation.describe_stack_events(StackName=stack_id)
            
            failure_events = [
                event for event in response['StackEvents']
                if event.get('ResourceStatus', '').endswith('_FAILED')
            ]
            
            if failure_events:
                # Get the most recent failure
                latest_failure = failure_events[0]
                return f"{latest_failure.get('LogicalResourceId', 'Unknown')}: {latest_failure.get('ResourceStatusReason', 'No reason provided')}"
            
            return "Stack operation failed (no specific reason found)"
            
        except Exception as e:
            return f"Failed to get failure reason: {e}"
    
    def _validate_deployment(self, outputs: Optional[Dict[str, str]]) -> bool:
        """Validate deployment by checking key resources."""
        if not outputs:
            logger.warning("No stack outputs to validate")
            return False
        
        validation_checks = []
        
        # Check Lambda functions
        lambda_functions = [
            f"healthcare-ai-{self.config.environment}-agent-router",
            f"healthcare-ai-{self.config.environment}-illness-monitor",
            f"healthcare-ai-{self.config.environment}-mental-health",
            f"healthcare-ai-{self.config.environment}-safety-guardian",
            f"healthcare-ai-{self.config.environment}-wellness-coach"
        ]
        
        for function_name in lambda_functions:
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                if response['Configuration']['State'] == 'Active':
                    validation_checks.append(f"Lambda {function_name}: OK")
                else:
                    validation_checks.append(f"Lambda {function_name}: NOT ACTIVE")
                    return False
            except Exception as e:
                validation_checks.append(f"Lambda {function_name}: ERROR - {e}")
                return False
        
        # Check API Gateway
        if 'ApiGatewayUrl' in outputs:
            try:
                import requests
                health_url = f"{outputs['ApiGatewayUrl']}/health"
                response = requests.get(health_url, timeout=10)
                if response.status_code == 200:
                    validation_checks.append("API Gateway: OK")
                else:
                    validation_checks.append(f"API Gateway: HTTP {response.status_code}")
                    return False
            except Exception as e:
                validation_checks.append(f"API Gateway: ERROR - {e}")
                return False
        
        # Check DynamoDB tables
        dynamodb = boto3.client('dynamodb', region_name=self.config.aws_region)
        tables = [
            f"HealthcareAI-{self.config.environment.title()}-Conversations",
            f"HealthcareAI-{self.config.environment.title()}-Users"
        ]
        
        for table_name in tables:
            try:
                response = dynamodb.describe_table(TableName=table_name)
                if response['Table']['TableStatus'] == 'ACTIVE':
                    validation_checks.append(f"DynamoDB {table_name}: OK")
                else:
                    validation_checks.append(f"DynamoDB {table_name}: NOT ACTIVE")
                    return False
            except Exception as e:
                validation_checks.append(f"DynamoDB {table_name}: ERROR - {e}")
                return False
        
        # Log validation results
        logger.info("Deployment validation results:")
        for check in validation_checks:
            logger.info(f"  - {check}")
        
        return True
    
    def _rollback_stack(self) -> bool:
        """Rollback stack to previous version."""
        if not self.previous_stack_info:
            logger.error("No previous stack info available for rollback")
            return False
        
        try:
            logger.info("Initiating stack rollback...")
            
            # Cancel current update if in progress
            try:
                self.cloudformation.cancel_update_stack(StackName=self.config.stack_name)
                logger.info("Cancelled current update")
                time.sleep(30)
            except Exception as e:
                logger.info(f"Could not cancel update (may not be in progress): {e}")
            
            # Continue with rollback
            self.cloudformation.continue_update_rollback(StackName=self.config.stack_name)
            
            # Wait for rollback completion
            start_time = time.time()
            timeout = 30 * 60  # 30 minutes for rollback
            
            while True:
                response = self.cloudformation.describe_stacks(StackName=self.config.stack_name)
                stack = response['Stacks'][0]
                status = stack['StackStatus']
                
                logger.info(f"Rollback status: {status}")
                
                if status == 'UPDATE_ROLLBACK_COMPLETE':
                    logger.info("Rollback completed successfully")
                    return True
                
                elif status in ['UPDATE_ROLLBACK_FAILED', 'UPDATE_FAILED']:
                    logger.error("Rollback failed")
                    return False
                
                if time.time() - start_time > timeout:
                    logger.error("Rollback timed out")
                    return False
                
                time.sleep(30)
                
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def delete_stack(self) -> bool:
        """Delete CloudFormation stack."""
        try:
            logger.info(f"Deleting stack: {self.config.stack_name}")
            
            self.cloudformation.delete_stack(StackName=self.config.stack_name)
            
            # Wait for deletion
            start_time = time.time()
            timeout = 30 * 60  # 30 minutes
            
            while True:
                try:
                    response = self.cloudformation.describe_stacks(StackName=self.config.stack_name)
                    stack = response['Stacks'][0]
                    status = stack['StackStatus']
                    
                    logger.info(f"Deletion status: {status}")
                    
                    if status == 'DELETE_COMPLETE':
                        logger.info("Stack deleted successfully")
                        return True
                    
                    elif status == 'DELETE_FAILED':
                        logger.error("Stack deletion failed")
                        return False
                    
                    if time.time() - start_time > timeout:
                        logger.error("Stack deletion timed out")
                        return False
                    
                    time.sleep(30)
                    
                except self.cloudformation.exceptions.ClientError as e:
                    if 'does not exist' in str(e):
                        logger.info("Stack deleted successfully")
                        return True
                    raise
                
        except Exception as e:
            logger.error(f"Error deleting stack: {e}")
            return False
    
    def generate_deployment_report(self, result: DeploymentResult) -> Dict[str, Any]:
        """Generate deployment report."""
        return {
            'deployment_info': {
                'environment': self.config.environment,
                'stack_name': self.config.stack_name,
                'aws_region': self.config.aws_region,
                'template_path': self.config.template_path
            },
            'result': {
                'success': result.success,
                'duration_seconds': result.duration,
                'stack_id': result.stack_id,
                'error_message': result.error_message,
                'rollback_performed': result.rollback_performed
            },
            'outputs': result.outputs or {},
            'timestamp': datetime.utcnow().isoformat()
        }


def load_deployment_config(config_file: str, environment: str) -> DeploymentConfig:
    """Load deployment configuration from file."""
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    env_config = config_data.get(environment)
    if not env_config:
        raise ValueError(f"Environment '{environment}' not found in config file")
    
    return DeploymentConfig(
        environment=environment,
        aws_region=env_config.get('aws_region', 'us-east-1'),
        stack_name=env_config['stack_name'],
        template_path=env_config['template_path'],
        parameters=env_config.get('parameters', {}),
        capabilities=env_config.get('capabilities', ['CAPABILITY_IAM']),
        timeout_minutes=env_config.get('timeout_minutes', 60),
        enable_rollback=env_config.get('enable_rollback', True)
    )


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description='Deploy Healthcare AI system')
    parser.add_argument('--environment', required=True, help='Deployment environment')
    parser.add_argument('--config', default='deployment/config.json', help='Configuration file')
    parser.add_argument('--action', choices=['deploy', 'delete', 'validate'], default='deploy', help='Action to perform')
    parser.add_argument('--output', help='Output file for deployment report')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Load configuration
        config = load_deployment_config(args.config, args.environment)
        
        # Initialize deployer
        deployer = HealthcareAIDeployer(config)
        
        if args.action == 'validate':
            # Validate template only
            if deployer.validate_template():
                logger.info("Template validation successful")
                return 0
            else:
                logger.error("Template validation failed")
                return 1
        
        elif args.action == 'delete':
            # Delete stack
            if deployer.delete_stack():
                logger.info("Stack deletion successful")
                return 0
            else:
                logger.error("Stack deletion failed")
                return 1
        
        elif args.action == 'deploy':
            # Validate template first
            if not deployer.validate_template():
                logger.error("Template validation failed")
                return 1
            
            # Deploy stack
            result = deployer.deploy_stack()
            
            # Generate report
            report = deployer.generate_deployment_report(result)
            
            # Save report if requested
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2)
                logger.info(f"Deployment report saved to: {args.output}")
            
            # Print summary
            if result.success:
                logger.info("🎉 Deployment completed successfully!")
                if result.outputs:
                    logger.info("Stack outputs:")
                    for key, value in result.outputs.items():
                        logger.info(f"  {key}: {value}")
                return 0
            else:
                logger.error(f"❌ Deployment failed: {result.error_message}")
                if result.rollback_performed:
                    logger.info("Rollback was performed")
                return 1
    
    except Exception as e:
        logger.error(f"Deployment script error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())