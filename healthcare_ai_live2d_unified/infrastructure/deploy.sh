#!/bin/bash

# Healthcare AI Live2D System - One-Click AWS Deployment Script
# This script deploys the entire serverless healthcare system to AWS

set -e

# Configuration
STACK_NAME="healthcare-ai-live2d"
TEMPLATE_FILE="cloudformation-template.yaml"
REGION="us-east-1"
ENVIRONMENT="dev"
COST_ALERT_EMAIL=""
COST_THRESHOLD="20"

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

# Function to check if AWS CLI is installed and configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi

    print_success "AWS CLI is installed and configured"
}

# Function to validate parameters
validate_parameters() {
    if [ -z "$COST_ALERT_EMAIL" ]; then
        read -p "Enter email address for cost alerts: " COST_ALERT_EMAIL
        if [ -z "$COST_ALERT_EMAIL" ]; then
            print_error "Email address is required for cost alerts"
            exit 1
        fi
    fi

    # Validate email format
    if [[ ! "$COST_ALERT_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
        print_error "Invalid email format"
        exit 1
    fi

    print_success "Parameters validated"
}

# Function to check if stack exists
stack_exists() {
    aws cloudformation describe-stacks --stack-name "$1" --region "$REGION" &> /dev/null
}

# Function to deploy CloudFormation stack
deploy_stack() {
    local stack_name="$1"
    local operation="$2"
    
    print_status "Starting CloudFormation $operation for stack: $stack_name"
    
    local parameters=(
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT"
        "ParameterKey=CostAlertEmail,ParameterValue=$COST_ALERT_EMAIL"
        "ParameterKey=CostThreshold,ParameterValue=$COST_THRESHOLD"
    )
    
    if [ "$operation" = "create" ]; then
        aws cloudformation create-stack \
            --stack-name "$stack_name" \
            --template-body "file://$TEMPLATE_FILE" \
            --parameters "${parameters[@]}" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION" \
            --tags Key=Project,Value=HealthcareAI Key=Environment,Value="$ENVIRONMENT" Key=CostCenter,Value=Development
    else
        aws cloudformation update-stack \
            --stack-name "$stack_name" \
            --template-body "file://$TEMPLATE_FILE" \
            --parameters "${parameters[@]}" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION"
    fi
}

# Function to wait for stack operation to complete
wait_for_stack() {
    local stack_name="$1"
    local operation="$2"
    
    print_status "Waiting for stack $operation to complete..."
    
    if [ "$operation" = "create" ]; then
        aws cloudformation wait stack-create-complete --stack-name "$stack_name" --region "$REGION"
    else
        aws cloudformation wait stack-update-complete --stack-name "$stack_name" --region "$REGION"
    fi
    
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        print_success "Stack $operation completed successfully"
    else
        print_error "Stack $operation failed"
        exit 1
    fi
}

# Function to get stack outputs
get_stack_outputs() {
    local stack_name="$1"
    
    print_status "Retrieving stack outputs..."
    
    local outputs=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs' \
        --output table)
    
    echo "$outputs"
}

# Function to display deployment summary
display_summary() {
    local stack_name="$1"
    
    print_success "Deployment completed successfully!"
    echo ""
    echo "=== DEPLOYMENT SUMMARY ==="
    echo "Stack Name: $stack_name"
    echo "Region: $REGION"
    echo "Environment: $ENVIRONMENT"
    echo ""
    
    # Get important outputs
    local api_url=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`APIGatewayURL`].OutputValue' \
        --output text)
    
    local cloudfront_url=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
        --output text)
    
    local website_bucket=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`WebsiteBucketName`].OutputValue' \
        --output text)
    
    echo "=== IMPORTANT URLS ==="
    echo "API Endpoint: $api_url"
    echo "Frontend URL: $cloudfront_url"
    echo ""
    echo "=== NEXT STEPS ==="
    echo "1. Upload your Live2D frontend files to S3 bucket: $website_bucket"
    echo "2. Update your frontend configuration to use the API endpoint: $api_url"
    echo "3. Deploy your Lambda function code (see tasks 2-6 in the implementation plan)"
    echo "4. Test the system functionality"
    echo ""
    echo "=== COST MONITORING ==="
    echo "- Cost alerts configured for: $COST_ALERT_EMAIL"
    echo "- Alert threshold: \$$COST_THRESHOLD USD/month"
    echo "- Estimated cost for light usage: \$5-10 USD/month"
    echo ""
    echo "=== USEFUL COMMANDS ==="
    echo "View stack details: aws cloudformation describe-stacks --stack-name $stack_name --region $REGION"
    echo "View stack events: aws cloudformation describe-stack-events --stack-name $stack_name --region $REGION"
    echo "Delete stack: aws cloudformation delete-stack --stack-name $stack_name --region $REGION"
}

# Function to show help
show_help() {
    echo "Healthcare AI Live2D System - AWS Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV     Environment name (dev, staging, prod) [default: dev]"
    echo "  -r, --region REGION       AWS region [default: us-east-1]"
    echo "  -s, --stack-name NAME     CloudFormation stack name [default: healthcare-ai-live2d]"
    echo "  -m, --email EMAIL         Email for cost alerts"
    echo "  -t, --threshold AMOUNT    Cost threshold in USD [default: 20]"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --email admin@example.com"
    echo "  $0 --environment prod --region us-west-2 --email admin@example.com"
    echo "  $0 --stack-name my-healthcare-stack --threshold 50 --email admin@example.com"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -m|--email)
            COST_ALERT_EMAIL="$2"
            shift 2
            ;;
        -t|--threshold)
            COST_THRESHOLD="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main deployment process
main() {
    echo "=== Healthcare AI Live2D System - AWS Deployment ==="
    echo ""
    
    # Check prerequisites
    check_aws_cli
    validate_parameters
    
    # Check if template file exists
    if [ ! -f "$TEMPLATE_FILE" ]; then
        print_error "CloudFormation template file not found: $TEMPLATE_FILE"
        exit 1
    fi
    
    # Determine operation (create or update)
    local operation="create"
    if stack_exists "$STACK_NAME"; then
        operation="update"
        print_warning "Stack already exists. Will perform update operation."
    fi
    
    # Deploy the stack
    deploy_stack "$STACK_NAME" "$operation"
    wait_for_stack "$STACK_NAME" "$operation"
    
    # Display results
    display_summary "$STACK_NAME"
}

# Run main function
main "$@"