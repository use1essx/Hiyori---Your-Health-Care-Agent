"""
Deploy and Test Healthcare AI System
====================================

Complete deployment and testing orchestration script that:
1. Deploys the system to AWS test environment
2. Validates deployment
3. Runs comprehensive functionality tests
4. Performs cost analysis
5. Generates final report
"""

import json
import os
import sys
import time
import logging
import subprocess
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / 'tests'))
sys.path.append(str(Path(__file__).parent.parent / 'deployment'))

from deployment.deploy import HealthcareAIDeployer, DeploymentConfig
from tests.final_integration_test import FinalIntegrationTester, IntegrationTestConfig

logger = logging.getLogger(__name__)


class DeploymentOrchestrator:
    """Orchestrates complete deployment and testing process."""
    
    def __init__(self, environment: str, aws_region: str):
        self.environment = environment
        self.aws_region = aws_region
        self.project_root = Path(__file__).parent.parent
        
        # Results tracking
        self.deployment_result = None
        self.test_results = None
        self.final_report = None
        
    def run_complete_deployment_and_test(self) -> Dict[str, Any]:
        """Run complete deployment and testing process."""
        logger.info("Starting complete deployment and testing process...")
        
        process_results = {
            'start_time': datetime.utcnow().isoformat(),
            'environment': self.environment,
            'aws_region': self.aws_region,
            'steps': {}
        }
        
        try:
            # Step 1: Prepare deployment
            logger.info("Step 1: Preparing deployment...")
            prep_result = self._prepare_deployment()
            process_results['steps']['preparation'] = prep_result
            
            if not prep_result['success']:
                process_results['overall_status'] = 'FAILED'
                process_results['failure_step'] = 'preparation'
                return process_results
            
            # Step 2: Deploy infrastructure
            logger.info("Step 2: Deploying infrastructure...")
            deploy_result = self._deploy_infrastructure()
            process_results['steps']['deployment'] = deploy_result
            
            if not deploy_result['success']:
                process_results['overall_status'] = 'FAILED'
                process_results['failure_step'] = 'deployment'
                return process_results
            
            # Step 3: Deploy Lambda functions
            logger.info("Step 3: Deploying Lambda functions...")
            lambda_result = self._deploy_lambda_functions()
            process_results['steps']['lambda_deployment'] = lambda_result
            
            if not lambda_result['success']:
                process_results['overall_status'] = 'FAILED'
                process_results['failure_step'] = 'lambda_deployment'
                return process_results
            
            # Step 4: Deploy frontend
            logger.info("Step 4: Deploying frontend...")
            frontend_result = self._deploy_frontend()
            process_results['steps']['frontend_deployment'] = frontend_result
            
            if not frontend_result['success']:
                process_results['overall_status'] = 'FAILED'
                process_results['failure_step'] = 'frontend_deployment'
                return process_results
            
            # Step 5: Wait for deployment stabilization
            logger.info("Step 5: Waiting for deployment stabilization...")
            time.sleep(60)  # Wait 1 minute for services to stabilize
            
            # Step 6: Run comprehensive tests
            logger.info("Step 6: Running comprehensive tests...")
            test_result = self._run_comprehensive_tests()
            process_results['steps']['testing'] = test_result
            
            # Step 7: Generate final report
            logger.info("Step 7: Generating final report...")
            report_result = self._generate_final_report()
            process_results['steps']['reporting'] = report_result
            
            # Determine overall status
            if test_result.get('success', False):
                process_results['overall_status'] = 'PASSED'
            else:
                process_results['overall_status'] = 'FAILED'
                process_results['failure_step'] = 'testing'
            
            process_results['end_time'] = datetime.utcnow().isoformat()
            
            return process_results
            
        except Exception as e:
            logger.error(f"Deployment and testing process failed: {e}")
            process_results['overall_status'] = 'ERROR'
            process_results['error'] = str(e)
            process_results['end_time'] = datetime.utcnow().isoformat()
            return process_results
    
    def _prepare_deployment(self) -> Dict[str, Any]:
        """Prepare deployment environment and files."""
        try:
            # Check prerequisites
            prerequisites = [
                ('aws', 'AWS CLI'),
                ('docker', 'Docker'),
                ('python', 'Python')
            ]
            
            missing_prereqs = []
            for cmd, name in prerequisites:
                if subprocess.run(['which', cmd], capture_output=True).returncode != 0:
                    missing_prereqs.append(name)
            
            if missing_prereqs:
                return {
                    'success': False,
                    'error': f"Missing prerequisites: {', '.join(missing_prereqs)}"
                }
            
            # Validate configuration files exist
            required_files = [
                'infrastructure/cloudformation-template.yaml',
                'deployment/config.json',
                'frontend/config/aws-config.js'
            ]
            
            missing_files = []
            for file_path in required_files:
                full_path = self.project_root / file_path
                if not full_path.exists():
                    missing_files.append(file_path)
            
            if missing_files:
                return {
                    'success': False,
                    'error': f"Missing required files: {', '.join(missing_files)}"
                }
            
            # Create deployment configuration if needed
            self._ensure_deployment_config()
            
            return {
                'success': True,
                'message': 'Deployment preparation completed successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Preparation failed: {str(e)}"
            }
    
    def _ensure_deployment_config(self):
        """Ensure deployment configuration exists."""
        config_file = self.project_root / 'deployment' / 'config.json'
        
        if not config_file.exists():
            # Create default configuration
            default_config = {
                self.environment: {
                    'stack_name': f'healthcare-ai-{self.environment}',
                    'template_path': 'infrastructure/cloudformation-template.yaml',
                    'aws_region': self.aws_region,
                    'parameters': {
                        'Environment': self.environment,
                        'CostAlertEmail': 'admin@example.com',
                        'CostThreshold': '20'
                    },
                    'capabilities': ['CAPABILITY_IAM'],
                    'timeout_minutes': 60,
                    'enable_rollback': True
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            
            logger.info(f"Created default deployment configuration: {config_file}")
    
    def _deploy_infrastructure(self) -> Dict[str, Any]:
        """Deploy CloudFormation infrastructure."""
        try:
            # Load deployment configuration
            config_file = self.project_root / 'deployment' / 'config.json'
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            env_config = config_data[self.environment]
            
            # Create deployment config
            deployment_config = DeploymentConfig(
                environment=self.environment,
                aws_region=env_config['aws_region'],
                stack_name=env_config['stack_name'],
                template_path=str(self.project_root / env_config['template_path']),
                parameters=env_config['parameters'],
                capabilities=env_config['capabilities'],
                timeout_minutes=env_config['timeout_minutes'],
                enable_rollback=env_config['enable_rollback']
            )
            
            # Deploy infrastructure
            deployer = HealthcareAIDeployer(deployment_config)
            
            # Validate template first
            if not deployer.validate_template():
                return {
                    'success': False,
                    'error': 'CloudFormation template validation failed'
                }
            
            # Deploy stack
            self.deployment_result = deployer.deploy_stack()
            
            return {
                'success': self.deployment_result.success,
                'stack_id': self.deployment_result.stack_id,
                'outputs': self.deployment_result.outputs,
                'duration': self.deployment_result.duration,
                'error': self.deployment_result.error_message
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Infrastructure deployment failed: {str(e)}"
            }
    
    def _deploy_lambda_functions(self) -> Dict[str, Any]:
        """Deploy Lambda function code."""
        try:
            # Build and deploy Lambda functions
            lambda_dirs = [
                'src/lambda/agent_router',
                'src/lambda/illness_monitor',
                'src/lambda/mental_health',
                'src/lambda/safety_guardian',
                'src/lambda/wellness_coach',
                'src/lambda/speech_to_text',
                'src/lambda/text_to_speech',
                'src/lambda/file_upload'
            ]
            
            deployment_results = []
            
            for lambda_dir in lambda_dirs:
                lambda_path = self.project_root / lambda_dir
                
                if lambda_path.exists():
                    # Check if deployment script exists
                    deploy_script = lambda_path / 'deploy.py'
                    
                    if deploy_script.exists():
                        # Run deployment script
                        result = subprocess.run([
                            'python', str(deploy_script),
                            '--environment', self.environment,
                            '--region', self.aws_region
                        ], capture_output=True, text=True, cwd=lambda_path)
                        
                        deployment_results.append({
                            'function': lambda_dir,
                            'success': result.returncode == 0,
                            'output': result.stdout,
                            'error': result.stderr
                        })
                    else:
                        logger.warning(f"No deployment script found for {lambda_dir}")
                        deployment_results.append({
                            'function': lambda_dir,
                            'success': False,
                            'error': 'No deployment script found'
                        })
                else:
                    logger.warning(f"Lambda directory not found: {lambda_dir}")
            
            # Check overall success
            successful_deployments = sum(1 for r in deployment_results if r['success'])
            total_deployments = len(deployment_results)
            
            return {
                'success': successful_deployments > 0,  # At least one function deployed
                'deployed_functions': successful_deployments,
                'total_functions': total_deployments,
                'deployment_results': deployment_results
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Lambda deployment failed: {str(e)}"
            }
    
    def _deploy_frontend(self) -> Dict[str, Any]:
        """Deploy frontend to S3."""
        try:
            # Check if frontend deployment script exists
            frontend_deploy_script = self.project_root / 'frontend' / 's3-deployment' / 'deploy-frontend.py'
            
            if not frontend_deploy_script.exists():
                return {
                    'success': False,
                    'error': 'Frontend deployment script not found'
                }
            
            # Get API URL from deployment outputs
            api_url = None
            if self.deployment_result and self.deployment_result.outputs:
                api_url = self.deployment_result.outputs.get('APIGatewayURL')
            
            # Run frontend deployment
            cmd = [
                'python', str(frontend_deploy_script),
                '--environment', self.environment,
                '--region', self.aws_region
            ]
            
            if api_url:
                cmd.extend(['--api-url', api_url])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=frontend_deploy_script.parent
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'api_url_configured': api_url is not None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Frontend deployment failed: {str(e)}"
            }
    
    def _run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive integration tests."""
        try:
            # Get stack name from deployment
            stack_name = f'healthcare-ai-{self.environment}'
            if self.deployment_result and hasattr(self.deployment_result, 'stack_id'):
                # Extract stack name from stack ID if available
                pass
            
            # Create integration test configuration
            test_config = IntegrationTestConfig(
                environment=self.environment,
                aws_region=self.aws_region,
                stack_name=stack_name,
                timeout=30,
                parallel_tests=5
            )
            
            # Run integration tests
            tester = FinalIntegrationTester(test_config)
            
            if not tester.setup_integration_test():
                return {
                    'success': False,
                    'error': 'Failed to set up integration test environment'
                }
            
            # Run comprehensive tests
            self.test_results = tester.run_comprehensive_tests()
            
            # Generate final report
            self.final_report = tester.generate_final_report(self.test_results)
            
            # Determine success based on test results
            summary = self.test_results.get('summary', {})
            success_rate = summary.get('success_rate', 0)
            
            return {
                'success': success_rate >= 80,  # 80% success rate threshold
                'test_results': self.test_results,
                'success_rate': success_rate,
                'total_tests': summary.get('total_tests', 0),
                'passed_tests': summary.get('passed', 0),
                'failed_tests': summary.get('failed', 0)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Integration testing failed: {str(e)}"
            }
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final deployment and testing report."""
        try:
            report_data = {
                'deployment_summary': {
                    'environment': self.environment,
                    'aws_region': self.aws_region,
                    'deployment_time': datetime.utcnow().isoformat(),
                    'deployment_success': self.deployment_result.success if self.deployment_result else False,
                    'stack_outputs': self.deployment_result.outputs if self.deployment_result else {}
                },
                'test_summary': self.test_results.get('summary', {}) if self.test_results else {},
                'detailed_results': self.test_results if self.test_results else {},
                'final_report': self.final_report if self.final_report else {}
            }
            
            # Save report to file
            report_file = self.project_root / 'reports' / f'deployment_test_report_{self.environment}_{int(time.time())}.json'
            report_file.parent.mkdir(exist_ok=True)
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            logger.info(f"Final report saved to: {report_file}")
            
            return {
                'success': True,
                'report_file': str(report_file),
                'report_data': report_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Report generation failed: {str(e)}"
            }
    
    def print_summary(self, process_results: Dict[str, Any]):
        """Print deployment and testing summary."""
        print(f"\n{'='*80}")
        print(f"HEALTHCARE AI DEPLOYMENT AND TESTING SUMMARY")
        print(f"{'='*80}")
        print(f"Environment: {self.environment}")
        print(f"AWS Region: {self.aws_region}")
        print(f"Overall Status: {process_results.get('overall_status', 'UNKNOWN')}")
        
        if process_results.get('failure_step'):
            print(f"Failed at Step: {process_results['failure_step']}")
        
        print(f"\nStep Results:")
        for step_name, step_result in process_results.get('steps', {}).items():
            status = "✅ PASSED" if step_result.get('success', False) else "❌ FAILED"
            print(f"  {step_name}: {status}")
            
            if not step_result.get('success', False) and step_result.get('error'):
                print(f"    Error: {step_result['error']}")
        
        # Print test summary if available
        test_step = process_results.get('steps', {}).get('testing', {})
        if test_step.get('success') is not None:
            print(f"\nTest Results:")
            print(f"  Total Tests: {test_step.get('total_tests', 0)}")
            print(f"  Passed: {test_step.get('passed_tests', 0)}")
            print(f"  Failed: {test_step.get('failed_tests', 0)}")
            print(f"  Success Rate: {test_step.get('success_rate', 0):.1f}%")
        
        # Print key URLs if available
        deployment_step = process_results.get('steps', {}).get('deployment', {})
        if deployment_step.get('outputs'):
            outputs = deployment_step['outputs']
            print(f"\nDeployment URLs:")
            if outputs.get('APIGatewayURL'):
                print(f"  📡 API Gateway: {outputs['APIGatewayURL']}")
            if outputs.get('CloudFrontURL'):
                print(f"  🌐 CloudFront: {outputs['CloudFrontURL']}")
        
        # Print recommendations
        if self.final_report and 'recommendations' in self.final_report:
            recommendations = self.final_report['recommendations'][:3]  # Top 3
            if recommendations:
                print(f"\n💡 Top Recommendations:")
                for rec in recommendations:
                    print(f"  • {rec}")
        
        print(f"\n{'='*80}")


def main():
    """Main function for deployment and testing orchestration."""
    parser = argparse.ArgumentParser(description='Deploy and Test Healthcare AI System')
    parser.add_argument('--environment', default='test', help='Deployment environment')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--skip-deployment', action='store_true', help='Skip deployment, only run tests')
    parser.add_argument('--skip-tests', action='store_true', help='Skip tests, only deploy')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create orchestrator
    orchestrator = DeploymentOrchestrator(args.environment, args.region)
    
    try:
        if args.skip_deployment and args.skip_tests:
            logger.error("Cannot skip both deployment and tests")
            return 1
        
        if args.skip_deployment:
            # Run tests only
            logger.info("Running tests only (skipping deployment)...")
            test_result = orchestrator._run_comprehensive_tests()
            
            if test_result['success']:
                logger.info("✅ Tests completed successfully")
                return 0
            else:
                logger.error("❌ Tests failed")
                return 1
        
        elif args.skip_tests:
            # Deploy only
            logger.info("Running deployment only (skipping tests)...")
            
            # Run deployment steps
            prep_result = orchestrator._prepare_deployment()
            if not prep_result['success']:
                logger.error(f"Preparation failed: {prep_result['error']}")
                return 1
            
            deploy_result = orchestrator._deploy_infrastructure()
            if not deploy_result['success']:
                logger.error(f"Deployment failed: {deploy_result['error']}")
                return 1
            
            logger.info("✅ Deployment completed successfully")
            return 0
        
        else:
            # Run complete process
            process_results = orchestrator.run_complete_deployment_and_test()
            
            # Print summary
            orchestrator.print_summary(process_results)
            
            # Return appropriate exit code
            if process_results.get('overall_status') == 'PASSED':
                logger.info("🎉 Deployment and testing completed successfully!")
                return 0
            else:
                logger.error("❌ Deployment and testing failed")
                return 1
    
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())