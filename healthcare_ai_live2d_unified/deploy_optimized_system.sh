#!/bin/bash
set -e

# Healthcare AI Lambda Optimization Deployment Script
echo "🚀 Deploying Healthcare AI Lambda Optimization System..."

# Configuration
ENVIRONMENT=${ENVIRONMENT:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
DEPLOYMENT_BUCKET=${DEPLOYMENT_BUCKET:-healthcare-ai-deployment-$ENVIRONMENT}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

if ! command -v zip &> /dev/null; then
    print_error "zip command is not available"
    exit 1
fi

print_success "Prerequisites check passed"

# Create deployment bucket if it doesn't exist
print_status "Setting up deployment bucket: $DEPLOYMENT_BUCKET"
aws s3 mb s3://$DEPLOYMENT_BUCKET --region $AWS_REGION 2>/dev/null || print_warning "Bucket already exists or creation failed"

# Enable versioning on deployment bucket
aws s3api put-bucket-versioning \
    --bucket $DEPLOYMENT_BUCKET \
    --versioning-configuration Status=Enabled

print_success "Deployment bucket configured"

# Create optimization layer
print_status "Creating Lambda optimization layer..."
cd src/aws
python3 -c "
import sys
sys.path.append('.')
from lambda_layer_config import create_layer_package
layer_zip = create_layer_package('../../lambda_layers')
print(f'Created layer: {layer_zip}')
"
cd ../..

# Upload optimization layer to S3
print_status "Uploading optimization layer to S3..."
aws s3 cp lambda_layers/healthcare-ai-optimization-layer.zip \
    s3://$DEPLOYMENT_BUCKET/layers/healthcare-ai-optimization-layer.zip

print_success "Optimization layer uploaded"

# Package Lambda functions
print_status "Packaging Lambda functions..."

# Create temporary directory for packaging
mkdir -p temp_packages

# Function to package a Lambda function
package_function() {
    local function_name=$1
    local source_dir=$2
    
    print_status "Packaging $function_name..."
    
    # Create package directory
    local package_dir="temp_packages/$function_name"
    mkdir -p $package_dir
    
    # Copy function code
    cp -r $source_dir/* $package_dir/
    
    # Copy shared AWS modules
    mkdir -p $package_dir/aws
    cp src/aws/*.py $package_dir/aws/
    touch $package_dir/aws/__init__.py
    
    # Create zip file
    cd $package_dir
    zip -r ../../$function_name.zip . -x "*.pyc" "__pycache__/*" "*.git*" "test_*" "*_test.py"
    cd ../..
    
    # Upload to S3
    aws s3 cp $function_name.zip s3://$DEPLOYMENT_BUCKET/functions/$function_name.zip
    
    # Cleanup
    rm $function_name.zip
    
    print_success "$function_name packaged and uploaded"
}

# Package all healthcare agent functions
package_function "healthcare-agent-router" "src/lambda/agent_router"
package_function "healthcare-illness-monitor" "src/lambda/illness_monitor"
package_function "healthcare-mental-health" "src/lambda/mental_health"
package_function "healthcare-safety-guardian" "src/lambda/safety_guardian"
package_function "healthcare-wellness-coach" "src/lambda/wellness_coach"
package_function "healthcare-speech-processor" "src/lambda/speech_to_text"
package_function "healthcare-file-processor" "src/lambda/file_upload"

# Cleanup temporary packages
rm -rf temp_packages

print_success "All Lambda functions packaged and uploaded"

# Deploy CloudFormation stack
print_status "Deploying CloudFormation stack..."

# Check if stack exists
STACK_NAME="healthcare-ai-$ENVIRONMENT"
if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION >/dev/null 2>&1; then
    print_status "Stack exists, updating..."
    OPERATION="update-stack"
else
    print_status "Stack doesn't exist, creating..."
    OPERATION="create-stack"
fi

# Deploy stack
aws cloudformation $OPERATION \
    --stack-name $STACK_NAME \
    --template-body file://infrastructure/cloudformation-template.yaml \
    --parameters \
        ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
        ParameterKey=CostAlertEmail,ParameterValue=${COST_ALERT_EMAIL:-admin@example.com} \
        ParameterKey=CostThreshold,ParameterValue=${COST_THRESHOLD:-50} \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --region $AWS_REGION

# Wait for stack operation to complete
print_status "Waiting for stack operation to complete..."
aws cloudformation wait stack-${OPERATION%-stack}-complete \
    --stack-name $STACK_NAME \
    --region $AWS_REGION

# Check stack status
STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].StackStatus' \
    --output text)

if [[ $STACK_STATUS == *"COMPLETE"* ]]; then
    print_success "CloudFormation stack deployed successfully"
else
    print_error "CloudFormation stack deployment failed with status: $STACK_STATUS"
    exit 1
fi

# Get stack outputs
print_status "Retrieving stack outputs..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`HealthcareAPIEndpoint`].OutputValue' \
    --output text)

FRONTEND_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`Live2DWebsiteURL`].OutputValue' \
    --output text)

# Test the optimization system
print_status "Testing optimization system..."

# Create a test script
cat > test_optimization.py << 'EOF'
import json
import boto3
import sys
import time

def test_lambda_optimization():
    """Test Lambda optimization features."""
    lambda_client = boto3.client('lambda')
    
    # Test agent router function
    function_name = f"{sys.argv[1]}-healthcare-agent-router"
    
    print(f"Testing {function_name}...")
    
    # Test normal invocation
    test_payload = {
        "message": "Hello, I have a headache",
        "user_id": "test-user",
        "conversation_id": "test-conversation"
    }
    
    start_time = time.time()
    response = lambda_client.invoke(
        FunctionName=function_name,
        Payload=json.dumps(test_payload)
    )
    duration = time.time() - start_time
    
    result = json.loads(response['Payload'].read())
    
    print(f"✓ Function invoked successfully in {duration:.2f}s")
    print(f"✓ Status Code: {response['StatusCode']}")
    
    # Test warming invocation
    warming_payload = {"warming": True, "source": "test"}
    
    start_time = time.time()
    response = lambda_client.invoke(
        FunctionName=function_name,
        Payload=json.dumps(warming_payload)
    )
    warming_duration = time.time() - start_time
    
    print(f"✓ Warming invocation completed in {warming_duration:.2f}s")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_optimization.py <environment>")
        sys.exit(1)
    
    try:
        test_lambda_optimization()
        print("✅ Optimization system test passed!")
    except Exception as e:
        print(f"❌ Optimization system test failed: {e}")
        sys.exit(1)
EOF

python3 test_optimization.py $ENVIRONMENT
rm test_optimization.py

# Generate optimization report
print_status "Generating optimization report..."

cat > generate_report.py << 'EOF'
import json
import sys
import os
sys.path.append('src/aws')

try:
    from lambda_config_optimizer import optimize_lambda_configurations
    
    print("Generating Lambda optimization report...")
    report = optimize_lambda_configurations(dry_run=True)
    
    # Save report
    with open('optimization_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("✅ Optimization report generated: optimization_report.json")
    
    # Print summary
    summary = report.get('summary', {})
    print(f"\n📊 Optimization Summary:")
    print(f"   Functions analyzed: {summary.get('total_functions_analyzed', 0)}")
    print(f"   Current monthly cost: ${summary.get('total_current_monthly_cost', 0):.2f}")
    print(f"   Optimized monthly cost: ${summary.get('total_optimized_monthly_cost', 0):.2f}")
    print(f"   Potential monthly savings: ${summary.get('total_monthly_savings', 0):.2f}")
    
except ImportError as e:
    print(f"⚠️  Could not generate optimization report: {e}")
except Exception as e:
    print(f"❌ Error generating optimization report: {e}")
EOF

python3 generate_report.py
rm generate_report.py

# Final success message
print_success "🎉 Healthcare AI Lambda Optimization System deployed successfully!"

echo ""
echo "📋 Deployment Summary:"
echo "   Environment: $ENVIRONMENT"
echo "   Region: $AWS_REGION"
echo "   Stack Name: $STACK_NAME"
echo "   API Endpoint: $API_ENDPOINT"
echo "   Frontend URL: $FRONTEND_URL"
echo ""
echo "🔧 Optimization Features Enabled:"
echo "   ✓ Connection pooling for AWS services"
echo "   ✓ Lazy loading for non-critical modules"
echo "   ✓ Lambda warming every 5 minutes"
echo "   ✓ Optimized memory and timeout settings"
echo "   ✓ Reserved concurrency limits"
echo "   ✓ Dead letter queues for error handling"
echo "   ✓ X-Ray tracing for performance monitoring"
echo ""
echo "📈 Next Steps:"
echo "   1. Monitor CloudWatch metrics for performance improvements"
echo "   2. Review optimization_report.json for further tuning opportunities"
echo "   3. Set up CloudWatch alarms for cost and performance monitoring"
echo "   4. Test the system with realistic workloads"
echo ""
echo "🔗 Useful Commands:"
echo "   View logs: aws logs tail /aws/lambda/$ENVIRONMENT-healthcare-agent-router --follow"
echo "   Monitor costs: aws ce get-cost-and-usage --time-period Start=\$(date -d '1 month ago' +%Y-%m-%d),End=\$(date +%Y-%m-%d) --granularity MONTHLY --metrics BlendedCost"
echo "   Update functions: ./deploy_optimized_system.sh"

print_success "Deployment completed! 🚀"